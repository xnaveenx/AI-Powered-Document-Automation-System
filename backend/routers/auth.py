from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, model_validator
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.database.models import User, SessionLocal
from backend.common.authentication import get_password_hash, verify_password, create_access_token, get_current_user
from backend.common.redis_utils import set_last_active
from backend.common.logger import logger

router = APIRouter()

# -------------------- Pydantic Schemas --------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    password_confirm: str

    @model_validator(mode='after')
    def check_passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    email: EmailStr
    last_active_at: str|None

# -------------------- Endpoints --------------------

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(request: RegisterRequest, db: Session = Depends(SessionLocal)):
    logger.info(f"Attempting to register user: {request.email}")
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        logger.warning(f"Registration failed - email already registered: {request.email}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = get_password_hash(request.password)
    new_user = User(
        email=request.email,
        password=hashed_password,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"User registered successfully: {request.email}")

    return {"message": "User registered successfully"}

@router.post("/login", response_model=TokenResponse)
def login_user(request: LoginRequest, db: Session = Depends(SessionLocal)):
    logger.info(f"Login attempt for user: {request.email}")
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password):
        logger.warning(f"Invalid login attempt for user: {request.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.id})
    set_last_active(user.id)

    logger.info(f"User logged in successfully: {request.email}")
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    logger.info(f"Fetching current user info for : {current_user.email}")
    return {
    "email": current_user.email,
    "last_active_at": current_user.last_active_at.isoformat() if current_user.last_active_at else None
}

