
from backend.database.models import init_db

print("Attempting to create database tables...")
init_db()
print("Database tables created successfully (if they didn't already exist).")