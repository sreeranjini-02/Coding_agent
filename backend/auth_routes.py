import os
import secrets
import hashlib
import base64
import logging
import traceback
import smtplib

from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlencode

from email.message import EmailMessage

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

from pydantic import BaseModel, EmailStr

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
# EMAIL CONFIGURATION
# =====================================================

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com"
).strip()

SMTP_PORT = int(
    os.getenv("SMTP_PORT", "587")
)

SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME",
    ""
).strip()

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD",
    ""
).strip()

EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    SMTP_USERNAME
).strip()


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
# PASSWORD RESET TOKEN HELPERS
# =====================================================

def hash_reset_token(token: str) -> str:

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


# =====================================================
# SEND PASSWORD RESET EMAIL
# =====================================================

def send_password_reset_email(
    recipient_email: str,
    reset_link: str
):

    if not SMTP_USERNAME or not SMTP_PASSWORD:

        raise RuntimeError(
            "SMTP configuration is missing in .env"
        )

    message = EmailMessage()

    message["Subject"] = (
        "ZENEX AI - Reset Your Password"
    )

    message["From"] = EMAIL_FROM

    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

We received a request to reset your ZENEX AI account password.

Click the following link to reset your password:

{reset_link}

This link expires in 30 minutes.

If you did not request this password reset,
you can safely ignore this email.

Regards,
ZENEX AI Team
"""
    )

    message.add_alternative(
        f"""
        <html>
            <body style="font-family:Arial,sans-serif;background:#0b0b0f;color:#ffffff;padding:30px;">

                <div style="max-width:500px;margin:auto;background:#15151b;padding:30px;border-radius:15px;">

                    <h2 style="color:#a78bfa;">ZENEX AI</h2>

                    <h3>Reset Your Password</h3>

                    <p>
                        We received a request to reset your password.
                    </p>

                    <p>
                        Click the button below to create a new password.
                    </p>

                    <a href="{reset_link}"
                       style="display:inline-block;background:#7c3aed;color:white;padding:14px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">

                        Reset Password

                    </a>

                    <p style="margin-top:25px;color:#aaaaaa;">
                        This link expires in 30 minutes.
                    </p>

                    <p style="color:#aaaaaa;">
                        If you did not request this, you can ignore this email.
                    </p>

                    <p>ZENEX AI Team</p>

                </div>

            </body>
        </html>
        """,
        subtype="html"
    )

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=30
    ) as server:

        server.starttls()

        server.login(
            SMTP_USERNAME,
            SMTP_PASSWORD
        )

        server.send_message(message)


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


class ForgotPasswordRequest(BaseModel):

    email: EmailStr


class ResetPasswordRequest(BaseModel):

    token: str

    new_password: str


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
# FORGOT PASSWORD
# =====================================================

@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):

    email = str(
        data.email
    ).strip().lower()

    generic_message = (
        "If your account exists, "
        "a password reset link has been sent."
    )

    # -------------------------------------------------
    # FIND USER
    # -------------------------------------------------

    user = db.execute(
        text("""
            SELECT id, email
            FROM users
            WHERE LOWER(email) = :email
        """),
        {
            "email": email
        }
    ).fetchone()

    # -------------------------------------------------
    # ACCOUNT NOT FOUND
    # -------------------------------------------------

    if not user:

        return {
            "message": generic_message
        }

    # -------------------------------------------------
    # GENERATE SECURE TOKEN
    # -------------------------------------------------

    reset_token = secrets.token_urlsafe(32)

    token_hash = hash_reset_token(
        reset_token
    )

    expires_at = (
        datetime.utcnow()
        + timedelta(minutes=30)
    )

    # -------------------------------------------------
    # INVALIDATE OLD TOKENS
    # -------------------------------------------------

    db.execute(
        text("""
            UPDATE password_reset_tokens
            SET used_at = NOW()
            WHERE user_id = :user_id
              AND used_at IS NULL
        """),
        {
            "user_id": user.id
        }
    )

    # -------------------------------------------------
    # STORE TOKEN HASH
    # -------------------------------------------------

    db.execute(
        text("""
            INSERT INTO password_reset_tokens (
                user_id,
                token_hash,
                expires_at,
                created_at
            )
            VALUES (
                :user_id,
                :token_hash,
                :expires_at,
                NOW()
            )
        """),
        {
            "user_id": user.id,
            "token_hash": token_hash,
            "expires_at": expires_at
        }
    )

    db.commit()

    # -------------------------------------------------
    # CREATE RESET LINK
    # -------------------------------------------------

    reset_link = (
        f"{FRONTEND_URL}/reset-password"
        f"?token={reset_token}"
    )

    # -------------------------------------------------
    # SEND EMAIL
    # -------------------------------------------------

    try:

        send_password_reset_email(
            recipient_email=user.email,
            reset_link=reset_link
        )

    except Exception:

        logger.exception(
            "Password reset email failed"
        )

        # Invalidate token if email fails.

        db.execute(
            text("""
                UPDATE password_reset_tokens
                SET used_at = NOW()
                WHERE token_hash = :token_hash
            """),
            {
                "token_hash": token_hash
            }
        )

        db.commit()

        raise HTTPException(
            status_code=500,
            detail="Unable to send reset email. Please try again later."
        )

    return {
        "message": generic_message
    }


# =====================================================
# VERIFY RESET TOKEN
# =====================================================

@router.get("/verify-reset-token")
def verify_reset_token(
    token: str,
    db: Session = Depends(get_db)
):

    if not token:

        raise HTTPException(
            status_code=400,
            detail="Reset token is missing"
        )

    token_hash = hash_reset_token(
        token
    )

    reset_record = db.execute(
        text("""
            SELECT id, user_id, expires_at, used_at
            FROM password_reset_tokens
            WHERE token_hash = :token_hash
        """),
        {
            "token_hash": token_hash
        }
    ).fetchone()

    if not reset_record:

        raise HTTPException(
            status_code=400,
            detail="Invalid reset link"
        )

    if reset_record.used_at:

        raise HTTPException(
            status_code=400,
            detail="Reset link has already been used"
        )

    if reset_record.expires_at < datetime.utcnow():

        raise HTTPException(
            status_code=400,
            detail="Reset link has expired"
        )

    return {
        "valid": True,
        "message": "Reset link is valid"
    }


# =====================================================
# RESET PASSWORD
# =====================================================

@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):

    # -------------------------------------------------
    # PASSWORD VALIDATION
    # -------------------------------------------------

    if len(data.new_password) < 8:

        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters"
        )

    # -------------------------------------------------
    # HASH TOKEN
    # -------------------------------------------------

    token_hash = hash_reset_token(
        data.token
    )

    # -------------------------------------------------
    # FIND RESET RECORD
    # -------------------------------------------------

    reset_record = db.execute(
        text("""
            SELECT id, user_id, expires_at, used_at
            FROM password_reset_tokens
            WHERE token_hash = :token_hash
        """),
        {
            "token_hash": token_hash
        }
    ).fetchone()

    if not reset_record:

        raise HTTPException(
            status_code=400,
            detail="Invalid reset token"
        )

    # -------------------------------------------------
    # CHECK USED TOKEN
    # -------------------------------------------------

    if reset_record.used_at:

        raise HTTPException(
            status_code=400,
            detail="Reset token has already been used"
        )

    # -------------------------------------------------
    # CHECK TOKEN EXPIRATION
    # -------------------------------------------------

    if reset_record.expires_at < datetime.utcnow():

        raise HTTPException(
            status_code=400,
            detail="Reset token has expired"
        )

    # -------------------------------------------------
    # HASH NEW PASSWORD
    # -------------------------------------------------

    new_password_hash = hash_password(
        data.new_password
    )

    # -------------------------------------------------
    # UPDATE USER PASSWORD
    # -------------------------------------------------

    db.execute(
        text("""
            UPDATE users
            SET password_hash = :password_hash
            WHERE id = :user_id
        """),
        {
            "password_hash": new_password_hash,
            "user_id": reset_record.user_id
        }
    )

    # -------------------------------------------------
    # MARK TOKEN USED
    # -------------------------------------------------

    db.execute(
        text("""
            UPDATE password_reset_tokens
            SET used_at = NOW()
            WHERE id = :token_id
        """),
        {
            "token_id": reset_record.id
        }
    )

    # -------------------------------------------------
    # INVALIDATE REMAINING TOKENS
    # -------------------------------------------------

    db.execute(
        text("""
            UPDATE password_reset_tokens
            SET used_at = NOW()
            WHERE user_id = :user_id
              AND used_at IS NULL
        """),
        {
            "user_id": reset_record.user_id
        }
    )

    db.commit()

    return {
        "message": "Password reset successfully"
    }


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

        stage = "google_token_exchange"

        token = await oauth.google.authorize_access_token(
            request
        )

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

        stage = "google_email"

        email = user_info.get(
            "email"
        )

        if not email:

            raise Exception(
                "Google email was not returned"
            )

        if user_info.get("email_verified") is not True:

            raise Exception(
                "Google email is not verified"
            )

        email = email.strip().lower()

        username = (
            user_info.get("name")
            or email.split("@")[0]
        )

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

        stage = "google_jwt_creation"

        zenex_token = create_access_token(
            {
                "sub": str(user.id)
            }
        )

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
                "?error=google_auth_failed"
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

        verifier, challenge = generate_pkce()

        state = secrets.token_urlsafe(32)

        request.session["microsoft_state"] = state

        request.session["microsoft_verifier"] = verifier

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
        # MICROSOFT ERROR
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
        # AUTHORIZATION CODE
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
        # STATE VALIDATION
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
        # PKCE VERIFIER
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
        # TOKEN EXCHANGE
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
        # MICROSOFT USER INFO
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
        # EMAIL
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
        # DATABASE LOOKUP
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
        # CREATE USER
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
        # JWT
        # -------------------------------------------------

        stage = "microsoft_jwt_creation"

        zenex_token = create_access_token(
            {
                "sub": str(user.id)
            }
        )

        # -------------------------------------------------
        # CLEAR SESSION
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
        # REDIRECT
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