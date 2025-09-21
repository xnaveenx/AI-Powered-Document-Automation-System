import os
import time
import logging
import redis
from sqlalchemy.orm import Session
from backend.common.config import Settings
from backend.agents.ingestor.ingestor import IngestorAgent
from backend.agents.ingestor.gdrive_handler import DriveIngestor
from backend.agents.ingestor.gmail_handler import GmailIngestor  # we will implement next
from backend.common.db_utils import get_db
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)
r = redis.Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, decode_responses=True)

class UnifiedIngestor:
    def __init__(self, db: Session, gdrive_creds: Credentials, gmail_creds: Credentials):
        self.db = db
        self.agent = IngestorAgent(db)
        self.drive_ingestor = DriveIngestor(db, gdrive_creds)
        self.gmail_ingestor = GmailIngestor(db, gmail_creds)
        self.processed_drive_files = set()
        self.processed_gmail_files = set()
        self.local_folder = Settings.LOCAL_INGEST_FOLDER

    def poll_local_folder(self):
        logger.info(f"Polling local folder: {self.local_folder}")
        for fname in os.listdir(self.local_folder):
            fpath = os.path.join(self.local_folder, fname)
            if os.path.isfile(fpath) and not r.exists(f"local:{fname}"):
                logger.info(f"Processing local file: {fname}")
                self.agent.ingest_local_file(fpath, uploaded_by=1, source="local")
                r.set(f"local:{fname}", 1, ex=3600)

    def poll_gdrive(self, folder_id, mode="all"):
        self.drive_ingestor.ingest_folder(folder_id, mode, self.processed_drive_files)

    def poll_gmail(self, label="INBOX"):
        self.gmail_ingestor.fetch_attachments(label, self.processed_gmail_files)

    def start(self, interval=60, gdrive_folder_id=None, gdrive_mode="all"):
        logger.info("Unified Ingestor started...")
        while True:
            try:
                self.poll_local_folder()
                if gdrive_folder_id:
                    self.poll_gdrive(gdrive_folder_id, mode=gdrive_mode)
                self.poll_gmail()
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Unified Ingestor stopped by user")
                break
            except Exception as e:
                logger.error(f"Ingestor error: {e}")
                time.sleep(interval)