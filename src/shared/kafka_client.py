"""
AgentMeshKafka - Kafka Client Wrappers
=======================================
Wrappers pour Confluent Kafka Producer et Consumer.

NOTE D'ARCHITECTURE:
--------------------
Bien que l'architecture (ADR-002) spécifie l'utilisation d'Avro et du Schema Registry,
l'implémentation actuelle utilise un fallback JSON pour faciliter le développement local
et les tests sans infrastructure lourde.

État actuel:
- Sérialisation: JSON (utf-8)
- Validation Schema: Partielle (via Pydantic models en amont, pas de Schema Registry)

Cible (TODO):
- Intégrer `confluent_kafka.schema_registry`
- Utiliser `AvroSerializer` et `AvroDeserializer`
"""

import os
from typing import Any, Generator, Optional
import json

import structlog
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from dotenv import load_dotenv

load_dotenv()
logger = structlog.get_logger()


class KafkaProducerClient:
    """
    Client Producer Kafka.
    
    Actuellement implémenté avec sérialisation JSON.
    Doit évoluer vers Avro + Schema Registry.
    """
    
    def __init__(
        self, 
        topic: str,
        schema_subject: Optional[str] = None,
    ):
        """
        Initialise le producer Kafka.

        Args:
            topic: Nom du topic Kafka cible.
            schema_subject: (Futur) Subject pour le Schema Registry Avro.
        """
        self.topic = topic
        self.schema_subject = schema_subject
        
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        # Configuration standard du Producer pour la fiabilité
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "client.id": f"agentmesh-producer-{topic}",
            "acks": "all",  # Strong consistency: attendre tous les replicas
            "retries": 3,   # Réessayer en cas d'erreur transitoire
            "retry.backoff.ms": 1000,
        })
        
        logger.info(
            "KafkaProducerClient initialized (JSON Mode)",
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
            value: Payload du message (dict qui sera converti en JSON)
            headers: Headers optionnels pour le traçage (OpenTelemetry, etc.)
            
        Returns:
            bool: True si le message a été mis dans le buffer d'envoi avec succès.
                  Note: La confirmation réelle est asynchrone via _delivery_callback.
        """
        try:
            # Sérialisation JSON (Fallback temporaire au lieu d'Avro)
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
            
            # Flush pour s'assurer que les messages partent immédiatement (pour ce POC)
            # En production haute performance, on ferait moins de flush.
            messages_in_queue = self.producer.flush(timeout=10)
            
            if messages_in_queue > 0:
                logger.warning("Producer flush timeout, some messages might not be delivered")
                return False

            return True
            
        except KafkaException as e:
            logger.error("Kafka produce error", error=str(e), topic=self.topic)
            return False
        except Exception as e:
            logger.error("Unexpected error during produce", error=str(e), topic=self.topic)
            return False
    
    def _delivery_callback(self, err, msg):
        """Callback appelé par librdkafka après tentative d'envoi."""
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
        """Ferme proprement le producer."""
        self.producer.flush()
        logger.info("KafkaProducerClient closed", topic=self.topic)


class KafkaConsumerClient:
    """
    Client Consumer Kafka.
    
    Actuellement implémenté avec désérialisation JSON.
    Doit évoluer vers Avro + Schema Registry.
    """
    
    def __init__(
        self,
        topic: str,
        group_id: str,
        auto_offset_reset: str = "earliest",
    ):
        """
        Initialise le consumer Kafka.

        Args:
            topic: Nom du topic à écouter.
            group_id: ID du groupe de consommateurs (pour le load balancing).
            auto_offset_reset: Comportement si pas d'offset ('earliest' ou 'latest').
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
        
        logger.info(
            "KafkaConsumerClient initialized (JSON Mode)",
            topic=topic,
            group_id=group_id,
            bootstrap_servers=bootstrap_servers,
        )
    
    def consume(
        self, 
        timeout: float = 1.0,
    ) -> Generator[Any, None, None]:
        """
        Générateur infini qui yield les messages du topic.
        
        Args:
            timeout: Temps d'attente (polling) en secondes.
            
        Yields:
            MessageWrapper: Objet contenant value, key, topic, etc.
        """
        while True:
            msg = self.consumer.poll(timeout=timeout)
            
            if msg is None:
                # Pas de message reçu pendant le timeout
                yield None
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug("End of partition reached", topic=msg.topic())
                    continue
                else:
                    logger.error("Consumer error", error=msg.error())
                    # On lève l'exception pour que l'agent puisse décider d'arrêter ou de restart
                    raise KafkaException(msg.error())
            
            try:
                # Désérialisation JSON (Fallback)
                value = json.loads(msg.value().decode("utf-8"))
                
                # Wrapper simple pour imiter l'interface objet du message Kafka
                class MessageWrapper:
                    def __init__(self, value, key, topic, partition, offset):
                        self._value = value
                        self._key = key
                        self._topic = topic
                        self._partition = partition
                        self._offset = offset
                    
                    def value(self): return self._value
                    def key(self): return self._key
                    def topic(self): return self._topic
                    def partition(self): return self._partition
                    def offset(self): return self._offset
                
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
                
            except json.JSONDecodeError as e:
                logger.error("JSON Deserialization error", error=str(e), payload=msg.value())
                # En prod, il faudrait envoyer ce message vers une Dead Letter Queue (DLQ)
                continue
            except Exception as e:
                logger.error("Unexpected error during consumption", error=str(e))
                continue
    
    def close(self):
        """Ferme proprement le consumer."""
        self.consumer.close()
        logger.info("KafkaConsumerClient closed", topic=self.topic)
