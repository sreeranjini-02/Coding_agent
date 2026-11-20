import os
import uuid
import csv

from pathlib import Path
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook

from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

EMBEDDING_MODEL = "gemini-embedding-001"


# --------------------------------------------------
# SUPPORTED FILE TYPES
# --------------------------------------------------

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".py",
    ".java",
    ".js",
    ".jsx",
    ".html",
    ".css",
    ".csv",
    ".xlsx"
}


# --------------------------------------------------
# TEMPORARY FILE STORE
# --------------------------------------------------

FILE_STORE = {}


# --------------------------------------------------
# TEXT EXTRACTION
# --------------------------------------------------

def extract_text(file_path):

    file_path = Path(file_path)

    extension = file_path.suffix.lower()

    # PDF
    if extension == ".pdf":

        reader = PdfReader(file_path)

        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    # DOCX
    elif extension == ".docx":

        document = Document(file_path)

        content = []

        for paragraph in document.paragraphs:

            if paragraph.text.strip():
                content.append(paragraph.text)

        # Extract table contents also
        for table in document.tables:

            for row in table.rows:

                content.append(
                    " | ".join(
                        cell.text.strip()
                        for cell in row.cells
                    )
                )

        return "\n".join(content)

    # EXCEL
    elif extension == ".xlsx":

        workbook = load_workbook(
            file_path,
            data_only=True,
            read_only=True
        )

        content = []

        for sheet in workbook.worksheets:

            content.append(
                f"\n===== SHEET: {sheet.title} ====="
            )

            for row in sheet.iter_rows(
                values_only=True
            ):

                values = [
                    str(cell) if cell is not None else ""
                    for cell in row
                ]

                # Skip completely empty rows
                if not any(value.strip() for value in values):
                    continue

                content.append(
                    " | ".join(values)
                )

        workbook.close()

        return "\n".join(content)

    # CSV
    elif extension == ".csv":

        content = []

        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            errors="ignore"
        ) as file:

            reader = csv.reader(file)

            for row in reader:

                if row:

                    content.append(
                        " | ".join(row)
                    )

        return "\n".join(content)

    # TXT AND CODE FILES
    else:

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            return file.read()


# --------------------------------------------------
# TEXT CHUNKING
# --------------------------------------------------

def split_text(
    text,
    chunk_size=1000,
    overlap=150
):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# --------------------------------------------------
# EMBEDDING GENERATION
# --------------------------------------------------

def generate_embeddings(texts):

    embeddings = []

    for start in range(
        0,
        len(texts),
        50
    ):

        batch = texts[start:start + 50]

        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch
        )

        embeddings.extend([
            item.values
            for item in result.embeddings
        ])

    return embeddings


# --------------------------------------------------
# UPLOAD AND INDEX
# --------------------------------------------------

def upload_and_index(
    file_path,
    filename
):

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:

        raise ValueError(
            "Unsupported file format."
        )

    content = extract_text(file_path)

    if not content.strip():

        raise ValueError(
            "No readable text found in file."
        )

    chunks = split_text(content)

    embeddings = generate_embeddings(chunks)

    file_id = str(uuid.uuid4())

    FILE_STORE[file_id] = {
        "filename": filename,
        "chunks": chunks,
        "embeddings": embeddings,
        "full_text": content,
        "extension": extension
    }

    return {
        "file_id": file_id,
        "filename": filename,
        "chunks": len(chunks)
    }


# --------------------------------------------------
# GET FULL FILE CONTENT
# --------------------------------------------------

def get_file_content(file_ids):

    if not file_ids:
        return ""

    content_parts = []

    for file_id in file_ids:

        file_data = FILE_STORE.get(file_id)

        if not file_data:
            continue

        content_parts.append(
            f"""
FILE NAME: {file_data['filename']}

FILE CONTENT:

{file_data.get('full_text', '')}
"""
        )

    return "\n\n".join(content_parts)


# --------------------------------------------------
# RAG RETRIEVAL
# --------------------------------------------------

def retrieve_context(
    question,
    file_ids=None,
    top_k=4
):

    if not file_ids:
        return ""

    question_embedding = generate_embeddings(
        [question]
    )[0]

    import numpy as np

    question_vector = np.array(
        question_embedding
    )

    results = []

    for file_id in file_ids:

        file_data = FILE_STORE.get(file_id)

        if not file_data:
            continue

        for chunk, embedding in zip(
            file_data["chunks"],
            file_data["embeddings"]
        ):

            vector = np.array(embedding)

            denominator = (
                np.linalg.norm(question_vector)
                * np.linalg.norm(vector)
            )

            if denominator == 0:
                continue

            similarity = float(
                np.dot(
                    question_vector,
                    vector
                ) / denominator
            )

            results.append({
                "chunk": chunk,
                "score": similarity,
                "filename": file_data["filename"]
            })

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    selected = results[:top_k]

    return "\n\n".join(
        f"Source: {item['filename']}\n{item['chunk']}"
        for item in selected
    )