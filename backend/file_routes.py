import os
from io import BytesIO

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException
)

from fastapi.responses import StreamingResponse

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.auth_routes import verify_token


router = APIRouter(
    prefix="/files",
    tags=["Uploaded Files"]
)


# --------------------------------------------------
# DATABASE SESSION
# --------------------------------------------------

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# --------------------------------------------------
# ALLOWED FILE TYPES
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
# UPLOAD FILE
# --------------------------------------------------

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(verify_token),
    db: Session = Depends(get_db)
):

    try:

        filename = os.path.basename(
            file.filename or "uploaded_file"
        )

        extension = os.path.splitext(filename)[1].lower()

        if extension not in ALLOWED_EXTENSIONS:

            raise HTTPException(
                status_code=400,
                detail="Unsupported file type."
            )

        file_content = await file.read()

        if not file_content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        if len(file_content) > MAX_FILE_SIZE:

            raise HTTPException(
                status_code=413,
                detail="File size exceeds 10 MB limit."
            )

        user_id = current_user["id"]

        result = db.execute(
            text("""
                INSERT INTO uploaded_files
                (
                    user_id,
                    filename,
                    file_type,
                    file_size,
                    file_content
                )
                VALUES
                (
                    :user_id,
                    :filename,
                    :file_type,
                    :file_size,
                    :file_content
                )
            """),
            {
                "user_id": user_id,
                "filename": filename,
                "file_type": extension,
                "file_size": len(file_content),
                "file_content": file_content
            }
        )

        db.commit()

        file_id = result.lastrowid

        return {
            "message": "File uploaded successfully.",
            "file_id": file_id,
            "filename": filename,
            "file_type": extension,
            "file_size": len(file_content)
        }

    except HTTPException:
        raise

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="File upload failed."
        )


# --------------------------------------------------
# GET USER FILES
# --------------------------------------------------

@router.get("/")
def get_uploaded_files(
    current_user=Depends(verify_token),
    db: Session = Depends(get_db)
):

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
            ORDER BY created_at DESC
        """),
        {
            "user_id": user_id
        }
    )

    files = [
        dict(row)
        for row in result.mappings().all()
    ]

    return {
        "files": files
    }


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

    return StreamingResponse(
        BytesIO(file_record["file_content"]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition":
                f'attachment; filename="{file_record["filename"]}"'
        }
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

    user_id = current_user["id"]

    result = db.execute(
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

    if result.rowcount == 0:

        raise HTTPException(
            status_code=404,
            detail="File not found."
        )

    return {
        "message": "File deleted successfully."
    }
