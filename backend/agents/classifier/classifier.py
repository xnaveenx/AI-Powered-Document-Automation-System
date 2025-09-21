import os
import json
import logging
import time
import random
from datetime import datetime
import redis
from sqlalchemy.orm import Session

from backend.common.config import Settings
from backend.database.models import SessionLocal, Document, Classification, Logs
from backend.common.kafka_consumer import KafkaConsumerClient
from backend.common.kafka_producer import KafkaProducerClient

from backend.agents.classifier.rule import RuleBasedClassifier
from backend.agents.classifier.ai_model import AIModel
from backend.agents.classifier.genai_utils import classify_with_api  # fallback API

# ---------------- CONFIGURATION ----------------
r = redis.Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, decode_responses=True)
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------- LOAD AI MODEL ----------------
ai_model = AIModel()  # automatically loads trained ai_model.pkl
rule_classifier = RuleBasedClassifier()

# ---------------- HELPER: Retry wrapper ----------------
def retry_with_backoff(func, max_retries=5, base_delay=1, max_delay=30, *args, **kwargs):
    attempt = 0
    while attempt < max_retries:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            wait_time = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0, 0.5)
            logger.warning(f"[RETRY] {func.__name__} failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
            attempt += 1
    raise Exception(f"[FATAL] {func.__name__} failed after {max_retries} retries.")

# ---------------- CLASSIFICATION ----------------
def classify_document(document: dict, uploaded_by: int = None):
    doc_name = document.get("document_name")
    text = document.get("extracted_text", "")

    if not text:
        logger.error(f"[CLASSIFIER] No text found in {doc_name}")
        return None

    # ---- Step 1: Redis cache ----
    cached = r.get(f"classification:{doc_name}")
    if cached:
        logger.info(f"[CLASSIFIER] Using cached classification for {doc_name}")
        return json.loads(cached)

    # ---- Step 2: Apply rule-based hints ----
    rule_hints = rule_classifier.get_applicable_rules(text)
    if rule_hints:
        logger.info(f"[CLASSIFIER] Rule matched for {doc_name}: {rule_hints}")

    # ---- Step 3: AI Model classification ----
    try:
        classification = ai_model.classify(text, hints=rule_hints)
    except Exception as e:
        logger.error(f"[CLASSIFIER] AI model failed for {doc_name}: {e}")
        # Fallback to GenAI API
        classification = classify_with_api(text)
        classification["details"] = f"Fallback to GenAI API due to AI failure: {str(e)}"

    # ---- Step 4: Handle unknown/low-confidence ----
    if classification.get("confidence", 0) < 0.5:
        logger.info(f"[CLASSIFIER] Low confidence ({classification['confidence']}) for {doc_name}. Marking as Unknown")
        classification["category"] = "Unknown"

    result = {
        "document_name": doc_name,
        "classification": classification["category"],
        "confidence": classification.get("confidence", 0),
        "details": classification.get("details", ""),
        "rule_hints": rule_hints,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # ---- Step 5: Save to DB ----
    try:
        db: Session = SessionLocal()
        doc_obj = db.query(Document).filter_by(filename=doc_name).first()
        if doc_obj:
            record = Classification(
                document_id=doc_obj.id,
                classifier_type="Hybrid-AI-Rule",
                category=classification["category"],
                confidence=classification.get("confidence", 0),
                details={"ai_details": classification.get("details", ""), "rule_hints": rule_hints},
            )
            db.add(record)

            log = Logs(
                document_id=doc_obj.id,
                action="classified",
                message=f"Document classified as {classification['category']}"
            )
            db.add(log)
            db.commit()
            logger.info(f"[DB] Classification saved for {doc_name}")
        else:
            logger.warning(f"[DB] Document not found in DB: {doc_name}")
    except Exception as e:
        logger.error(f"[DB ERROR] Could not save classification for {doc_name}: {str(e)}")
        db.rollback()
    finally:
        db.close()

    # ---- Step 6: Cache in Redis ----
    r.setex(f"classification:{doc_name}", 3600, json.dumps(result))

    return result

# ---------------- MAIN LOOP ----------------
def main():
    logger.info("[CLASSIFIER] Agent starting...")

    try:
        consumer = retry_with_backoff(
            KafkaConsumerClient,
            max_retries=5,
            topic=Settings.KAFKA_TOPIC_EXTRACTOR,
            group_id="classifier_group",
        )
        global producer
        producer = retry_with_backoff(KafkaProducerClient, max_retries=5)
    except Exception as e:
        logger.critical(f"[FATAL] Could not connect to Kafka: {e}")
        return

    def handle_message(data: dict):
        logger.info(f"[CLASSIFIER] Processing document: {data.get('document_name')}")
        result = classify_document(data, uploaded_by=data.get("uploaded_by"))
        if result:
            try:
                retry_with_backoff(
                    producer.send_message,
                    max_retries=3,
                    topic=Settings.KAFKA_TOPIC_CLASSIFIER,
                    value=result,
                )
                logger.info(f"[KAFKA] Sent classification result for {data.get('document_name')}")
            except Exception as e:
                logger.error(f"[KAFKA ERROR] Could not send classification for {data.get('document_name')}: {str(e)}")

    try:
        consumer.consume_messages(handle_message)
    except KeyboardInterrupt:
        logger.info("[CLASSIFIER] Shutting down...")
    finally:
        try: consumer.close()
        except: pass
        try: producer.close()
        except: pass

if __name__ == "__main__":
    main()
