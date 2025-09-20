import os
import logging
from sqlalchemy.orm import Session
from backend.common.db_utils import get_db
from backend.database.models import Document
from backend.agents.ingestor.s3_handler import upload_to_s3
from backend.agents.ingestor.ai_utils import calculate_credibility_score
from backend.agents.ingestor.kafka_producer import send_document_message

logger= logging.getLogger(__name__)

class IngestorAgent:
    def __init__(self, db: Session):
        self.db = db

    def ingest_local_file(self, file_path: str, uploaded_by: int, source="local", sender=None):
        filename=os.path.basename(file_path)
        s3_key= f"documents/{filename}"

        s3_url = upload_to_s3(file_path, s3_key)

        doc= Document(
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

        score = calculate_credibility_score(file_path)
        doc.credibility_score = score
        self.db.commit()
        logger.info(f"Updated document {doc.id} with credibility score: {score}")

        message = {
            "document_id": doc.id, 
            "s3_key": doc.stored_path, 
            "uploaded_by": uploaded_by, 
            "credibility_score": score
        }
        send_document_message(message)

        return doc