import csv
import json
import logging
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook


logger = logging.getLogger(__name__)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".txt",
    ".md",
    ".csv",
    ".tsv",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".py",
    ".java",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".sql",
}


# --------------------------------------------------
# DOCUMENT MODEL
# --------------------------------------------------

@dataclass
class SourceDocument:
    source: str
    text: str
    kind: str


# --------------------------------------------------
# HTML TEXT EXTRACTION
# --------------------------------------------------

class HTMLTextExtractor(HTMLParser):

    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        cleaned = data.strip()

        if cleaned:
            self.text_parts.append(cleaned)

    def get_text(self):
        return "\n".join(self.text_parts)


# --------------------------------------------------
# TEXT FILE READER
# --------------------------------------------------

def read_text_file(path: Path) -> str:

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin-1",
    ]

    for encoding in encodings:

        try:
            return path.read_text(
                encoding=encoding
            )

        except UnicodeDecodeError:
            continue

    raise ValueError(
        f"Unable to decode file: {path.name}"
    )


# --------------------------------------------------
# PDF READER
# --------------------------------------------------

def read_pdf(path: Path) -> str:

    reader = PdfReader(str(path))

    pages = []

    for page_number, page in enumerate(reader.pages):

        text = page.extract_text() or ""

        if text.strip():
            pages.append(
                f"Page {page_number + 1}\n{text}"
            )

    return "\n\n".join(pages)


# --------------------------------------------------
# WORD READER
# --------------------------------------------------

def read_docx(path: Path) -> str:

    document = Document(str(path))

    content = []

    # Read paragraphs
    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:
            content.append(text)

    # Read tables
    for table in document.tables:

        for row in table.rows:

            row_text = [
                cell.text.strip()
                for cell in row.cells
            ]

            content.append(
                " | ".join(row_text)
            )

    return "\n".join(content)


# --------------------------------------------------
# EXCEL READER
# --------------------------------------------------

def read_xlsx(path: Path) -> str:

    workbook = load_workbook(
        filename=path,
        read_only=True,
        data_only=True,
    )

    content = []

    try:

        for sheet in workbook.worksheets:

            content.append(
                f"\nSheet: {sheet.title}\n"
            )

            for row in sheet.iter_rows(
                values_only=True
            ):

                values = [
                    str(value) if value is not None else ""
                    for value in row
                ]

                if any(values):
                    content.append(
                        " | ".join(values)
                    )

    finally:
        workbook.close()

    return "\n".join(content)


# --------------------------------------------------
# CSV / TSV READER
# --------------------------------------------------

def read_csv_file(path: Path) -> str:

    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","

    content = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as file:

        reader = csv.reader(
            file,
            delimiter=delimiter,
        )

        for row in reader:

            content.append(
                " | ".join(row)
            )

    return "\n".join(content)


# --------------------------------------------------
# JSON READER
# --------------------------------------------------

def read_json(path: Path) -> str:

    text = read_text_file(path)

    data = json.loads(text)

    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
    )


# --------------------------------------------------
# HTML READER
# --------------------------------------------------

def read_html(path: Path) -> str:

    html_content = read_text_file(path)

    parser = HTMLTextExtractor()

    parser.feed(html_content)

    return parser.get_text()


# --------------------------------------------------
# FILE CONTENT EXTRACTION
# --------------------------------------------------

def extract_file_content(path: Path) -> str:

    extension = path.suffix.lower()

    if extension == ".pdf":
        return read_pdf(path)

    elif extension == ".docx":
        return read_docx(path)

    elif extension == ".xlsx":
        return read_xlsx(path)

    elif extension in {".csv", ".tsv"}:
        return read_csv_file(path)

    elif extension == ".json":
        return read_json(path)

    elif extension == ".html":
        return read_html(path)

    elif extension in {
        ".txt",
        ".md",
        ".yaml",
        ".yml",
        ".xml",
        ".py",
        ".java",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".sql",
    }:
        return read_text_file(path)

    raise ValueError(
        f"Unsupported file format: {extension}"
    )


# --------------------------------------------------
# LOAD SINGLE FILE
# --------------------------------------------------

def load_file(
    path,
    source=None,
) -> SourceDocument:

    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Not a valid file: {file_path}"
        )

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}"
        )

    file_size = file_path.stat().st_size

    if file_size > MAX_FILE_BYTES:
        raise ValueError(
            f"{file_path.name} exceeds the 20 MB limit."
        )

    text = extract_file_content(file_path)

    if not text.strip():
        raise ValueError(
            f"No readable text found in {file_path.name}. "
            "Scanned PDFs may require OCR."
        )

    return SourceDocument(
        source=source or file_path.name,
        text=text,
        kind=file_path.suffix.lower().replace(".", ""),
    )


# --------------------------------------------------
# LOAD MULTIPLE FILES
# --------------------------------------------------

def load_files(paths) -> list[SourceDocument]:

    documents = []

    for path in paths:

        try:

            document = load_file(path)

            documents.append(document)

        except Exception:

            logger.exception(
                "Failed to load file: %s",
                path,
            )

    return documents


# --------------------------------------------------
# LOAD DIRECTORY
# --------------------------------------------------

def load_directory(directory) -> list[SourceDocument]:

    folder = Path(directory)

    if not folder.exists():
        logger.warning(
            "Directory does not exist: %s",
            folder,
        )
        return []

    if not folder.is_dir():
        raise ValueError(
            f"Expected a directory: {folder}"
        )

    documents = []

    for file_path in folder.rglob("*"):

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:

            document = load_file(file_path)

            documents.append(document)

            logger.info(
                "Loaded document: %s",
                file_path.name,
            )

        except Exception:

            logger.exception(
                "Could not load document: %s",
                file_path.name,
            )

    return documents