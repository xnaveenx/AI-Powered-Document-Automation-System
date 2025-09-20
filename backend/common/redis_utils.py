import redis
from datetime import datetime, timedelta , timezone
from backend.common.config import Settings

r = redis.Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, db=0, decode_responses=True)

def last_active_key(user_id: int)-> str:
    return f"user:{user_id}:last_active_at"

def gmail_activity_key(user_id: int)->str:
    return f"user:{user_id}:gmail_last_activity_at"

def get_last_active(user_id: int)-> datetime | None:
    key=last_active_key(user_id)
    timestamp=r.get(key)
    if timestamp:
        return datetime.fromisoformat(timestamp)
    return None

def set_last_active(user_id: int):
    key=last_active_key(user_id)
    now = datetime.now(timezone.utc).isofromat()
    r.set(key, now, ex=4*60*60)

def get_gmail_activity(user_id: int) -> datetime | None:
    key = gmail_activity_key(user_id)
    timestamp= r.get(key)
    if timestamp:
        return datetime.fromisoformat(timestamp)
    return None

def set_gmail_activity(user_id: int):
    key = gmail_activity_key(user_id)
    now = datetime.now(timezone.utc).isoformat()
    r.set(key,now, ex=6*60*60)
