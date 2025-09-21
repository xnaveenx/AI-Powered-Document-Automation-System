import os
import io
import logging
import tempfile
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session
from backend.agents.ingestor.ingestor import IngestorAgent

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class DriveIngestor:
    def __init__(self, db: Session, creds: Credentials):
        """
        Args:
            db: SQLAlchemy session
            creds: Google OAuth2 credentials
        """
        self.db = db
        self.creds = creds
        self.agent = IngestorAgent(db)
        self.service = build('drive', 'v3', credentials=self.creds)

    def ingest_folder(self, folder_id: str, mode: str = "all", processed_files=set()):
        """
        Fetch files from a Google Drive folder and send to ingestion pipeline.

        Args:
            folder_id: ID of Google Drive folder
            mode: "existing", "new", or "all"
            processed_files: set of previously processed file IDs (for new-only mode)
        """
        query = f"'{folder_id}' in parents and trashed=false"
        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType)"
            ).execute()

            files = results.get('files', [])
            if not files:
                logger.info(f"No files found in folder {folder_id}")
                return

            for file in files:
                file_id = file['id']
                file_name = file['name']

                if mode == "new" and file_id in processed_files:
                    continue

                logger.info(f"Processing file: {file_name} (id={file_id})")

                # Download file temporarily
                request = self.service.files().get_media(fileId=file_id)
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as temp_file:
                    downloader = MediaIoBaseDownload(temp_file, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            logger.info(f"Download {int(status.progress() * 100)}% complete.")

                    temp_file_path = temp_file.name

                # Send through unified ingestion pipeline
                self.agent.ingest_remote_file(temp_file_path, uploaded_by=1, source="gdrive", sender="gdrive_user")

                # Cleanup
                os.remove(temp_file_path)

                # Mark file as processed
                processed_files.add(file_id)

        except HttpError as error:
            logger.error(f"Drive API error: {error}")
