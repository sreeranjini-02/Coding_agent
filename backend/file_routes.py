import os
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException
)

from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from io import BytesIO

from backend.database import SessionLocal
from backend.auth_routes import get_current_user


router = APIRouter(
    prefix="/files",
    tags=["Uploaded Files"]
)


# =====================================================
# DATABASE
# =====================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =====================================================
# UPLOAD DIRECTORY
# =====================================================

# Project root/uploads/users/
BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads" / "users"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================
# FILE SETTINGS
# =====================================================

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
    ".md",
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


# =====================================================
# SAVE FILE TO FOLDER AND DATABASE
# =====================================================

def store_uploaded_file(user_id, filename, file_content, db):

    extension = Path(filename).suffix.lower()

    # Validate extension
    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail="Unsupported file type."
        )

    # Validate empty file
    if not file_content:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    # Validate file size
    if len(file_content) > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=413,
            detail="File size exceeds 10 MB limit."
        )

    user_folder = UPLOAD_DIR / str(user_id)

    user_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # Generate unique filename
    stored_filename = f"{uuid.uuid4().hex}{extension}"

    file_path = user_folder / stored_filename

    try:

        # Save physical file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

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
                "file_size": len(file_content)
            }
        )

        db.commit()

        return {
            "file_id": result.lastrowid,
            "filename": filename,
            "stored_filename": stored_filename,
            "file_type": extension,
            "file_size": len(file_content)
        }

    except Exception:

        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise


# =====================================================
# UPLOAD FILE API
# =====================================================

@router.post("/upload")
async def upload_file(

    file: UploadFile = File(...),

    current_user: dict = Depends(get_current_user),

    db: Session = Depends(get_db)

):

    try:

        user_id = current_user["id"]

        filename = os.path.basename(
            file.filename or "uploaded_file"
        )

        file_content = await file.read()

        file_data = store_uploaded_file(
            user_id,
            filename,
            file_content,
            db
        )

        return {
            "message": "File uploaded successfully.",
            **file_data
        }

    except HTTPException:
        raise

    except Exception as e:

        print("File upload error:", str(e))

        raise HTTPException(
            status_code=500,
            detail="File upload failed."
        )

    finally:

        await file.close()


# =====================================================
# LIST USER FILES
# =====================================================

@router.get("/")
def get_uploaded_files(

    current_user: dict = Depends(get_current_user),

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


# =====================================================
# DOWNLOAD FILE
# =====================================================

@router.get("/{file_id}/download")
def download_file(

    file_id: int,

    current_user: dict = Depends(get_current_user),

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

    stored_filename = file_record["stored_filename"]

    # Download from physical folder
    if stored_filename:

        file_path = (
            UPLOAD_DIR
            / str(user_id)
            / stored_filename
        )

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

    # Download old files stored in MySQL
    file_content = file_record["file_content"]

    if file_content:

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


# =====================================================
# DELETE FILE
# =====================================================

@router.delete("/{file_id}")
def delete_file(

    file_id: int,

    current_user: dict = Depends(get_current_user),

    db: Session = Depends(get_db)

):

    try:

        user_id = current_user["id"]

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

            file_path = (
                UPLOAD_DIR
                / str(user_id)
                / stored_filename
            )

            if file_path.exists():
                file_path.unlink()

        # Delete database record
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