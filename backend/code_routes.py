from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth_routes import get_current_user
from code_analyzer import check_code_syntax


router = APIRouter(
    prefix="/code",
    tags=["Code Tools"]
)


class SyntaxCheckRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000)
    language: str = Field(..., min_length=1, max_length=20)


@router.post("/check-syntax")
def check_syntax(
    request: SyntaxCheckRequest,
    current_user=Depends(get_current_user)
):
    user_id = current_user.get("id") if isinstance(current_user, dict) else None

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )

    result = check_code_syntax(request.code, request.language)

    return {
        "success": True,
        **result
    }