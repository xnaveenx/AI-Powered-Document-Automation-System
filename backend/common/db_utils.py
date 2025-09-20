from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import logging

from backend.common.config import Settings
from backend.database.models import User
from backend.common.redis_utils import get_last_active, get_gmail_activity

# Setup logging
logger = logging.getLogger(__name__)

# Database setup
settings = Settings()
DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def sync_last_active_to_db(db: Session, user_id: int) -> bool:
    """
    Sync last active timestamp from Redis to DB for a given user.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found in DB.")
            return False

        last_active = get_last_active(user_id)
        if last_active:
            user.last_active_at = last_active
            db.commit()
            logger.info(f"Updated last_active_at for user {user_id}: {last_active}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to sync last active for user {user_id}: {e}")
        db.rollback()
        return False


def sync_gmail_activity_to_db(db: Session, user_id: int) -> bool:
    """
    Sync Gmail last activity timestamp from Redis to DB for a given user.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found in DB.")
            return False

        gmail_last_active = get_gmail_activity(user_id)
        if gmail_last_active:
            user.gmail_last_activity_at = gmail_last_active
            db.commit()
            logger.info(f"Updated gmail_last_activity_at for user {user_id}: {gmail_last_active}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to sync Gmail activity for user {user_id}: {e}")
        db.rollback()
        return False


# Dependency (for FastAPI or standalone usage)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
