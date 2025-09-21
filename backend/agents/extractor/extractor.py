import os
import json
import logging
import hashlib
import time
import random
from datetime import datetime, timezone
import redis
from sqlalchemy.orm import Session
from backend.agents.extractor.extractor_utils import extract_any
from backend.common.config import Settings
from backend.database.models import SessionLocal, Document, Extraction, Logs
from backend.common.kafka_consumer import KafkaConsumerClient
from backend.common.kafka_producer import KafkaProducerClient

# ---------------- CONFIGURATION ----------------
r = redis.Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, decode_responses=True)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------- HELPER: Retry wrapper ----------------
def retry_with_backoff(func, max_retries=5, base_delay=1, max_delay=30, *args, **kwargs):
    """Retry function with exponential backoff."""
    attempt = 0
    while attempt < max_retries:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            wait_time = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0, 0.5)
            logger.warning(
                f"[RETRY] {func.__name__} failed (attempt {attempt+1}/{max_retries}): {e}. "
                f"Retrying in {wait_time:.1f}s..."
            )
            time.sleep(wait_time)
            attempt += 1
    logger.error(f"[FATAL] {func.__name__} failed after {max_retries} retries.")
    raise

# ---------------- UTILITY FUNCTIONS ----------------
def compute_file_hash(file_path: str) -> str:
    """Compute MD5 hash of a file for deduplication."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# ---------------- EXTRACTOR FUNCTIONS ----------------
def process_document(file_path: str, uploaded_by: int = None, source: str = "unknown"):
    filename = os.path.basename(file_path)

    # Compute file hash
    try:
        file_hash = compute_file_hash(file_path)
    except Exception as e:
        logger.error(f"[EXTRACTOR] Failed to compute hash for {filename}: {str(e)}")
        return None

    # Skip if duplicate (based on hash in Redis)
    if r.exists(file_hash):
        logger.info(f"[EXTRACTOR] Skipping duplicate document (hash match): {filename}")
        return None

    # Extract plain text only
    try:
        extracted_content = extract_any(file_path)  # {"pages": [...], "full_text": "..."}
        extracted_text = extracted_content["full_text"]
    except Exception as e:
        logger.error(f"[EXTRACTOR] Failed to extract {filename}: {str(e)}")
        return None

    metadata = {
        "word_count": len(extracted_text.split()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }

    result = {
        "document_name": filename,
        "document_type": os.path.splitext(filename)[1].lower(),
        "extracted_text": extracted_text,
        "metadata": metadata,
    }

    # ---------------- DB Operations ----------------
    try:
        db: Session = SessionLocal()
        document = db.query(Document).filter_by(file_hash=file_hash).first()

        if document:
            logger.info(f"[DB] Document already exists (hash match): {filename}")
        else:
            document = Document(
                filename=filename,
                file_hash=file_hash,
                source=source,
                uploaded_by=uploaded_by,
                stored_path=file_path,
                status="extracted",
            )
            db.add(document)
            db.commit()
            db.refresh(document)

        extraction = Extraction(
            document_id=document.id,
            extracted_text=extracted_text,
            extracted_metadata=metadata,
        )
        db.add(extraction)

        log = Logs(
            document_id=document.id,
            action="extracted",
            message=f"Document extracted with {metadata['word_count']} words",
        )
        db.add(log)

        db.commit()
        logger.info(f"[DB] Saved document and extraction: {filename}")
    except Exception as e:
        logger.error(f"[DB ERROR] Failed to save {filename}: {str(e)}")
    finally:
        db.close()

    # Store hash in Redis (TTL = 1 hour)
    r.setex(file_hash, 3600, json.dumps(metadata))

    # Send to Kafka (with retry)
    try:
        retry_with_backoff(
            producer.send_message,
            max_retries=3,
            topic=Settings.KAFKA_TOPIC_EXTRACTOR,
            value=result,
        )
        logger.info(f"[KAFKA] Sent document {filename} to {Settings.KAFKA_TOPIC_EXTRACTOR}")
    except Exception as e:
        logger.error(f"[KAFKA ERROR] Permanent failure sending {filename}: {str(e)}")

    return result

# ---------------- MAIN LOOP ----------------
def main():
    logger.info("[EXTRACTOR] Agent starting...")

    # Initialize Kafka clients with retry
    try:
        consumer = retry_with_backoff(
            KafkaConsumerClient,
            max_retries=5,
            topic=Settings.KAFKA_TOPIC_INGESTOR,
            group_id="extractor_group",
        )
        global producer
        producer = retry_with_backoff(
            KafkaProducerClient,
            max_retries=5,
        )
    except Exception as e:
        logger.critical(f"[FATAL] Could not connect to Kafka: {e}")
        return

    def handle_message(data: dict):
        file_path = data.get("file_path")
        uploaded_by = data.get("uploaded_by")
        source = data.get("source", "unknown")

        if not file_path or not os.path.exists(file_path):
            logger.error(f"[EXTRACTOR] File does not exist: {file_path}")
            return

        logger.info(f"[EXTRACTOR] Processing new document: {file_path}")
        process_document(file_path, uploaded_by, source)

    try:
        consumer.consume_messages(handle_message)
    except KeyboardInterrupt:
        logger.info("[EXTRACTOR] Shutting down...")
    finally:
        try:
            consumer.close()
        except Exception as e:
            logger.error(f"[KAFKA ERROR] Failed to close consumer: {str(e)}")
        try:
            producer.close()
        except Exception as e:
            logger.error(f"[KAFKA ERROR] Failed to close producer: {str(e)}")


if __name__ == "__main__":
    main()
