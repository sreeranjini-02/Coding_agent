import os
import uuid
import csv
import io

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

# Temporary in-memory storage.
# Each upload receives its own file ID.

FILE_STORE = {}


def extract_text(file_path):

    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":

        reader = PdfReader(file_path)

        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    elif extension == ".docx":

        document = Document(file_path)

        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    elif extension == ".xlsx":

        workbook = load_workbook(
            file_path,
            data_only=True
        )

        content = []

        for sheet in workbook.worksheets:

            content.append(f"Sheet: {sheet.title}")

            for row in sheet.iter_rows(values_only=True):

                content.append(
                    " | ".join(
                        str(cell) if cell is not None else ""
                        for cell in row
                    )
                )

        return "\n".join(content)

    elif extension == ".csv":

        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            errors="ignore"
        ) as file:

            return file.read()

    else:

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            return file.read()


def split_text(text, chunk_size=1000, overlap=150):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def generate_embeddings(texts):

    embeddings = []

    for start in range(0, len(texts), 50):

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


def upload_and_index(file_path, filename):

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file format.")

    content = extract_text(file_path)

    if not content.strip():
        raise ValueError("No readable text found in file.")

    chunks = split_text(content)

    embeddings = generate_embeddings(chunks)

    file_id = str(uuid.uuid4())

    FILE_STORE[file_id] = {
        "filename": filename,
        "chunks": chunks,
        "embeddings": embeddings
    }

    return {
        "file_id": file_id,
        "filename": filename,
        "chunks": len(chunks)
    }


def retrieve_context(question, file_ids, top_k=4):

    if not file_ids:
        return ""

    question_embedding = generate_embeddings(
        [question]
    )[0]

    import numpy as np

    question_vector = np.array(question_embedding)

    results = []

    # Search ONLY the files attached to this question.

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
                np.dot(question_vector, vector)
                / denominator
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