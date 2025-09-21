# reset_db.py
from backend.database.models import Base, engine

def reset_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")

    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")

if __name__ == "__main__":
    reset_database()
