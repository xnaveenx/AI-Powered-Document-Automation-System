import json
import logging
from kafka import KafkaConsumer
from backend.common.config import Settings

logger = logging.getLogger(__name__)

class KafkaConsumerClient:
    def __init__(self, topic: str, group_id: str, bootstrap_servers: str = None, auto_offset_reset: str = "earliest"):
        self.topic = topic
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers or Settings.KAFKA_BOOTSTRAP_SERVERS

        self.consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        logger.info(f"[KAFKA] Consumer subscribed to {self.topic}, group {self.group_id}")

    def consume_messages(self, process_function):
        """
        Continuously consume messages and pass them to process_function.
        process_function(message: dict) -> None
        """
        logger.info(f"[KAFKA] Starting message consumption on {self.topic}")
        try:
            for msg in self.consumer:
                try:
                    logger.debug(f"[KAFKA] Received message: {msg.value}")
                    process_function(msg.value)
                except Exception as e:
                    logger.error(f"[KAFKA] Error processing message {msg.value}: {e}")
        except Exception as e:
            logger.error(f"[KAFKA] Consumer loop crashed: {e}")
            raise  # re-raise so your agent knows something went wrong

    def close(self):
        """Close Kafka consumer safely."""
        try:
            self.consumer.close()
            logger.info(f"[KAFKA] Consumer closed for topic {self.topic}, group {self.group_id}")
        except Exception as e:
            logger.error(f"[KAFKA] Error while closing consumer: {e}")
