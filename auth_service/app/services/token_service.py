from app.core.security import create_access_token, create_refresh_token
from app.schemas.token import Token


class TokenService:
    def create_tokens(self, user_id: str, username: str) -> Token:
        access_token = create_access_token(
            data={"sub": user_id, "username": username}
        )
        refresh_token = create_refresh_token(
            data={"sub": user_id}
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )


token_service = TokenService()
