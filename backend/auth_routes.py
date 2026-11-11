import os

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pydantic import BaseModel, EmailStr, Field

from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from passlib.context import CryptContext
from jose import jwt, JWTError

from backend.database import SessionLocal


# ==================================================
# ROUTER
# ==================================================

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# ==================================================
# JWT CONFIGURATION
# ==================================================

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "dev-only-change-this-secret-before-deployment"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer(auto_error=False)


# ==================================================
# PASSWORD CONFIGURATION
# ==================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ==================================================
# DATABASE SESSION
# ==================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ==================================================
# REQUEST MODELS
# ==================================================

class RegisterRequest(BaseModel):

    username: str = Field(
        min_length=2,
        max_length=100
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=72
    )


class LoginRequest(BaseModel):

    username_or_email: str = Field(
        min_length=1,
        max_length=100
    )

    password: str = Field(
        min_length=1,
        max_length=72
    )


# ==================================================
# PASSWORD FUNCTIONS
# ==================================================

def hash_password(password: str):

    if len(password.encode("utf-8")) > 72:

        raise HTTPException(
            status_code=400,
            detail="Password is too long"
        )

    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str):

    if len(password.encode("utf-8")) > 72:

        return False

    try:

        return pwd_context.verify(
            password,
            hashed_password
        )

    except Exception:

        return False


# ==================================================
# JWT TOKEN GENERATION
# ==================================================

def create_access_token(data: dict):

    payload = data.copy()

    now = datetime.now(timezone.utc)

    expire = now + timedelta(
        hours=ACCESS_TOKEN_EXPIRE_HOURS
    )

    payload.update({
        "exp": expire,
        "iat": now
    })

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ==================================================
# VERIFY JWT TOKEN
# ==================================================

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    if credentials is None:

        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if credentials.scheme.lower() != "bearer":

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication scheme"
        )

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:

            raise HTTPException(
                status_code=401,
                detail="Invalid token payload"
            )

        return payload

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )


# ==================================================
# REGISTER API
# ==================================================

@router.post("/register")
def register_user(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):

    username = request.username.strip()

    email = str(request.email).lower().strip()

    # Validate username
    if not username:

        raise HTTPException(
            status_code=400,
            detail="Username cannot be empty"
        )

    # Check username or email already exists
    existing_user = db.execute(
        text("""
            SELECT id
            FROM users
            WHERE LOWER(username) = :username
               OR LOWER(email) = :email
            LIMIT 1
        """),
        {
            "username": username.lower(),
            "email": email
        }
    ).fetchone()

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Username or email already registered"
        )

    hashed_password = hash_password(
        request.password
    )

    try:

        db.execute(
            text("""
                INSERT INTO users
                (
                    username,
                    email,
                    password_hash
                )
                VALUES
                (
                    :username,
                    :email,
                    :password_hash
                )
            """),
            {
                "username": username,
                "email": email,
                "password_hash": hashed_password
            }
        )

        db.commit()

        return {
            "success": True,
            "message": "Registration successful"
        }

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Username or email already registered"
        )

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database registration failed"
        )


# ==================================================
# LOGIN API
# USERNAME OR EMAIL + PASSWORD
# ==================================================

@router.post("/login")
def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    username_or_email = (
        request.username_or_email.strip().lower()
    )

    # Find user using username or email
    user = db.execute(
        text("""
            SELECT
                id,
                username,
                email,
                password_hash
            FROM users
            WHERE LOWER(username) = :value
               OR LOWER(email) = :value
            LIMIT 1
        """),
        {
            "value": username_or_email
        }
    ).mappings().first()

    # User not found
    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password"
        )

    # Verify password
    if not verify_password(
        request.password,
        user["password_hash"]
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password"
        )

    # Generate JWT token
    access_token = create_access_token({
        "sub": str(user["id"]),
        "email": user["email"]
    })

    return {
        "success": True,
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    }


# ==================================================
# CURRENT USER API
# ==================================================

@router.get("/me")
def get_current_user(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):

    user_id = token_data.get("sub")

    user = db.execute(
        text("""
            SELECT
                id,
                username,
                email
            FROM users
            WHERE id = :id
        """),
        {
            "id": user_id
        }
    ).mappings().first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "success": True,
        "user": dict(user)
    }
    