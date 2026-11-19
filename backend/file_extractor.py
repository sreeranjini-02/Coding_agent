import json
import csv
from pathlib import Path

import fitz
import pandas as pd

from docx import Document
from openpyxl import load_workbook


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".txt",
    ".md",
    ".json",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".sql",
}


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from supported documents and code files.
    """

    path = Path(file_path)
    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    # PDF
    if extension == ".pdf":
        return extract_pdf(path)

    # Word
    elif extension == ".docx":
        return extract_docx(path)

    # Excel
    elif extension == ".xlsx":
        return extract_excel(path)

    # CSV
    elif extension == ".csv":
        return extract_csv(path)

    # JSON
    elif extension == ".json":
        return extract_json(path)

    # Text and code files
    else:
        return extract_text_file(path)


# =========================
# PDF EXTRACTION
# =========================

def extract_pdf(path: Path) -> str:

    text = []

    with fitz.open(path) as pdf:

        for page_number, page in enumerate(pdf, start=1):

            page_text = page.get_text()

            text.append(
                f"\n--- Page {page_number} ---\n"
                f"{page_text}"
            )

    return "\n".join(text)


# =========================
# DOCX EXTRACTION
# =========================

def extract_docx(path: Path) -> str:

    document = Document(path)

    text = []

    # Paragraphs
    for paragraph in document.paragraphs:

        if paragraph.text.strip():

            text.append(paragraph.text)

    # Tables
    for table_index, table in enumerate(
        document.tables, start=1
    ):

        text.append(
            f"\n--- Table {table_index} ---"
        )

        for row in table.rows:

            row_data = [
                cell.text.strip()
                for cell in row.cells
            ]

            text.append(
                " | ".join(row_data)
            )

    return "\n".join(text)


# =========================
# EXCEL EXTRACTION
# =========================

def extract_excel(path: Path) -> str:

    workbook = load_workbook(
        filename=path,
        data_only=True
    )

    output = []

    for sheet in workbook.worksheets:

        output.append(
            f"\n--- Sheet: {sheet.title} ---"
        )

        for row in sheet.iter_rows(
            values_only=True
        ):

            values = [
                str(value) if value is not None else ""
                for value in row
            ]

            if any(values):

                output.append(
                    " | ".join(values)
                )

    workbook.close()

    return "\n".join(output)


# =========================
# CSV EXTRACTION
# =========================

def extract_csv(path: Path) -> str:

    try:

        dataframe = pd.read_csv(
            path,
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        dataframe = pd.read_csv(
            path,
            encoding="latin-1"
        )

    return dataframe.to_string(
        index=False
    )


# =========================
# JSON EXTRACTION
# =========================

def extract_json(path: Path) -> str:

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False
    )


# =========================
# TEXT / CODE EXTRACTION
# =========================

def extract_text_file(path: Path) -> str:

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return file.read()

    except UnicodeDecodeError:

        with open(
            path,
            "r",
            encoding="latin-1"
        ) as file:

            return file.read()