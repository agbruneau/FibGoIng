"""
Phase 2 - Kafka Client Wrappers
=================================
Wrappers simplifiés pour Confluent Kafka Producer et Consumer.
Version sans Schema Registry (JSON uniquement).
"""

import os
import json
from typing import Any, Generator, Optional

from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from dotenv import load_dotenv

load_dotenv()


class KafkaProducerClient:
    """
    Client Producer Kafka avec sérialisation JSON.
    
    Publie des messages dans un topic.
    """
    
    def __init__(self, topic: str):
        """
        Args:
            topic: Nom du topic Kafka
        """
        self.topic = topic
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "client.id": f"agentmesh-producer-{topic}",
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 1000,
        })
        
        print(f"✅ Producer initialisé pour topic: {topic}")
    
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
            print(f"❌ Erreur Kafka: {e}")
            return False
    
    def _delivery_callback(self, err, msg):
        """Callback appelé après delivery."""
        if err is not None:
            print(f"❌ Échec de livraison: {err}")
        else:
            print(f"✅ Message livré: topic={msg.topic()}, partition={msg.partition()}, offset={msg.offset()}")
    
    def close(self):
        """Ferme le producer."""
        self.producer.flush()
        print(f"✅ Producer fermé pour topic: {self.topic}")


class KafkaConsumerClient:
    """
    Client Consumer Kafka avec désérialisation JSON.
    
    Consomme des messages depuis un topic.
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
        
        print(f"✅ Consumer initialisé: topic={topic}, group={group_id}")
    
    def consume(
        self, 
        timeout: float = 1.0,
    ) -> Generator[Any, None, None]:
        """
        Générateur qui yield les messages du topic.
        
        Args:
            timeout: Timeout de poll en secondes
            
        Yields:
            Messages désérialisés (dict) ou None
        """
        while True:
            msg = self.consumer.poll(timeout=timeout)
            
            if msg is None:
                yield None
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"❌ Erreur Consumer: {msg.error()}")
                    raise KafkaException(msg.error())
            
            # Désérialiser le message
            try:
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
                
                print(f"📨 Message reçu: topic={msg.topic()}, partition={msg.partition()}, offset={msg.offset()}")
                
                yield wrapper
                
            except Exception as e:
                print(f"❌ Erreur de désérialisation: {e}")
                continue
    
    def close(self):
        """Ferme le consumer."""
        self.consumer.close()
        print(f"✅ Consumer fermé: topic={self.topic}")
