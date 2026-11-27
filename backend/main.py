import logging
import time
import os

from pathlib import Path
from dotenv import load_dotenv

# =====================================================
# LOAD ENVIRONMENT VARIABLES
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)


# =====================================================
# IMPORTS
# =====================================================

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends
)

from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import text

# Authentication
from backend.auth_routes import (
    router as auth_router,
    get_current_user
)

# File routes and storage
from backend.file_routes import (
    router as file_router,
    store_uploaded_file
)

# Database
from backend.file_routes import get_db
from backend.database import SessionLocal

# Chat history
from backend.chat_routes import router as chat_router

# Code tools (syntax check)
from backend.code_routes import router as code_router

# Coding agent
from coding_agent import prepare_agent_prompt

# File extraction
from rag_engine import extract_text, SUPPORTED_EXTENSIONS

# Gemini streaming with fallback and overload retry
from llm_service import open_stream_with_fallback


# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)


# =====================================================
# ENVIRONMENT CONFIGURATION
# =====================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    ""
).strip()

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
).strip().rstrip("/")

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing from root .env"
    )


# =====================================================
# ALLOWED MODELS
# =====================================================

ALLOWED_MODELS = {
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
}


# =====================================================
# FASTAPI APPLICATION
# =====================================================

app = FastAPI(
    title="ZENEX",
    description="ZENEX - Intelligent AI Coding Assistant",
    version="1.0.0"
)


# =====================================================
# SESSION MIDDLEWARE
# =====================================================

app.add_middleware(
    SessionMiddleware,
    secret_key=JWT_SECRET_KEY,
    session_cookie="zenex_session",
    same_site="lax",
    https_only=False,
    max_age=600
)


# =====================================================
# CORS MIDDLEWARE
# =====================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],

    allow_credentials=True,

    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS"
    ],

    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept"
    ],

    # Lets the browser read these custom response headers
    expose_headers=[
        "X-Active-Model",
        "X-Fallback-Used"
    ]
)


# =====================================================
# REGISTER ROUTERS
# =====================================================

app.include_router(auth_router)

app.include_router(file_router)

app.include_router(chat_router)

app.include_router(code_router)


# =====================================================
# HOME
# =====================================================

@app.get("/")
def home():

    return {
        "success": True,
        "message": "AI Coding Agent Backend Running",
        "version": "1.0.0"
    }


# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "application": "AI Coding Agent"
    }


# =====================================================
# CONVERSATION HISTORY HELPER
# =====================================================

def get_conversation_history(
    conversation_id: int,
    user_id: int,
    db
):
    """
    Retrieve conversation history belonging to the
    authenticated user and selected conversation.
    """

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
            detail="Conversation not found."
        )

    result = db.execute(
        text("""
            SELECT
                role,
                content
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

    history = [
        dict(row)
        for row in result.mappings().all()
    ]

    logger.info(
        "Conversation history retrieved | "
        "Conversation=%s | Messages=%s",
        conversation_id,
        len(history)
    )

    return history


# =====================================================
# SAVE ASSISTANT REPLY (OWN DATABASE SESSION)
# =====================================================

def save_assistant_reply(
    conversation_id,
    user_id,
    content,
    model_name,
    response_time
):
    """
    Saves the assistant reply using its own database session.
    The request's session may already be closed once streaming
    has started, so this does not depend on it.
    """

    save_db = SessionLocal()

    try:

        save_db.execute(
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
                    'assistant',
                    :content,
                    :model_name,
                    :response_time
                )
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "content": content,
                "model_name": model_name,
                "response_time": response_time,
            }
        )

        save_db.execute(
            text("""
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = :conversation_id
                  AND user_id = :user_id
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id
            }
        )

        save_db.commit()

    except Exception:

        save_db.rollback()
        raise

    finally:

        save_db.close()


# =====================================================
# CODING AGENT API
# =====================================================

@app.post("/coding-agent")
async def coding_agent_api(

    prompt: str = Form(...),

    mode: str = Form("generate"),

    model: str = Form("gemini-3.5-flash-lite"),

    auto_fallback: bool = Form(False),

    conversation_id: int = Form(...),

    file: UploadFile | None = File(None),

    current_user: dict = Depends(get_current_user),

    db=Depends(get_db)

):

    try:

        start_time = time.perf_counter()

        logger.info(
            "Coding Agent request received"
        )

        # =================================================
        # USER AUTHENTICATION
        # =================================================

        user_id = current_user.get("id")

        if not user_id:

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        logger.info(
            "Authenticated user ID: %s",
            user_id
        )

        # =================================================
        # VALIDATE MODEL
        # =================================================

        if model not in ALLOWED_MODELS:

            raise HTTPException(
                status_code=400,
                detail="Unsupported model selected."
            )

        # =================================================
        # VALIDATE QUESTION
        # =================================================

        if not prompt or not prompt.strip():

            raise HTTPException(
                status_code=400,
                detail="Prompt cannot be empty"
            )

        prompt = prompt.strip()

        # =================================================
        # FETCH CONVERSATION HISTORY
        # =================================================

        conversation_history = get_conversation_history(
            conversation_id=conversation_id,
            user_id=user_id,
            db=db
        )

        # The frontend saves the user's message before calling
        # this route, so it is already the last history entry.
        # Remove it here, because the prompt already includes it.
        if (
            conversation_history
            and conversation_history[-1]["role"] == "user"
            and conversation_history[-1]["content"].strip() == prompt
        ):
            conversation_history = conversation_history[:-1]

        # =================================================
        # UPLOADED FILE CONTEXT
        # =================================================

        uploaded_context = ""

        if file:

            filename = os.path.basename(
                file.filename or "uploaded_file"
            )

            extension = Path(filename).suffix.lower()

            if extension not in SUPPORTED_EXTENSIONS:

                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {extension}"
                )

            file_content = await file.read()

            if not file_content:

                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is empty."
                )

            file_data = store_uploaded_file(
                user_id=user_id,
                filename=filename,
                file_content=file_content,
                db=db
            )

            logger.info(
                "File saved successfully: %s",
                filename
            )

            logger.info(
                "Stored filename: %s",
                file_data["stored_filename"]
            )

            stored_path = Path(
                file_data["file_path"]
            )

            if not stored_path.exists():

                raise HTTPException(
                    status_code=500,
                    detail="Uploaded file could not be located."
                )

            uploaded_context = extract_text(
                stored_path
            )

            if not uploaded_context.strip():

                raise HTTPException(
                    status_code=400,
                    detail="No readable content found in uploaded file."
                )

            uploaded_context = uploaded_context[:30000]

            logger.info(
                "File content extracted successfully | "
                "Filename=%s | Characters=%s",
                filename,
                len(uploaded_context)
            )

        # =================================================
        # PREPARE AGENT PROMPT WITH HISTORY
        # =================================================

        final_prompt = prepare_agent_prompt(
            question=prompt,
            mode=mode,
            uploaded_context=uploaded_context,
            conversation_history=conversation_history
        )

        logger.info(
            "Agent prompt prepared | "
            "History messages=%s",
            len(conversation_history)
        )

        # =================================================
        # OPEN STREAM (retries overloaded models, then falls back)
        # =================================================

        try:

            stream_info = open_stream_with_fallback(
                prompt=final_prompt,
                selected_model=model,
                auto_fallback=auto_fallback
            )

        except RuntimeError:

            raise HTTPException(
                status_code=503,
                detail="All models failed to respond. Please try again."
            )

        active_model = stream_info["active_model"]
        fallback_used = stream_info["fallback_used"]

        # =================================================
        # STREAM RESPONSE
        # =================================================

        def response_generator():

            full_response = ""

            try:

                for chunk in stream_info["stream"]:

                    if not chunk:
                        continue

                    full_response += chunk

                    yield chunk

            except Exception:

                logger.exception(
                    "Streaming failed"
                )

                yield "\n\nError: The response stopped early."
                return

            # The reply is already streamed. Saving happens separately,
            # so a save problem is logged instead of replacing the reply.
            if full_response.strip():

                try:

                    save_assistant_reply(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        content=full_response,
                        model_name=active_model,
                        response_time=round(
                            time.perf_counter() - start_time,
                            2
                        ),
                    )

                    logger.info(
                        "Reply saved | Conversation=%s | Model=%s",
                        conversation_id,
                        active_model,
                    )

                except Exception:

                    logger.exception(
                        "Saving the assistant reply failed"
                    )

        return StreamingResponse(
            response_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Active-Model": active_model,
                "X-Fallback-Used": "true" if fallback_used else "false"
            }
        )

    except HTTPException:

        raise

    except Exception as e:

        logger.exception(
            "Coding Agent failed"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =====================================================
# STARTUP EVENT
# =====================================================

@app.on_event("startup")
async def startup_event():

    logger.info(
        "=========================================="
    )

    logger.info(
        "ZENEX Backend Started Successfully"
    )

    logger.info(
        "Authentication: Enabled"
    )

    logger.info(
        "Google OAuth: %s",
        "Enabled"
        if os.getenv("GOOGLE_CLIENT_ID")
        and os.getenv("GOOGLE_CLIENT_SECRET")
        else "Not configured"
    )

    logger.info(
        "Microsoft OAuth: %s",
        "Enabled"
        if os.getenv("MICROSOFT_CLIENT_ID")
        else "Not configured"
    )

    logger.info(
        "MySQL Chat History: Enabled"
    )

    logger.info(
        "Conversation Context: Enabled"
    )

    logger.info(
        "Uploaded Files: Enabled"
    )

    logger.info(
        "Coding Agent: Enabled"
    )

    logger.info(
        "Frontend: %s",
        FRONTEND_URL
    )

    logger.info(
        "=========================================="
    )