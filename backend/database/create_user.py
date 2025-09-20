from backend.database.models import SessionLocal, User
from datetime import datetime, timezone

def create_user():
    db=SessionLocal()

    try:
        user=User(
            username="admin", 
            hashed_password="admin",
            email="admin@dokmanic.com",
            created_at=datetime.now(timezone.utc)
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"User created with ID: {user.id}")

    finally:
        db.close()

if __name__ == "__main__":
    create_user()