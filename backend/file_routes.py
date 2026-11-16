import os
import uuid
import shutil
from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException
)

from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.auth_routes import verify_token


router = APIRouter(
    prefix="/files",
    tags=["Uploaded Files"]
)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------
# UPLOAD DIRECTORY
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads" / "users"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# FILE SETTINGS
# --------------------------------------------------

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
    ".py",
    ".java",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".json",
    ".sql"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# --------------------------------------------------
# SAVE FILE TO FOLDER
# --------------------------------------------------

def save_file_to_folder(user_id, filename, file_content):

    user_folder = UPLOAD_DIR / str(user_id)

    user_folder.mkdir(parents=True, exist_ok=True)

    extension = Path(filename).suffix.lower()

    stored_filename = f"{uuid.uuid4().hex}{extension}"

    file_path = user_folder / stored_filename

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    return stored_filename, file_path


# --------------------------------------------------
# UPLOAD FILE
# --------------------------------------------------

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(verify_token),
    db: Session = Depends(get_db)
):

    file_path = None

    try:

        user_id = current_user["id"]

        filename = os.path.basename(file.filename or "uploaded_file")

        extension = Path(filename).suffix.lower()

        # Validate extension
        if extension not in ALLOWED_EXTENSIONS:

            raise HTTPException(
                status_code=400,
                detail="Unsupported file type."
            )

        # Read file
        file_content = await file.read()

        # Empty file validation
        if not file_content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        # Size validation
        if len(file_content) > MAX_FILE_SIZE:

            raise HTTPException(
                status_code=413,
                detail="File size exceeds 10 MB limit."
            )

        # Save physical file
        stored_filename, file_path = save_file_to_folder(
            user_id,
            filename,
            file_content
        )

        file_size = len(file_content)

        # Save metadata in MySQL
        result = db.execute(
            text("""
                INSERT INTO uploaded_files
                (
                    user_id,
                    filename,
                    stored_filename,
                    file_type,
                    file_size,
                    file_content
                )
                VALUES
                (
                    :user_id,
                    :filename,
                    :stored_filename,
                    :file_type,
                    :file_size,
                    NULL
                )
            """),
            {
                "user_id": user_id,
                "filename": filename,
                "stored_filename": stored_filename,
                "file_type": extension,
                "file_size": file_size
            }
        )

        db.commit()

        file_id = result.lastrowid

        return {
            "message": "File uploaded successfully.",
            "file_id": file_id,
            "filename": filename,
            "stored_filename": stored_filename,
            "file_type": extension,
            "file_size": file_size
        }

    except HTTPException:
        raise

    except Exception as e:

        db.rollback()

        # Remove physical file if database insertion fails
        if file_path and file_path.exists():

            file_path.unlink()

        print("File upload error:", str(e))

        raise HTTPException(
            status_code=500,
            detail="File upload failed."
        )

    finally:

        await file.close()


# --------------------------------------------------
# LIST USER FILES
# --------------------------------------------------

@router.get("/")
def get_uploaded_files(
    current_user=Depends(verify_token),
    db: Session = Depends(get_db)
):

    try:

        user_id = current_user["id"]

        result = db.execute(
            text("""
                SELECT
                    id,
                    filename,
                    file_type,
                    file_size,
                    created_at
                FROM uploaded_files
                WHERE user_id = :user_id
                ORDER BY id DESC
            """),
            {
                "user_id": user_id
            }
        )

        files = result.mappings().all()

        return {
            "files": [dict(file) for file in files]
        }

    except Exception as e:

        print("File listing error:", str(e))

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve uploaded files."
        )


# --------------------------------------------------
# DOWNLOAD FILE
# --------------------------------------------------

@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    current_user=Depends(verify_token),
    db: Session = Depends(get_db)
):

    user_id = current_user["id"]

    result = db.execute(
        text("""
            SELECT
                filename,
                stored_filename,
                file_content
            FROM uploaded_files
            WHERE id = :file_id
            AND user_id = :user_id
        """),
        {
            "file_id": file_id,
            "user_id": user_id
        }
    )

    file_record = result.mappings().first()

    if not file_record:

        raise HTTPException(
            status_code=404,
            detail="File not found."
        )

    # New folder-based files
    stored_filename = file_record["stored_filename"]

    if stored_filename:

        file_path = UPLOAD_DIR / str(user_id) / stored_filename

        if not file_path.exists():

            raise HTTPException(
                status_code=404,
                detail="Physical file not found."
            )

        return FileResponse(
            path=str(file_path),
            filename=file_record["filename"],
            media_type="application/octet-stream"
        )

    # Old files stored in MySQL BLOB
    file_content = file_record["file_content"]

    if file_content:

        from io import BytesIO
        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            BytesIO(file_content),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{file_record["filename"]}"'
            }
        )

    raise HTTPException(
        status_code=404,
        detail="File content not found."
    )


# --------------------------------------------------
# DELETE FILE
# --------------------------------------------------

@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    current_user=Depends(verify_token),
    db: Session = Depends(get_db)
):

    try:

        user_id = current_user["id"]

        # Find file
        result = db.execute(
            text("""
                SELECT stored_filename
                FROM uploaded_files
                WHERE id = :file_id
                AND user_id = :user_id
            """),
            {
                "file_id": file_id,
                "user_id": user_id
            }
        )

        file_record = result.mappings().first()

        if not file_record:

            raise HTTPException(
                status_code=404,
                detail="File not found."
            )

        stored_filename = file_record["stored_filename"]

        # Delete physical file
        if stored_filename:

            file_path = UPLOAD_DIR / str(user_id) / stored_filename

            if file_path.exists():

                file_path.unlink()

        # Delete metadata from MySQL
        db.execute(
            text("""
                DELETE FROM uploaded_files
                WHERE id = :file_id
                AND user_id = :user_id
            """),
            {
                "file_id": file_id,
                "user_id": user_id
            }
        )

        db.commit()

        return {
            "message": "File deleted successfully."
        }

    except HTTPException:
        raise

    except Exception as e:

        db.rollback()

        print("File deletion error:", str(e))

        raise HTTPException(
            status_code=500,
            detail="File deletion failed."
        )
