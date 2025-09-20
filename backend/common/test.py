import logging
from backend.common.db_utils import SessionLocal
from backend.agents.ingestor.ingestor import IngestorAgent

# Setup logging to console
logging.basicConfig(level=logging.INFO)

def main():
    db = SessionLocal()
    ingestor = IngestorAgent(db)

    # Provide path to an actual file on your system
    file_path = r"C:\Users\Naveenkumar\Downloads\Aatif_Resume.pdf"  
    uploaded_by = 1  # Use an existing user ID from your DB

    document = ingestor.ingest_local_file(file_path, uploaded_by)

    print(f"Ingested Document ID: {document.id}")
    print(f"Filename: {document.filename}")
    print(f"Credibility Score: {document.credibility_score}")

if __name__ == "__main__":
    main()
