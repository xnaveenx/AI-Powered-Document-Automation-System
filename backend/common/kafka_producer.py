import json
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError
from backend.common.config import Settings

logger = logging.getLogger(__name__)

class KafkaProducerClient:
    def __init__(self, bootstrap_servers: str=None):
        self.bootstrap_servers = bootstrap_servers or Settings.KAFKA_BOOTSTRAP_SERVERS
        self.producer = KafkaProducer(
            bootstrap_servers= self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=5,
            linger_ms=10,
            acks="all"
        )
        logger.info(f"Kafka Producer connected to {self.bootstrap_servers}")

    def send_message(self, topic: str, message: dict):
        """ Send JSON message to Kafka topic."""
        try:
            future = self.producer.send(topic, value=message)
            record_metadata = future.get(timeout=10)
            logger.info(f"Message sent to {record_metadata.topic} partition {record_metadata.partion} offset {record_metadata.offset}")
        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            raise

    def flush(self):
        """Ensure all messages are sent before shutdown."""
        self.producer.flush()

    def close(self):
        """Close Kafka producer safelly."""
        self.flush()
        self.producer.close()