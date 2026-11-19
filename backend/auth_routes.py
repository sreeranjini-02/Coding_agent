import os
import secrets
import hashlib
import base64
import logging
import traceback

from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlencode

from dotenv import load_dotenv

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session
from sqlalchemy import text

from pydantic import BaseModel

from jose import jwt, JWTError

from passlib.context import CryptContext

from authlib.integrations.starlette_client import OAuth

import httpx


# =====================================================
# LOAD ENVIRONMENT
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)


# =====================================================
# LOGGER
# =====================================================

logger = logging.getLogger("zenex.auth")


# =====================================================
# DATABASE
# =====================================================

from backend.database import SessionLocal


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =====================================================
# JWT CONFIGURATION
# =====================================================

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    ""
).strip()

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 1440


if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing from .env"
    )


# =====================================================
# PASSWORD CONFIGURATION
# =====================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# =====================================================
# FRONTEND CONFIGURATION
# =====================================================

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
).rstrip("/")

FRONTEND_LOGIN_URL = (
    f"{FRONTEND_URL}/login"
)

FRONTEND_OAUTH_CALLBACK_URL = (
    f"{FRONTEND_URL}/oauth/callback"
)


# =====================================================
# GOOGLE OAUTH CONFIGURATION
# =====================================================

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    ""
).strip()

GOOGLE_CLIENT_SECRET = os.getenv(
    "GOOGLE_CLIENT_SECRET",
    ""
).strip()

GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/auth/google/callback"
).strip()


oauth = OAuth()


if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:

    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,

        server_metadata_url=(
            "https://accounts.google.com/.well-known/"
            "openid-configuration"
        ),

        client_kwargs={
            "scope": "openid email profile"
        },
    )


# =====================================================
# MICROSOFT OAUTH CONFIGURATION
# =====================================================

MICROSOFT_CLIENT_ID = os.getenv(
    "MICROSOFT_CLIENT_ID",
    ""
).strip()

MICROSOFT_CLIENT_SECRET = os.getenv(
    "MICROSOFT_CLIENT_SECRET",
    ""
).strip()

MICROSOFT_TENANT_ID = os.getenv(
    "MICROSOFT_TENANT_ID",
    "common"
).strip()

MICROSOFT_REDIRECT_URI = os.getenv(
    "MICROSOFT_REDIRECT_URI",
    "http://localhost:8000/auth/microsoft/callback"
).strip()


# =====================================================
# MICROSOFT URL CONFIGURATION
# =====================================================

MICROSOFT_AUTHORITY = (
    f"https://login.microsoftonline.com/"
    f"{MICROSOFT_TENANT_ID}"
)

MICROSOFT_AUTHORIZE_URL = (
    f"{MICROSOFT_AUTHORITY}/oauth2/v2.0/authorize"
)

MICROSOFT_TOKEN_URL = (
    f"{MICROSOFT_AUTHORITY}/oauth2/v2.0/token"
)

MICROSOFT_GRAPH_URL = (
    "https://graph.microsoft.com/v1.0/me"
)


# =====================================================
# PASSWORD HELPERS
# =====================================================

def hash_password(password: str) -> str:

    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# =====================================================
# JWT HELPERS
# =====================================================

def create_access_token(
    data: dict,
    expires_delta=None
):

    to_encode = data.copy()

    if expires_delta:

        expire = (
            datetime.utcnow()
            + expires_delta
        )

    else:

        expire = (
            datetime.utcnow()
            + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# =====================================================
# VERIFY JWT TOKEN
# =====================================================

def verify_token(token: str):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return user_id

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


# =====================================================
# CURRENT USER
# =====================================================

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):

    authorization = request.headers.get(
        "Authorization"
    )

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )

    if not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header"
        )

    token = authorization.replace(
        "Bearer ",
        "",
        1
    )

    user_id = verify_token(token)

    user = db.execute(
        text("""
            SELECT id, username, email
            FROM users
            WHERE id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).fetchone()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email
    }


# =====================================================
# REQUEST MODELS
# =====================================================

class RegisterRequest(BaseModel):

    username: str

    email: str

    password: str


class LoginRequest(BaseModel):

    username_or_email: str

    password: str


# =====================================================
# REGISTER
# =====================================================

@router.post("/register")
def register_user(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):

    existing_user = db.execute(
        text("""
            SELECT id
            FROM users
            WHERE username = :username
               OR email = :email
        """),
        {
            "username": data.username,
            "email": data.email
        }
    ).fetchone()

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )

    hashed_password = hash_password(
        data.password
    )

    db.execute(
        text("""
            INSERT INTO users (
                username,
                email,
                password_hash,
                created_at
            )
            VALUES (
                :username,
                :email,
                :password_hash,
                :created_at
            )
        """),
        {
            "username": data.username,
            "email": data.email,
            "password_hash": hashed_password,
            "created_at": datetime.utcnow()
        }
    )

    db.commit()

    return {
        "message": "User registered successfully"
    }


# =====================================================
# LOGIN
# =====================================================

@router.post("/login")
def login_user(
    data: LoginRequest,
    db: Session = Depends(get_db)
):

    user = db.execute(
        text("""
            SELECT id, username, email, password_hash
            FROM users
            WHERE username = :value
               OR email = :value
        """),
        {
            "value": data.username_or_email
        }
    ).fetchone()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password"
        )

    if not user.password_hash:

        raise HTTPException(
            status_code=401,
            detail="This account uses social login"
        )

    if not verify_password(
        data.password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password"
        )

    access_token = create_access_token(
        {
            "sub": str(user.id)
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }


# =====================================================
# AUTHENTICATED USER
# =====================================================

@router.get("/me")
def get_me(
    current_user=Depends(get_current_user)
):

    return current_user


# =====================================================
# GOOGLE LOGIN
# =====================================================

@router.get("/google/login")
async def google_login(
    request: Request
):

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:

        raise HTTPException(
            status_code=500,
            detail="Google OAuth is not configured"
        )

    try:

        logger.info(
            "Starting Google OAuth"
        )

        # IMPORTANT:
        # Forces Google account selection every time.

        return await oauth.google.authorize_redirect(
            request,
            GOOGLE_REDIRECT_URI,
            prompt="select_account"
        )

    except Exception:

        logger.exception(
            "Google login initiation failed"
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_LOGIN_URL}"
                "?error=google_auth_failed"
                "&stage=google_login"
            ),
            status_code=302
        )


# =====================================================
# GOOGLE CALLBACK
# =====================================================

@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db)
):

    stage = "google_callback_start"

    try:

        # -------------------------------------------------
        # STEP 1: EXCHANGE AUTHORIZATION CODE
        # -------------------------------------------------

        stage = "google_token_exchange"

        token = await oauth.google.authorize_access_token(
            request
        )

        # -------------------------------------------------
        # STEP 2: GET GOOGLE USER INFORMATION
        # -------------------------------------------------

        stage = "google_user_info"

        user_info = token.get(
            "userinfo"
        )

        if not user_info:

            user_info = await oauth.google.userinfo(
                token=token
            )

        if not user_info:

            raise Exception(
                "Google user information is missing"
            )

        # -------------------------------------------------
        # STEP 3: GET EMAIL
        # -------------------------------------------------

        stage = "google_email"

        email = user_info.get(
            "email"
        )

        if not email:

            raise Exception(
                "Google email was not returned"
            )

        # Only link accounts when Google confirms the email.

        if user_info.get("email_verified") is not True:

            raise Exception(
                "Google email is not verified"
            )

        email = email.strip().lower()

        username = (
            user_info.get("name")
            or email.split("@")[0]
        )

        # -------------------------------------------------
        # STEP 4: FIND EXISTING USER
        # -------------------------------------------------

        stage = "google_database_lookup"

        user = db.execute(
            text("""
                SELECT id, username, email
                FROM users
                WHERE email = :email
            """),
            {
                "email": email
            }
        ).fetchone()

        # -------------------------------------------------
        # STEP 5: CREATE USER IF NOT FOUND
        # -------------------------------------------------

        if not user:

            stage = "google_create_user"

            db.execute(
                text("""
                    INSERT INTO users (
                        username,
                        email,
                        password_hash,
                        created_at
                    )
                    VALUES (
                        :username,
                        :email,
                        NULL,
                        :created_at
                    )
                """),
                {
                    "username": username,
                    "email": email,
                    "created_at": datetime.utcnow()
                }
            )

            db.commit()

            user = db.execute(
                text("""
                    SELECT id, username, email
                    FROM users
                    WHERE email = :email
                """),
                {
                    "email": email
                }
            ).fetchone()

        if not user:

            raise Exception(
                "Google user could not be loaded from database"
            )

        # -------------------------------------------------
        # STEP 6: GENERATE ZENEX JWT
        # -------------------------------------------------

        stage = "google_jwt_creation"

        zenex_token = create_access_token(
            {
                "sub": str(user.id)
            }
        )

        # -------------------------------------------------
        # STEP 7: REDIRECT TO FRONTEND
        # -------------------------------------------------

        stage = "google_frontend_redirect"

        redirect_url = (
            f"{FRONTEND_OAUTH_CALLBACK_URL}"
            f"?token={zenex_token}"
        )

        logger.info(
            "Google authentication successful"
        )

        return RedirectResponse(
            url=redirect_url,
            status_code=302
        )

    except Exception as e:

        db.rollback()

        logger.error(
            "Google authentication failed at stage: %s",
            stage
        )

        logger.error(
            "Google error: %s",
            str(e)
        )

        logger.error(
            traceback.format_exc()
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_LOGIN_URL}"
                f"?error=google_auth_failed"
                f"&stage={stage}"
            ),
            status_code=302
        )


# =====================================================
# MICROSOFT PKCE HELPERS
# =====================================================

def generate_pkce():

    verifier = secrets.token_urlsafe(64)

    challenge_bytes = hashlib.sha256(
        verifier.encode("utf-8")
    ).digest()

    challenge = base64.urlsafe_b64encode(
        challenge_bytes
    ).decode("utf-8").rstrip("=")

    return verifier, challenge


# =====================================================
# MICROSOFT LOGIN
# =====================================================

@router.get("/microsoft/login")
async def microsoft_login(
    request: Request
):

    if not MICROSOFT_CLIENT_ID:

        raise HTTPException(
            status_code=500,
            detail="Microsoft Client ID is not configured"
        )

    if not MICROSOFT_CLIENT_SECRET:

        raise HTTPException(
            status_code=500,
            detail="Microsoft Client Secret is not configured"
        )

    try:

        # -------------------------------------------------
        # STEP 1: GENERATE PKCE
        # -------------------------------------------------

        verifier, challenge = generate_pkce()

        # -------------------------------------------------
        # STEP 2: GENERATE STATE
        # -------------------------------------------------

        state = secrets.token_urlsafe(32)

        # -------------------------------------------------
        # STEP 3: SAVE SESSION VALUES
        # -------------------------------------------------

        request.session["microsoft_state"] = state

        request.session["microsoft_verifier"] = verifier

        # -------------------------------------------------
        # STEP 4: BUILD MICROSOFT AUTHORIZATION URL
        # -------------------------------------------------

        params = {
            "client_id": MICROSOFT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": MICROSOFT_REDIRECT_URI,
            "response_mode": "query",
            "scope": "openid profile email User.Read",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "prompt": "select_account"
        }

        authorization_url = (
            f"{MICROSOFT_AUTHORIZE_URL}"
            f"?{urlencode(params)}"
        )

        logger.info(
            "Starting Microsoft OAuth login"
        )

        return RedirectResponse(
            url=authorization_url,
            status_code=302
        )

    except Exception:

        logger.exception(
            "Microsoft login initialization failed"
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_LOGIN_URL}"
                "?error=microsoft_auth_failed"
                "&stage=microsoft_login"
            ),
            status_code=302
        )


# =====================================================
# MICROSOFT CALLBACK
# =====================================================

@router.get("/microsoft/callback")
async def microsoft_callback(
    request: Request,
    db: Session = Depends(get_db)
):

    stage = "microsoft_callback_start"

    try:

        # -------------------------------------------------
        # STEP 1: CHECK MICROSOFT ERROR
        # -------------------------------------------------

        microsoft_error = request.query_params.get(
            "error"
        )

        microsoft_error_description = (
            request.query_params.get(
                "error_description"
            )
        )

        if microsoft_error:

            logger.error(
                "Microsoft authorization error: %s - %s",
                microsoft_error,
                microsoft_error_description
            )

            return RedirectResponse(
                url=(
                    f"{FRONTEND_LOGIN_URL}"
                    "?error=microsoft_auth_failed"
                    "&stage=microsoft_authorization"
                ),
                status_code=302
            )

        # -------------------------------------------------
        # STEP 2: GET AUTHORIZATION CODE
        # -------------------------------------------------

        stage = "microsoft_authorization_code"

        code = request.query_params.get(
            "code"
        )

        if not code:

            raise Exception(
                "Microsoft authorization code missing"
            )

        # -------------------------------------------------
        # STEP 3: VALIDATE STATE
        # -------------------------------------------------

        stage = "microsoft_state_validation"

        received_state = request.query_params.get(
            "state"
        )

        stored_state = request.session.get(
            "microsoft_state"
        )

        if not received_state or not stored_state:

            raise Exception(
                "Microsoft OAuth state missing"
            )

        if not secrets.compare_digest(
            received_state,
            stored_state
        ):

            raise Exception(
                "Microsoft OAuth state mismatch"
            )

        # -------------------------------------------------
        # STEP 4: GET PKCE VERIFIER
        # -------------------------------------------------

        stage = "microsoft_pkce_verifier"

        verifier = request.session.get(
            "microsoft_verifier"
        )

        if not verifier:

            raise Exception(
                "Microsoft PKCE verifier missing"
            )

        # -------------------------------------------------
        # STEP 5: EXCHANGE AUTHORIZATION CODE FOR TOKEN
        # -------------------------------------------------

        stage = "microsoft_token_exchange"

        token_payload = {
            "client_id": MICROSOFT_CLIENT_ID,
            "client_secret": MICROSOFT_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": MICROSOFT_REDIRECT_URI,
            "code_verifier": verifier,
            "scope": "openid profile email User.Read"
        }

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            token_response = await client.post(
                MICROSOFT_TOKEN_URL,
                data=token_payload,
                headers={
                    "Content-Type": (
                        "application/x-www-form-urlencoded"
                    )
                }
            )

        if token_response.status_code != 200:

            # Do not log token contents or secrets.

            try:
                error_data = token_response.json()

                logger.error(
                    "Microsoft token exchange error: %s",
                    error_data.get("error")
                )

                logger.error(
                    "Microsoft error description: %s",
                    error_data.get("error_description")
                )

            except Exception:

                logger.error(
                    "Microsoft token exchange failed with HTTP %s",
                    token_response.status_code
                )

            raise Exception(
                "Microsoft token exchange unsuccessful"
            )

        token_data = token_response.json()

        microsoft_access_token = token_data.get(
            "access_token"
        )

        if not microsoft_access_token:

            raise Exception(
                "Microsoft access token missing"
            )

        # -------------------------------------------------
        # STEP 6: GET MICROSOFT USER INFORMATION
        # -------------------------------------------------

        stage = "microsoft_user_info"

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            graph_response = await client.get(
                MICROSOFT_GRAPH_URL,
                headers={
                    "Authorization": (
                        f"Bearer {microsoft_access_token}"
                    )
                }
            )

        if graph_response.status_code != 200:

            logger.error(
                "Microsoft Graph failed with HTTP %s",
                graph_response.status_code
            )

            raise Exception(
                "Microsoft Graph user information failed"
            )

        microsoft_user = graph_response.json()

        # -------------------------------------------------
        # STEP 7: GET EMAIL
        # -------------------------------------------------

        stage = "microsoft_email"

        email = (
            microsoft_user.get("mail")
            or microsoft_user.get("userPrincipalName")
        )

        if not email:

            raise Exception(
                "Microsoft email not found"
            )

        email = email.strip().lower()

        username = (
            microsoft_user.get("displayName")
            or email.split("@")[0]
        )

        # -------------------------------------------------
        # STEP 8: FIND EXISTING USER
        # -------------------------------------------------

        stage = "microsoft_database_user"

        user = db.execute(
            text("""
                SELECT id, username, email
                FROM users
                WHERE email = :email
            """),
            {
                "email": email
            }
        ).fetchone()

        # -------------------------------------------------
        # STEP 9: CREATE USER IF NOT FOUND
        # -------------------------------------------------

        if not user:

            db.execute(
                text("""
                    INSERT INTO users (
                        username,
                        email,
                        password_hash,
                        created_at
                    )
                    VALUES (
                        :username,
                        :email,
                        NULL,
                        :created_at
                    )
                """),
                {
                    "username": username,
                    "email": email,
                    "created_at": datetime.utcnow()
                }
            )

            db.commit()

            user = db.execute(
                text("""
                    SELECT id, username, email
                    FROM users
                    WHERE email = :email
                """),
                {
                    "email": email
                }
            ).fetchone()

        if not user:

            raise Exception(
                "Microsoft user could not be loaded from database"
            )

        # -------------------------------------------------
        # STEP 10: CREATE ZENEX JWT
        # -------------------------------------------------

        stage = "microsoft_jwt_creation"

        zenex_token = create_access_token(
            {
                "sub": str(user.id)
            }
        )

        # -------------------------------------------------
        # STEP 11: CLEAR MICROSOFT SESSION
        # -------------------------------------------------

        request.session.pop(
            "microsoft_state",
            None
        )

        request.session.pop(
            "microsoft_verifier",
            None
        )

        # -------------------------------------------------
        # STEP 12: FRONTEND REDIRECT
        # -------------------------------------------------

        stage = "microsoft_frontend_redirect"

        redirect_url = (
            f"{FRONTEND_OAUTH_CALLBACK_URL}"
            f"?token={zenex_token}"
        )

        logger.info(
            "Microsoft authentication successful"
        )

        return RedirectResponse(
            url=redirect_url,
            status_code=302
        )

    except Exception as e:

        db.rollback()

        logger.error(
            "Microsoft authentication failed at stage: %s",
            stage
        )

        logger.error(
            "Microsoft error: %s",
            str(e)
        )

        logger.error(
            traceback.format_exc()
        )

        # Clear session values on failure.

        request.session.pop(
            "microsoft_state",
            None
        )

        request.session.pop(
            "microsoft_verifier",
            None
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_LOGIN_URL}"
                "?error=microsoft_auth_failed"
                f"&stage={stage}"
            ),
            status_code=302
        )