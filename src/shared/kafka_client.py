"""
AgentMeshKafka - Kafka Client Wrappers
=======================================
Wrappers pour Confluent Kafka Producer et Consumer
avec support Schema Registry (Avro).

Features:
- Sérialisation JSON (Avro en production)
- Propagation automatique du correlation_id via headers
- Health checks pour monitoring
- Métriques Prometheus intégrées

Voir docs/01-ArchitectureDecisions.md (ADR-001, ADR-002).
"""

import os
import time
from datetime import datetime, timezone
from typing import Any, Generator, Optional

import structlog
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException, TopicPartition
from confluent_kafka.serialization import SerializationContext, MessageField
from dotenv import load_dotenv

load_dotenv()
logger = structlog.get_logger()

# Header pour la propagation du correlation_id
CORRELATION_ID_HEADER = "X-Correlation-ID"
APPLICATION_ID_HEADER = "X-Application-ID"


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
        correlation_id: Optional[str] = None,
    ) -> bool:
        """
        Publie un message dans le topic.
        
        Propage automatiquement le correlation_id via les headers Kafka
        pour permettre le tracing distribué.
        
        Args:
            key: Clé de partitionnement (ex: application_id)
            value: Payload du message (dict)
            headers: Headers optionnels
            correlation_id: ID de corrélation pour le tracing (optionnel,
                           récupéré du contexte si non fourni)
            
        Returns:
            True si production réussie
        """
        try:
            # Récupérer le correlation_id du contexte si non fourni
            if correlation_id is None:
                try:
                    from src.shared.logging_config import get_correlation_id, generate_correlation_id
                    correlation_id = get_correlation_id() or generate_correlation_id()
                except ImportError:
                    import uuid
                    correlation_id = str(uuid.uuid4())
            
            # TODO: Utiliser AvroSerializer pour la sérialisation
            # Pour le squelette, on utilise JSON
            import json
            serialized_value = json.dumps(value).encode("utf-8")
            
            # Construire les headers avec correlation_id
            kafka_headers = []
            if headers:
                kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]
            
            # Ajouter le correlation_id aux headers
            kafka_headers.append((CORRELATION_ID_HEADER, correlation_id.encode("utf-8")))
            
            # Ajouter l'application_id si présent dans le value
            if "application_id" in value:
                kafka_headers.append(
                    (APPLICATION_ID_HEADER, str(value["application_id"]).encode("utf-8"))
                )
            
            self.producer.produce(
                topic=self.topic,
                key=key.encode("utf-8"),
                value=serialized_value,
                headers=kafka_headers,
                callback=self._delivery_callback,
            )
            
            # Flush pour garantir l'envoi
            self.producer.flush(timeout=10)
            
            logger.debug(
                "Message produced",
                topic=self.topic,
                key=key,
                correlation_id=correlation_id,
            )
            
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
    
    def health_check(self) -> dict[str, Any]:
        """
        Vérifie la santé du consumer Kafka.
        
        Effectue les vérifications suivantes:
        - Connexion au broker
        - Topics souscrits
        - Lag du consumer (différence entre highwater et offset commité)
        
        Returns:
            Dictionnaire avec le statut de santé:
            {
                "status": "healthy" | "unhealthy",
                "broker_connected": bool,
                "topics_subscribed": list[str],
                "partitions": [
                    {
                        "topic": str,
                        "partition": int,
                        "lag": int,
                        "committed_offset": int,
                        "high_watermark": int
                    }
                ],
                "total_lag": int,
                "last_check_time": str (ISO 8601)
            }
            
        Example:
            health = consumer.health_check()
            if health["status"] == "unhealthy":
                alert_ops_team(health)
        """
        result = {
            "status": "healthy",
            "broker_connected": False,
            "topics_subscribed": [],
            "partitions": [],
            "total_lag": 0,
            "last_check_time": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            # Vérifier la connexion au broker via list_topics
            cluster_metadata = self.consumer.list_topics(timeout=5)
            result["broker_connected"] = True
            
            # Récupérer les topics souscrits
            result["topics_subscribed"] = [self.topic]
            
            # Récupérer les partitions assignées
            assignment = self.consumer.assignment()
            
            if not assignment:
                # Pas encore de partitions assignées
                logger.debug("No partitions assigned yet")
                return result
            
            total_lag = 0
            
            for tp in assignment:
                partition_info = {
                    "topic": tp.topic,
                    "partition": tp.partition,
                    "lag": 0,
                    "committed_offset": -1,
                    "high_watermark": -1,
                }
                
                try:
                    # Récupérer le high watermark
                    low, high = self.consumer.get_watermark_offsets(tp, timeout=5)
                    partition_info["high_watermark"] = high
                    
                    # Récupérer l'offset commité
                    committed = self.consumer.committed([tp], timeout=5)
                    if committed and committed[0] and committed[0].offset >= 0:
                        partition_info["committed_offset"] = committed[0].offset
                        partition_info["lag"] = high - committed[0].offset
                        total_lag += partition_info["lag"]
                        
                        # Mettre à jour les métriques Prometheus
                        try:
                            from src.shared.metrics import update_consumer_lag
                            update_consumer_lag(
                                topic=tp.topic,
                                group_id=self.group_id,
                                partition=tp.partition,
                                lag=partition_info["lag"],
                            )
                        except ImportError:
                            pass
                    
                except Exception as e:
                    logger.warning(
                        "Failed to get watermark offsets",
                        topic=tp.topic,
                        partition=tp.partition,
                        error=str(e),
                    )
                
                result["partitions"].append(partition_info)
            
            result["total_lag"] = total_lag
            
            # Définir le statut basé sur le lag
            # Lag > 10000 = potentiellement unhealthy
            if total_lag > 10000:
                result["status"] = "degraded"
                logger.warning("High consumer lag detected", lag=total_lag)
            
        except KafkaException as e:
            result["status"] = "unhealthy"
            result["error"] = str(e)
            logger.error("Kafka health check failed", error=str(e))
            
        except Exception as e:
            result["status"] = "unhealthy"
            result["error"] = str(e)
            logger.error("Health check error", error=str(e))
        
        return result
    
    def extract_correlation_id(self, message) -> Optional[str]:
        """
        Extrait le correlation_id des headers d'un message.
        
        Args:
            message: Message Kafka (ou MessageWrapper)
            
        Returns:
            Correlation ID ou None si non présent
        """
        try:
            # Essayer d'accéder aux headers selon le type de message
            headers = None
            if hasattr(message, "headers"):
                headers = message.headers()
            
            if headers:
                for key, value in headers:
                    if key == CORRELATION_ID_HEADER:
                        return value.decode("utf-8")
        except Exception:
            pass
        
        return None
