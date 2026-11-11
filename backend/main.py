import logging
import json
import time

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

# Authentication
from backend.auth_routes import (
    router as auth_router,
    verify_token
)

# File routes
from backend.file_routes import router as file_router

# Chat history
from backend.chat_routes import router as chat_router

# Coding agent
from coding_agent import run_coding_agent, prepare_agent_prompt

# Gemini streaming
from llm_service import generate_response_stream


# =========================
# LOGGING
# =========================

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# =========================
# FASTAPI APPLICATION
# =========================

app = FastAPI(
    title="AI Coding Agent",
    description="AI Coding Agent with JWT Authentication, MySQL, RAG and Chat History",
    version="1.0.0"
)


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =========================
# REGISTER ROUTERS
# =========================

app.include_router(auth_router)
app.include_router(file_router)
app.include_router(chat_router)


# =========================
# HOME
# =========================

@app.get("/")
def home():

    return {
        "success": True,
        "message": "AI Coding Agent Backend Running",
        "version": "1.0.0"
    }


# =========================
# HEALTH CHECK
# =========================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "application": "AI Coding Agent"
    }


# =========================
# CODING AGENT API
# =========================

@app.post("/coding-agent")
async def coding_agent_api(

    prompt: str = Form(...),

    mode: str = Form("generate"),

    model: str = Form("gemini-3.5-flash-lite"),

    auto_fallback: bool = Form(False),

    file: UploadFile | None = File(None),

    current_user: dict = Depends(verify_token)

):

    try:

        start_time = time.perf_counter()

        logger.info("Coding Agent request received")

        # =========================
        # AUTHENTICATED USER
        # =========================

        user_id = current_user.get("sub")

        if not user_id:

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        logger.info(
            "Authenticated user ID: %s",
            user_id
        )

        # =========================
        # FILE CONTEXT
        # =========================

        uploaded_context = ""

        if file:

            filename = file.filename or "uploaded_file"

            file_extension = filename.lower().split(".")[-1]

            supported_text_extensions = {
                "txt",
                "py",
                "java",
                "js",
                "jsx",
                "ts",
                "tsx",
                "html",
                "css",
                "json",
                "sql",
                "md",
                "csv"
            }

            if file_extension in supported_text_extensions:

                file_content = await file.read()

                uploaded_context = file_content.decode(
                    "utf-8",
                    errors="ignore"
                )

                uploaded_context = uploaded_context[:12000]

                logger.info(
                    "Uploaded text file processed: %s",
                    filename
                )

            else:

                logger.info(
                    "Uploaded file: %s. "
                    "Document extraction is not implemented here.",
                    filename
                )

        # =========================
        # VALIDATE PROMPT
        # =========================

        if not prompt.strip():

            raise HTTPException(
                status_code=400,
                detail="Prompt cannot be empty"
            )

        # =========================
        # PREPARE AGENT PROMPT
        # =========================

        final_prompt = prepare_agent_prompt(
            question=prompt,
            mode=mode,
            uploaded_context=uploaded_context
        )

        # =========================
        # STREAM RESPONSE
        # =========================

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
                    "Streaming response completed | "
                    "User=%s | Model=%s | Time=%ss",
                    user_id,
                    model,
                    elapsed
                )

            except Exception as error:

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


# =========================
# STARTUP
# =========================

@app.on_event("startup")
async def startup_event():

    logger.info("AI Coding Agent Backend Started")

    logger.info("Authentication: Enabled")

    logger.info("MySQL Chat History: Enabled")

    logger.info("Uploaded Files: Enabled")

    logger.info("Coding Agent: Enabled")
