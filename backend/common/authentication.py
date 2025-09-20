from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database.models import User, SessionLocal
from backend.common.config import settings
from backend.common.redis_utils import get_last_active, set_last_active
from backend.common.db_utils import sync_last_active_to_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire =datetime.now(timezone.utc)+timedelta(hours=4)
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session=Depends(SessionLocal))->User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail= "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception
    
    last_active= get_last_active(user.id)
    if last_active and datetime.now(timezone.utc) - last_active > timedelta(hours=4):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired due to inactivity")
    
    set_last_active(user.id)

    return user

def sync_user_activity_to_db(user_id:int):
    db=SessionLocal()
    try:
        user=db.query(User).filter(User.id==user_id).first()
        if user:
            last_active = get_last_active(user.id)
            if last_active:
                user.last_active_at = last_active
                db.commit()
    
    finally:
        db.close()
