import os
import base64
import logging
import tempfile
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session
from backend.agents.ingestor.ingestor import IngestorAgent

logger = logging.getLogger(__name__)

# Scopes required to read Gmail messages
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailIngestor:
    def __init__(self, db: Session, creds: Credentials, user_id='me'):
        """
        Args:
            db: SQLAlchemy session
            creds: Google OAuth2 credentials
            user_id: Gmail user (default 'me' for authenticated user)
        """
        self.db = db
        self.creds = creds
        self.user_id = user_id
        self.agent = IngestorAgent(db)
        self.service = build('gmail', 'v1', credentials=self.creds)

    def fetch_unseen_attachments(self, label_ids=['INBOX']):
        """
        Fetch unseen emails with attachments and process them.
        """
        try:
            results = self.service.users().messages().list(
                userId=self.user_id,
                labelIds=label_ids,
                q="has:attachment is:unread"
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                logger.info("No new emails with attachments.")
                return

            for msg in messages:
                self._process_message(msg['id'])

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")

    def _process_message(self, msg_id: str):
        """Download attachments from a single email and pass to pipeline."""
        try:
            message = self.service.users().messages().get(
                userId=self.user_id, id=msg_id
            ).execute()

            payload = message.get('payload', {})
            parts = payload.get('parts', [])

            for part in parts:
                filename = part.get('filename')
                body = part.get('body', {})
                attachment_id = body.get('attachmentId')

                if filename and attachment_id:
                    attachment = self.service.users().messages().attachments().get(
                        userId=self.user_id, messageId=msg_id, id=attachment_id
                    ).execute()

                    data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

                    # Save temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as temp_file:
                        temp_file.write(data)
                        temp_file_path = temp_file.name

                    logger.info(f"Fetched attachment: {filename}")

                    # Send through unified pipeline
                    self.agent.ingest_remote_file(temp_file_path, uploaded_by=1, source="gmail", sender="gmail_user")

                    # Optionally, delete temp file
                    os.remove(temp_file_path)

            # Mark message as read
            self.service.users().messages().modify(
                userId=self.user_id,
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

        except Exception as e:
            logger.error(f"Failed to process Gmail message {msg_id}: {e}")
