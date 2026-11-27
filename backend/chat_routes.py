from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.database import SessionLocal
from backend.auth_routes import get_current_user


router = APIRouter(
    prefix="/chat",
    tags=["Chat History"]
)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------
# VALID TOOL MODES
# --------------------------------------------------

VALID_MODES = {
    "generate",
    "debug",
    "explain",
    "review",
    "optimize",
    "tests",
    "convert",
}


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class ConversationCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=255)
    mode: str = Field(default="generate", max_length=20)


class MessageCreate(BaseModel):
    role: str
    content: str
    model_name: str | None = None
    response_time: float | None = None


# --------------------------------------------------
# USER ID HELPER
# --------------------------------------------------

def get_user_id(current_user):
    if isinstance(current_user, dict):
        return current_user.get("id")

    return getattr(current_user, "id", None)


# --------------------------------------------------
# CREATE NEW CONVERSATION
# --------------------------------------------------

@router.post("/conversations")
def create_conversation(
    request: ConversationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )

    if request.mode not in VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail="Invalid tool mode"
        )

    try:
        result = db.execute(
            text("""
                INSERT INTO conversations (user_id, title, mode)
                VALUES (:user_id, :title, :mode)
            """),
            {
                "user_id": user_id,
                "title": request.title,
                "mode": request.mode
            }
        )

        conversation_id = result.lastrowid

        db.commit()

        return {
            "success": True,
            "conversation_id": conversation_id,
            "title": request.title,
            "mode": request.mode
        }

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to create conversation"
        )


# --------------------------------------------------
# GET ALL USER CONVERSATIONS
# --------------------------------------------------

@router.get("/conversations")
def get_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )

    try:
        result = db.execute(
            text("""
                SELECT
                    id,
                    title,
                    mode,
                    created_at,
                    updated_at
                FROM conversations
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
            """),
            {"user_id": user_id}
        )

        conversations = [
            dict(row)
            for row in result.mappings().all()
        ]

        return {
            "success": True,
            "conversations": conversations
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversations"
        )


# --------------------------------------------------
# GET MESSAGES FROM A CONVERSATION
# --------------------------------------------------

@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )

    try:
        conversation = db.execute(
            text("""
                SELECT id
                FROM conversations
                WHERE id = :conversation_id
                AND user_id = :user_id
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id
            }
        ).first()

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

        result = db.execute(
            text("""
                SELECT
                    id,
                    role,
                    content,
                    model_name,
                    response_time,
                    created_at
                FROM messages
                WHERE conversation_id = :conversation_id
                AND user_id = :user_id
                ORDER BY id ASC
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id
            }
        )

        messages = [
            dict(row)
            for row in result.mappings().all()
        ]

        return {
            "success": True,
            "conversation_id": conversation_id,
            "messages": messages
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve messages"
        )


# --------------------------------------------------
# SAVE MESSAGE
# --------------------------------------------------

@router.post("/conversations/{conversation_id}/messages")
def save_message(
    conversation_id: int,
    request: MessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )

    if request.role not in ["user", "assistant"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid message role"
        )

    try:
        conversation = db.execute(
            text("""
                SELECT id
                FROM conversations
                WHERE id = :conversation_id
                AND user_id = :user_id
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id
            }
        ).first()

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

        result = db.execute(
            text("""
                INSERT INTO messages (
                    conversation_id,
                    user_id,
                    role,
                    content,
                    model_name,
                    response_time
                )
                VALUES (
                    :conversation_id,
                    :user_id,
                    :role,
                    :content,
                    :model_name,
                    :response_time
                )
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": request.role,
                "content": request.content,
                "model_name": request.model_name,
                "response_time": request.response_time
            }
        )

        message_id = result.lastrowid

        # Update conversation activity
        db.execute(
            text("""
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = :conversation_id
            """),
            {"conversation_id": conversation_id}
        )

        # Automatically generate title from first user message
        if request.role == "user":
            db.execute(
                text("""
                    UPDATE conversations
                    SET title = :title
                    WHERE id = :conversation_id
                    AND title = 'New Chat'
                """),
                {
                    "title": request.content[:50],
                    "conversation_id": conversation_id
                }
            )

        db.commit()

        return {
            "success": True,
            "message_id": message_id
        }

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to save message"
        )


# --------------------------------------------------
# DELETE CONVERSATION
# --------------------------------------------------

@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )

    try:
        result = db.execute(
            text("""
                DELETE FROM conversations
                WHERE id = :conversation_id
                AND user_id = :user_id
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id
            }
        )

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

        db.commit()

        return {
            "success": True,
            "message": "Conversation deleted successfully"
        }

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to delete conversation"
        )