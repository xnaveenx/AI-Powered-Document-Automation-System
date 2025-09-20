from fastapi import FastAPI
from backend.routers import auth  # Import the auth router

app = FastAPI(
    title="AI-Powered Document Automation System",
    description="API for handling user registration, authentication, and document processing with intelligent classification and routing.",
    version="1.0.0"
)

# Register the auth router
app.include_router(auth.router, prefix="/auth", tags=["auth"])