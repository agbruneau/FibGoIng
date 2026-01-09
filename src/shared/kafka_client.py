"""
AgentMeshKafka - Kafka Client Wrappers
=======================================
Wrappers pour Confluent Kafka Producer et Consumer
avec support Schema Registry (Avro).

Voir docs/01-ArchitectureDecisions.md (ADR-001, ADR-002).
"""

import os
from typing import Any, Generator, Optional

import structlog
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from confluent_kafka.serialization import SerializationContext, MessageField
from dotenv import load_dotenv

load_dotenv()
logger = structlog.get_logger()


class KafkaProducerClient:
    """
    Client Producer Kafka avec sérialisation Avro.
    
    Publie des messages dans un topic avec validation de schéma.
    """
    
    def __init__(
        self, 
        topic: str,
        schema_subject: Optional[str] = None,
    ):
        """
        Args:
            topic: Nom du topic Kafka
            schema_subject: Subject dans le Schema Registry (optionnel)
        """
        self.topic = topic
        self.schema_subject = schema_subject
        
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "client.id": f"agentmesh-producer-{topic}",
            "acks": "all",  # Attendre confirmation de tous les replicas
            "retries": 3,
            "retry.backoff.ms": 1000,
        })
        
        # TODO: Configurer AvroSerializer avec Schema Registry
        # self.serializer = AvroSerializer(schema_registry_client, schema_str)
        
        logger.info(
            "KafkaProducerClient initialized",
            topic=topic,
            bootstrap_servers=bootstrap_servers,
        )
    
    def produce(
        self, 
        key: str, 
        value: dict[str, Any],
        headers: Optional[dict[str, str]] = None,
    ) -> bool:
        """
        Publie un message dans le topic.
        
        Args:
            key: Clé de partitionnement (ex: application_id)
            value: Payload du message (dict)
            headers: Headers optionnels
            
        Returns:
            True si production réussie
        """
        try:
            # TODO: Utiliser AvroSerializer pour la sérialisation
            # Pour le squelette, on utilise JSON
            import json
            serialized_value = json.dumps(value).encode("utf-8")
            
            kafka_headers = []
            if headers:
                kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]
            
            self.producer.produce(
                topic=self.topic,
                key=key.encode("utf-8"),
                value=serialized_value,
                headers=kafka_headers,
                callback=self._delivery_callback,
            )
            
            # Flush pour garantir l'envoi
            self.producer.flush(timeout=10)
            
            return True
            
        except KafkaException as e:
            logger.error("Kafka produce error", error=str(e), topic=self.topic)
            return False
    
    def _delivery_callback(self, err, msg):
        """Callback appelé après delivery."""
        if err is not None:
            logger.error(
                "Message delivery failed",
                error=str(err),
                topic=msg.topic(),
            )
        else:
            logger.debug(
                "Message delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )
    
    def close(self):
        """Ferme le producer."""
        self.producer.flush()
        logger.info("KafkaProducerClient closed", topic=self.topic)


class KafkaConsumerClient:
    """
    Client Consumer Kafka avec désérialisation Avro.
    
    Consomme des messages depuis un topic avec validation de schéma.
    """
    
    def __init__(
        self,
        topic: str,
        group_id: str,
        auto_offset_reset: str = "earliest",
    ):
        """
        Args:
            topic: Nom du topic Kafka
            group_id: ID du consumer group
            auto_offset_reset: "earliest" ou "latest"
        """
        self.topic = topic
        self.group_id = group_id
        
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        self.consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": auto_offset_reset,
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 5000,
            "session.timeout.ms": 30000,
        })
        
        self.consumer.subscribe([topic])
        
        # TODO: Configurer AvroDeserializer avec Schema Registry
        
        logger.info(
            "KafkaConsumerClient initialized",
            topic=topic,
            group_id=group_id,
            bootstrap_servers=bootstrap_servers,
        )
    
    def consume(
        self, 
        timeout: float = 1.0,
    ) -> Generator[Any, None, None]:
        """
        Générateur qui yield les messages du topic.
        
        Args:
            timeout: Timeout de poll en secondes
            
        Yields:
            Messages désérialisés
        """
        while True:
            msg = self.consumer.poll(timeout=timeout)
            
            if msg is None:
                yield None
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug("End of partition reached")
                    continue
                else:
                    logger.error("Consumer error", error=msg.error())
                    raise KafkaException(msg.error())
            
            # Désérialiser le message
            # TODO: Utiliser AvroDeserializer
            try:
                import json
                value = json.loads(msg.value().decode("utf-8"))
                
                # Créer un wrapper avec les métadonnées
                class MessageWrapper:
                    def __init__(self, value, key, topic, partition, offset):
                        self._value = value
                        self._key = key
                        self._topic = topic
                        self._partition = partition
                        self._offset = offset
                    
                    def value(self):
                        return self._value
                    
                    def key(self):
                        return self._key
                    
                    def topic(self):
                        return self._topic
                    
                    def partition(self):
                        return self._partition
                    
                    def offset(self):
                        return self._offset
                
                wrapper = MessageWrapper(
                    value=value,
                    key=msg.key().decode("utf-8") if msg.key() else None,
                    topic=msg.topic(),
                    partition=msg.partition(),
                    offset=msg.offset(),
                )
                
                logger.debug(
                    "Message consumed",
                    topic=msg.topic(),
                    partition=msg.partition(),
                    offset=msg.offset(),
                )
                
                yield wrapper
                
            except Exception as e:
                logger.error("Deserialization error", error=str(e))
                # TODO: Publier dans Dead Letter Queue
                continue
    
    def close(self):
        """Ferme le consumer."""
        self.consumer.close()
        logger.info("KafkaConsumerClient closed", topic=self.topic)
