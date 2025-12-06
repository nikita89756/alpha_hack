from typing import Optional

from app.services.auth_service import auth_service
from app.schemas.user import UserInDB


class UserService:
    async def get_by_user_id(self, user_id: str) -> Optional[UserInDB]:
        user = await auth_service.users_collection.find_one({"user_id": user_id})
        if user:
            user["_id"] = str(user["_id"])
            return UserInDB(**user)
        return None


user_service = UserService()
