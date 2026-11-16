import os
import logging
import secrets

from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlencode

from dotenv import load_dotenv

# =====================================================
# LOAD ENVIRONMENT VARIABLES
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)


# =====================================================
# IMPORTS
# =====================================================

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from starlette.requests import Request

from pydantic import BaseModel, EmailStr, Field

from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from passlib.context import CryptContext
from jose import jwt, JWTError

from authlib.integrations.starlette_client import OAuth

from backend.database import SessionLocal


# =====================================================
# LOGGER
# =====================================================

logger = logging.getLogger(__name__)


# =====================================================
# ROUTER
# =====================================================

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# =====================================================
# JWT CONFIGURATION
# =====================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing from root .env"
    )

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 1440

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

security = HTTPBearer()


# =====================================================
# GOOGLE OAUTH CONFIGURATION
# =====================================================

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID", ""
).strip()

GOOGLE_CLIENT_SECRET = os.getenv(
    "GOOGLE_CLIENT_SECRET", ""
).strip()

GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/auth/google/callback"
).strip()

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
).strip()


# =====================================================
# OAUTH CLIENT
# =====================================================

oauth = OAuth()

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:

    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=(
            "https://accounts.google.com/.well-known/openid-configuration"
        ),
        client_kwargs={
            "scope": "openid email profile"
        }
    )


# =====================================================
# GOOGLE OAUTH CONFIGURATION LOGS
# =====================================================

print("\n========== GOOGLE OAUTH CONFIG ==========")

print(
    "Google Client ID Loaded:",
    bool(GOOGLE_CLIENT_ID)
)

print(
    "Google Client ID Format:",
    GOOGLE_CLIENT_ID.endswith(
        ".apps.googleusercontent.com"
    )
)

print(
    "Google Client Secret Loaded:",
    bool(GOOGLE_CLIENT_SECRET)
)

print(
    "Google Redirect URI:",
    GOOGLE_REDIRECT_URI
)

print(
    "Frontend URL:",
    FRONTEND_URL
)

print("=======================================\n")


# =====================================================
# DATABASE DEPENDENCY
# =====================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =====================================================
# REQUEST MODELS
# =====================================================

class RegisterRequest(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=50
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=72
    )


class LoginRequest(BaseModel):

    username_or_email: str

    password: str


# =====================================================
# PASSWORD FUNCTIONS
# =====================================================

def hash_password(password: str):

    if len(password.encode("utf-8")) > 72:

        raise HTTPException(
            status_code=400,
            detail="Password cannot exceed 72 bytes"
        )

    return pwd_context.hash(password)


def verify_password(
    password: str,
    hashed_password: str
):

    return pwd_context.verify(
        password,
        hashed_password
    )


# =====================================================
# JWT FUNCTIONS
# =====================================================

def create_access_token(data: dict):

    payload = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_token(token: str):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        if not payload.get("sub"):

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        return payload

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token"
        )


# =====================================================
# CURRENT USER DEPENDENCY
# =====================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):

    payload = verify_token(
        credentials.credentials
    )

    user_id = payload.get("sub")

    user = db.execute(
        text("""
            SELECT id, username, email
            FROM users
            WHERE id = :user_id
        """),
        {"user_id": user_id}
    ).mappings().first()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return dict(user)


# =====================================================
# REGISTER
# =====================================================

@router.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):

    username = request.username.strip()

    email = request.email.lower().strip()

    password_hash = hash_password(
        request.password
    )

    try:

        db.execute(
            text("""
                INSERT INTO users
                (username, email, password_hash)
                VALUES
                (:username, :email, :password_hash)
            """),
            {
                "username": username,
                "email": email,
                "password_hash": password_hash
            }
        )

        db.commit()

        return {
            "message": "Registration successful"
        }

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Username or email already exists"
        )

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error during registration"
        )


# =====================================================
# LOGIN
# =====================================================

@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    identifier = request.username_or_email.strip()

    user = db.execute(
        text("""
            SELECT id, username, email, password_hash
            FROM users
            WHERE LOWER(username) = LOWER(:identifier)
               OR LOWER(email) = LOWER(:identifier)
            LIMIT 1
        """),
        {"identifier": identifier}
    ).mappings().first()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password"
        )

    if not verify_password(
        request.password,
        user["password_hash"]
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password"
        )

    access_token = create_access_token({
        "sub": str(user["id"]),
        "email": user["email"]
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    }


# =====================================================
# CURRENT USER
# =====================================================

@router.get("/me")
def get_me(
    current_user: dict = Depends(get_current_user)
):

    return current_user


# =====================================================
# GOOGLE LOGIN
# =====================================================

@router.get("/google/login")
async def google_login(request: Request):

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:

        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials missing in .env"
        )

    if not GOOGLE_CLIENT_ID.endswith(
        ".apps.googleusercontent.com"
    ):

        raise HTTPException(
            status_code=500,
            detail="Google Client ID format is invalid"
        )

    # Diagnostic: inspect session before starting OAuth
    logger.info(
        "Google OAuth login started | Session keys: %s",
        list(request.session.keys())
    )

    # Start OAuth using Authlib's session-based state
    response = await oauth.google.authorize_redirect(
        request,
        GOOGLE_REDIRECT_URI,
        prompt="select_account"
    )

    logger.info(
        "Google OAuth authorization redirect created"
    )

    return response


# =====================================================
# GOOGLE CALLBACK
# =====================================================

@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db)
):

    try:

        # -------------------------------------------------
        # DEBUG SESSION STATE
        # -------------------------------------------------

        received_state = request.query_params.get("state")

        session_keys = list(request.session.keys())

        logger.info(
            "Google callback received | State present: %s | Session keys: %s",
            bool(received_state),
            session_keys
        )

        # -------------------------------------------------
        # EXCHANGE GOOGLE AUTHORIZATION CODE
        # -------------------------------------------------

        token = await oauth.google.authorize_access_token(
            request
        )

        logger.info(
            "Google OAuth token successfully received"
        )

        # -------------------------------------------------
        # GOOGLE USER INFORMATION
        # -------------------------------------------------

        google_user = token.get("userinfo")

        if not google_user:

            google_user = await oauth.google.userinfo(
                token=token
            )

        if not google_user:

            raise HTTPException(
                status_code=400,
                detail="Unable to retrieve Google user information"
            )

        email = google_user.get("email")

        email_verified = google_user.get(
            "email_verified",
            False
        )

        if not email or not email_verified:

            raise HTTPException(
                status_code=400,
                detail="Google email is not verified"
            )

        email = email.lower().strip()

        # -------------------------------------------------
        # FIND EXISTING USER
        # -------------------------------------------------

        user = db.execute(
            text("""
                SELECT id, username, email
                FROM users
                WHERE LOWER(email) = :email
                LIMIT 1
            """),
            {"email": email}
        ).mappings().first()

        # -------------------------------------------------
        # CREATE GOOGLE USER IF NOT EXISTS
        # -------------------------------------------------

        if not user:

            base_username = (
                google_user.get("name")
                or email.split("@")[0]
            ).replace(" ", "_")

            username = base_username[:45]

            counter = 1

            while db.execute(
                text("""
                    SELECT id
                    FROM users
                    WHERE LOWER(username) = LOWER(:username)
                    LIMIT 1
                """),
                {"username": username}
            ).first():

                username = f"{base_username[:40]}_{counter}"

                counter += 1

            password_hash = pwd_context.hash(
                os.urandom(32).hex()
            )

            db.execute(
                text("""
                    INSERT INTO users
                    (username, email, password_hash)
                    VALUES
                    (:username, :email, :password_hash)
                """),
                {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash
                }
            )

            db.commit()

            user = db.execute(
                text("""
                    SELECT id, username, email
                    FROM users
                    WHERE LOWER(email) = :email
                    LIMIT 1
                """),
                {"email": email}
            ).mappings().first()

        # -------------------------------------------------
        # CREATE APPLICATION JWT
        # -------------------------------------------------

        access_token = create_access_token({
            "sub": str(user["id"]),
            "email": user["email"]
        })

        logger.info(
            "Google authentication successful for user ID: %s",
            user["id"]
        )

        # -------------------------------------------------
        # REDIRECT TO FRONTEND
        # -------------------------------------------------

        frontend_url = FRONTEND_URL.rstrip("/")

        return RedirectResponse(
            url=(
                f"{frontend_url}/oauth/callback?"
                f"{urlencode({'token': access_token})}"
            ),
            status_code=302
        )

    except HTTPException:

        db.rollback()

        raise

    except Exception as error:

        db.rollback()

        logger.exception(
            "Google OAuth Callback Error"
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_URL.rstrip('/')}/login?"
                f"{urlencode({'error': 'google_auth_failed'})}"
            ),
            status_code=302
        )