from fastapi import APIRouter, Depends

from app.schemas.user import UserResponse, UserInDB
from app.core.dependencies import get_current_active_user


router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: UserInDB = Depends(get_current_active_user)):
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at,
        is_active=current_user.is_active
    )


@router.post("/verify")
async def verify_token(current_user: UserInDB = Depends(get_current_active_user)):
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email
    }
