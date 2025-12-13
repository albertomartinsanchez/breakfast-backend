from fastapi import APIRouter, Depends, HTTPException, status

from auth.schemas import UserLogin, Token
from auth.dependencies import (
    create_access_token,
    verify_user_credentials,
    invalidate_user_tokens,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(user_in: UserLogin):
    if not verify_user_credentials(user_in.username, user_in.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(user_in.username)
    return Token(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: str = Depends(get_current_user)):
    invalidate_user_tokens(current_user)
    return None
