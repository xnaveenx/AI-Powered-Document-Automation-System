from kafka import KafkaProducer
import json
from backend.common.config import Settings
import logging 

settings=Settings()
logger= logging.getLogger(__name__)

producer = KafkaProducer(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def send_document_message(message: dict):
    try:
        producer.send(settings.KAFKA_TOPIC_INGESTOR, value=message)
        producer.flush()
        logger.info(f"Sent message to Kafka: {message}")
    except Exception as e:
        logger.error(f"Failed to send Kafka message: {e}")
        raise