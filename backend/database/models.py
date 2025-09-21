from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey, Float, Text, Boolean
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime, timezone
from backend.common.config import Settings

DATABASE_URL = Settings.DATABASE_URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    gmail_last_activity_at = Column(DateTime, nullable=True)
    last_active_at = Column(DateTime, nullable=True)

    documents = relationship("Document", back_populates="uploader", cascade="all, delete-orphan")
    logs = relationship("Logs", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_hash = Column(String, unique=True, nullable=True)
    doc_metadata = Column(JSON)
    source = Column(String, nullable=False)
    sender = Column(String, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    original_received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    stored_path = Column(String, nullable=False)
    routed_path = Column(String, nullable=True)
    status = Column(String, default="new", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    credibility_score = Column(Float, nullable=True)

    uploader = relationship("User", back_populates="documents")
    logs = relationship("Logs", back_populates="document", cascade="all, delete-orphan")
    extractions = relationship("Extraction", back_populates="document", cascade="all, delete-orphan")
    classifications = relationship("Classification", back_populates="document", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")
    routing_logs = relationship("RoutingLog", back_populates="document", cascade="all, delete-orphan")


class Logs(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    action = Column(String, nullable=False)
    message = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="logs")
    user = relationship("User", back_populates="logs")


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    extracted_text = Column(Text, nullable=True)
    extracted_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="extractions")


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    classifier_type = Column(String, nullable=False)   # e.g., "AI", "RuleBased"
    category = Column(String, nullable=False)          # e.g., "invoice", "resume"
    confidence = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="classifications")


class ClassificationRule(Base):
    __tablename__ = "classification_rule"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    destination = Column(String, nullable=False)      # e.g., "Finance", "HR"
    rule_applied = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="routes")


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = Column(JSON, nullable=False)    # store vector embedding
    model = Column(String, nullable=False)      # e.g., "openai-ada-002"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="embeddings")


# ------------------- NEW MODELS FOR ROUTER -------------------

class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id = Column(Integer, primary_key=True, index=True)
    doc_type = Column(String, nullable=False, index=True)       # E.g., "invoice", "resume"
    destination_type = Column(String, nullable=False)           # "folder" | "s3" | "erp" | "db"
    destination_value = Column(Text, nullable=False)            # path, s3://bucket/prefix, API url, table name
    conditions = Column(JSON, nullable=True)                    # optional JSON (e.g., {"amount": {">": 10000}})
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class RoutingLog(Base):
    __tablename__ = "routing_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    rule_id = Column(Integer, ForeignKey("routing_rules.id", ondelete="SET NULL"), nullable=True)
    file_name = Column(String, nullable=False)
    file_path = Column(Text, nullable=True)
    doc_type = Column(String, nullable=True)
    destination = Column(Text, nullable=True)
    status = Column(String, nullable=False)    # success | failed | retry | no_rule
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="routing_logs")
    rule = relationship("RoutingRule")


# ------------------- INIT -------------------

def init_db():
    Base.metadata.create_all(bind=engine)
