import os
import logging
from sqlalchemy.orm import Session
from backend.database.models import Document
from backend.agents.ingestor.s3_handler import upload_to_s3
from backend.agents.ingestor.ai_utils import calculate_credibility_score
from backend.agents.ingestor.kafka_producer import send_document_message

logger = logging.getLogger(__name__)


class IngestorAgent:
    def __init__(self, db: Session):
        self.db = db

    # ---------------------- PUBLIC METHODS ----------------------

    def ingest_local_file(self, file_path: str, uploaded_by: int, source="local", sender=None):
        """Ingest a local file through the unified pipeline."""
        return self._process_file(file_path, uploaded_by, source, sender)

    def ingest_remote_file(self, file_path: str, uploaded_by: int, source="remote", sender=None):
        """Ingest a file from Gmail/Drive/other sources through the same pipeline."""
        return self._process_file(file_path, uploaded_by, source, sender)

    # ---------------------- PRIVATE PIPELINE ----------------------

    def _process_file(self, file_path: str, uploaded_by: int, source="unknown", sender=None):
        """Handles S3 upload, DB save, credibility scoring, and Kafka notification."""
        filename = os.path.basename(file_path)
        s3_key = f"documents/{filename}"

        # Upload to S3
        s3_url = upload_to_s3(file_path, s3_key)

        # Save in DB
        doc = Document(
            filename=filename,
            stored_path=s3_url,
            uploaded_by=uploaded_by,
            source=source,
            sender=sender,
            status="new"
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        logger.info(f"Saved document in DB with id: {doc.id}")

        # Compute credibility score
        score = calculate_credibility_score(file_path)
        doc.credibility_score = score
        self.db.commit()
        logger.info(f"Updated document {doc.id} with credibility score: {score}")

        # Send Kafka message
        message = {
            "document_id": doc.id,
            "s3_key": doc.stored_path,
            "uploaded_by": uploaded_by,
            "credibility_score": score
        }
        send_document_message(message)
        logger.info(f"Sent Kafka message for document {doc.id}")

        return doc
