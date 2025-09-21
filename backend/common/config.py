import os
from dotenv import load_dotenv


load_dotenv()

class Settings:
    POSTGRES_USER = os.getenv("POSTGRES_USER", "dokmanic")
    POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB=os.getenv("POSTGRES_DB", "dokmanic")
    POSTGRES_HOST=os.getenv("POSTGRES_HOST", "dokmanic.czuuwm2uugft.ap-south-1.rds.amazonaws.com")
    POSTGRES_PORT=int(os.getenv("POSTGRES_PORT", "5432"))

    DATABASE_URL= f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_TOPIC_INGESTOR = os.getenv("KAFKA_TOPIC_INGESTOR", "ingestor_topic")
    KAFKA_TOPIC_EXTRACTOR = os.getenv("KAFKA_TOPIC_EXTRACTOR", "extractor_topic")
    KAFKA_TOPIC_CLASSIFIED = os.getenv("KAFKA_TOPIC_CLASSIFIED", "classified")


    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY=os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET_NAME=os.getenv("AWS_S3_BUCKET_NAME")
    AWS_REGION=os.getenv("AWS_REGION")

    SECRET_KEY=os.getenv("SECRET_KEY")
    ALGORITHM=os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES",60))

    TESSERACT_PATH=os.getenv("TESSERACT_PATH", "tesseract")
    TESSERACT_LANG = os.getenv("TESSERACT_LANG", "eng")

    GEMINI_API_KEY:str=os.getenv("GEMINI_API_KEY")
setting=Settings()