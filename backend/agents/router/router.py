# backend/agents/router/router.py

import logging
from backend.common.config import Settings
from backend.common.kafka_consumer import KafkaConsumerClient
from backend.database.models import SessionLocal, Document, RoutingRule, RoutingLog
from backend.agents.router.router_utils import move_to_folder, upload_to_s3, send_to_erp_api

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def process_document_message(message: dict):
    """
    Process each document message from Kafka and route according to rules.
    message: {
        "document_id": int,
        "doc_type": str (optional)
    }
    """
    session = SessionLocal()
    try:
        doc_id = message.get("document_id")
        doc = session.query(Document).filter_by(id=doc_id).first()
        if not doc:
            logger.warning(f"Document {doc_id} not found in DB.")
            return

        # Determine document type
        doc_type = message.get("doc_type") or (doc.doc_metadata.get("type") if doc.doc_metadata else None)
        if not doc_type:
            logger.warning(f"Document {doc.filename} has no type metadata.")
            return

        # Fetch routing rule for this doc_type
        rule = session.query(RoutingRule).filter_by(doc_type=doc_type, enabled=True).first()

        status = "success"
        routed_path = None
        message_text = None

        if rule:
            try:
                if rule.destination_type == "folder":
                    routed_path = move_to_folder(doc.stored_path, rule.destination_value)
                elif rule.destination_type == "s3":
                    routed_path = upload_to_s3(doc.stored_path, rule.destination_value)
                elif rule.destination_type == "erp":
                    routed_path = send_to_erp_api(doc.stored_path, rule.destination_value)
                else:
                    status = "failed"
                    message_text = f"Unknown destination type: {rule.destination_type}"
            except Exception as e:
                status = "failed"
                message_text = str(e)
        else:
            status = "no_rule"
            message_text = "No matching routing rule found"

        # Update document routed_path if successful
        if status == "success" and routed_path:
            doc.routed_path = routed_path

        # Log the routing attempt
        routing_log = RoutingLog(
            document_id=doc.id,
            rule_id=rule.id if rule else None,
            file_name=doc.filename,
            file_path=routed_path,
            doc_type=doc_type,
            destination=rule.destination_value if rule else None,
            status=status,
            message=message_text
        )
        session.add(routing_log)
        session.commit()

        logger.info(f"Document {doc.filename} routed with status: {status}")

    except Exception as e:
        logger.error(f"Error processing document message {message}: {e}")
        session.rollback()
    finally:
        session.close()


def start_router_agent():
    """
    Starts the router agent Kafka consumer to listen for classified documents.
    """
    consumer = KafkaConsumerClient(
        topic=Settings.KAFKA_TOPIC_CLASSIFIED,
        group_id="router_group"
    )
    logger.info("Router Agent started, listening for documents...")
    consumer.consume_messages(process_document_message)


if __name__ == "__main__":
    start_router_agent()
