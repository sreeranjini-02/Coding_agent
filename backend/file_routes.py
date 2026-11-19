import os
import uuid
from pathlib import Path
from io import BytesIO

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

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =====================================================
# FILE SETTINGS
# =====================================================
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


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# =====================================================
# HELPER: GET USER FILE FOLDER
# =====================================================

def get_user_folder(user_id: int) -> Path:

    user_folder = UPLOAD_DIR / str(user_id)

    user_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    return user_folder


# =====================================================
# HELPER: STORE UPLOADED FILE
# =====================================================

def store_uploaded_file(
    user_id,
    filename,
    file_content,
    db
):

    # Get file extension
    extension = Path(filename).suffix.lower()

    # -------------------------------------------------
    # Validate file extension
    # -------------------------------------------------

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail="Unsupported file type."
        )

    # -------------------------------------------------
    # Validate empty file
    # -------------------------------------------------

    if not file_content:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    # -------------------------------------------------
    # Validate file size
    # -------------------------------------------------

    if len(file_content) > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=413,
            detail="File size exceeds 10 MB limit."
        )

    # -------------------------------------------------
    # Create user folder
    # -------------------------------------------------

    user_folder = get_user_folder(user_id)

    # -------------------------------------------------
    # Generate unique filename
    # -------------------------------------------------

    stored_filename = f"{uuid.uuid4().hex}{extension}"

    file_path = user_folder / stored_filename

    try:

        # =================================================
        # STEP 1: SAVE PHYSICAL FILE
        # =================================================

        with open(file_path, "wb") as buffer:

            buffer.write(file_content)

        # =================================================
        # STEP 2: SAVE METADATA IN MYSQL
        # =================================================

        # Actual file bytes are stored in the uploads folder.
        # MySQL stores metadata only.
        #
        # file_content is intentionally excluded from INSERT.

        result = db.execute(
            text("""
                INSERT INTO uploaded_files
                (
                    user_id,
                    filename,
                    stored_filename,
                    file_type,
                    file_size
                )
                VALUES
                (
                    :user_id,
                    :filename,
                    :stored_filename,
                    :file_type,
                    :file_size
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

        # Commit database changes
        db.commit()

        # =================================================
        # STEP 3: RETURN FILE INFORMATION
        # =================================================

        return {
            "file_id": result.lastrowid,
            "filename": filename,
            "stored_filename": stored_filename,
            "file_type": extension,
            "file_size": len(file_content)
        }

    except Exception:

        # Rollback database changes
        db.rollback()

        # Delete physical file if database insert failed
        if file_path.exists():

            try:
                file_path.unlink()

            except OSError:
                pass

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

        # -------------------------------------------------
        # Get authenticated user ID
        # -------------------------------------------------

        user_id = current_user["id"]

        # -------------------------------------------------
        # Clean filename
        # -------------------------------------------------

        filename = os.path.basename(
            file.filename or "uploaded_file"
        )

        # -------------------------------------------------
        # Read file
        # -------------------------------------------------

        file_content = await file.read()

        # -------------------------------------------------
        # Store file
        # -------------------------------------------------

        file_data = store_uploaded_file(
            user_id=user_id,
            filename=filename,
            file_content=file_content,
            db=db
        )

        # -------------------------------------------------
        # Return success response
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Get authenticated user ID
        # -------------------------------------------------

        user_id = current_user["id"]

        # -------------------------------------------------
        # Retrieve file metadata
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Return files
        # -------------------------------------------------

        return {
            "files": [
                dict(file)
                for file in files
            ]
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

    # -------------------------------------------------
    # Get authenticated user
    # -------------------------------------------------

    user_id = current_user["id"]

    # -------------------------------------------------
    # Get file metadata
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Check file existence
    # -------------------------------------------------

    if not file_record:

        raise HTTPException(
            status_code=404,
            detail="File not found."
        )

    stored_filename = file_record["stored_filename"]

    # =================================================
    # DOWNLOAD FROM PHYSICAL UPLOAD FOLDER
    # =================================================

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

    # =================================================
    # FALLBACK: OLD FILES STORED IN MYSQL
    # =================================================

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

    # -------------------------------------------------
    # File not found
    # -------------------------------------------------

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

        # -------------------------------------------------
        # Get authenticated user
        # -------------------------------------------------

        user_id = current_user["id"]

        # -------------------------------------------------
        # Find file
        # -------------------------------------------------

        result = db.execute(
            text("""
                SELECT
                    stored_filename
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

        # -------------------------------------------------
        # Validate file
        # -------------------------------------------------

        if not file_record:

            raise HTTPException(
                status_code=404,
                detail="File not found."
            )

        stored_filename = file_record["stored_filename"]

        # =================================================
        # STEP 1: DELETE PHYSICAL FILE
        # =================================================

        if stored_filename:

            file_path = (
                UPLOAD_DIR
                / str(user_id)
                / stored_filename
            )

            if file_path.exists():

                file_path.unlink()

        # =================================================
        # STEP 2: DELETE DATABASE RECORD
        # =================================================

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

        # -------------------------------------------------
        # Return success
        # -------------------------------------------------

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