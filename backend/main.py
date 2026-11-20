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

# Chat history
from backend.chat_routes import router as chat_router

# Coding agent
from coding_agent import prepare_agent_prompt

# File extraction
from rag_engine import extract_text, SUPPORTED_EXTENSIONS

# Gemini streaming
from llm_service import generate_response_stream


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
    ]
)


# =====================================================
# REGISTER ROUTERS
# =====================================================

app.include_router(auth_router)

app.include_router(file_router)

app.include_router(chat_router)


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
# CODING AGENT API
# =====================================================

@app.post("/coding-agent")
async def coding_agent_api(

    prompt: str = Form(...),

    mode: str = Form("generate"),

    model: str = Form("gemini-3.5-flash-lite"),

    auto_fallback: bool = Form(False),

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

        uploaded_context = ""

        # =================================================
        # UPLOADED FILE PROCESSING AND STORAGE
        # =================================================

        if file:

            filename = os.path.basename(
                file.filename or "uploaded_file"
            )

            extension = Path(filename).suffix.lower()

            # ---------------------------------------------
            # VALIDATE FILE TYPE
            # ---------------------------------------------

            if extension not in SUPPORTED_EXTENSIONS:

                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {extension}"
                )

            # ---------------------------------------------
            # READ FILE
            # ---------------------------------------------

            file_content = await file.read()

            if not file_content:

                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is empty."
                )

            # ---------------------------------------------
            # SAVE FILE
            # ---------------------------------------------

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

            # ---------------------------------------------
            # TEMPORARY FILE FOR EXTRACTION
            # ---------------------------------------------

            stored_path = Path(
                file_data["file_path"]
            )

            if not stored_path.exists():

                raise HTTPException(
                    status_code=500,
                    detail="Uploaded file could not be located."
                )

            # ---------------------------------------------
            # EXTRACT FILE CONTENT
            # ---------------------------------------------

            uploaded_context = extract_text(
                stored_path
            )

            if not uploaded_context.strip():

                raise HTTPException(
                    status_code=400,
                    detail="No readable content found in uploaded file."
                )

            # ---------------------------------------------
            # CONTEXT LIMIT
            # ---------------------------------------------

            uploaded_context = uploaded_context[:30000]

            logger.info(
                "File content extracted successfully | "
                "Filename=%s | Characters=%s",
                filename,
                len(uploaded_context)
            )

        # =================================================
        # PROMPT VALIDATION
        # =================================================

        if not prompt.strip():

            raise HTTPException(
                status_code=400,
                detail="Prompt cannot be empty"
            )

        # =================================================
        # PREPARE AGENT PROMPT
        # =================================================

        final_prompt = prepare_agent_prompt(
            question=prompt,
            mode=mode,
            uploaded_context=uploaded_context
        )

        # =================================================
        # STREAM RESPONSE
        # =================================================

        def response_generator():

            try:

                for chunk in generate_response_stream(
                    prompt=final_prompt,
                    selected_model=model,
                    context=""
                ):

                    yield chunk

                elapsed = round(
                    time.perf_counter() - start_time,
                    2
                )

                logger.info(
                    "Streaming completed | "
                    "User=%s | Model=%s | Time=%ss",
                    user_id,
                    model,
                    elapsed
                )

            except Exception:

                logger.exception(
                    "Streaming generation failed"
                )

                yield "\n\nError: Unable to generate response."

        return StreamingResponse(
            response_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
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