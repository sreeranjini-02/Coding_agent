from pathlib import Path
from fastapi import UploadFile, HTTPException
import shutil
import uuid

# Dedicated upload directory
BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads" / "users"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def save_user_file(user_id: int, file: UploadFile):

    # Create user-specific folder
    user_folder = UPLOAD_DIR / str(user_id)
    user_folder.mkdir(parents=True, exist_ok=True)

    # Get original extension
    extension = Path(file.filename).suffix.lower()

    # Generate unique filename
    filename = f"{uuid.uuid4().hex}{extension}"

    file_path = user_folder / filename

    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": file.filename,
        "stored_filename": filename,
        "file_path": str(file_path),
        "file_size": file_path.stat().st_size,
    }


def get_user_upload_folder(user_id: int):

    folder = UPLOAD_DIR / str(user_id)

    folder.mkdir(parents=True, exist_ok=True)

    return folder