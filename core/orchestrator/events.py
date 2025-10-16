# core/orchestrator/events.py
"""Event Publisher and Agent Communication - Phase 2"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class AgentMessage:
    """Message between agents"""
    
    def __init__(
        self,
        from_agent: str,
        to_agent: str,
        topic: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.topic = topic
        self.message = message
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "topic": self.topic,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class AgentDialog:
    """Dialog session between multiple agents"""
    
    def __init__(self, topic: str, participants: List[str]):
        self.dialog_id = f"dialog_{int(datetime.now(timezone.utc).timestamp())}"
        self.topic = topic
        self.participants = participants
        self.messages: List[AgentMessage] = []
        self.started_at = datetime.now(timezone.utc)
        self.ended_at = None
        self.outcome = None
    
    def add_message(self, message: AgentMessage):
        """Add message to dialog"""
        self.messages.append(message)
    
    def close(self, outcome: str):
        """Close dialog with outcome"""
        self.ended_at = datetime.now(timezone.utc)
        self.outcome = outcome
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "dialog_id": self.dialog_id,
            "topic": self.topic,
            "participants": self.participants,
            "messages": [msg.to_dict() for msg in self.messages],
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "outcome": self.outcome
        }


class EventPublisher:
    """Event publisher with MongoDB persistence - Phase 2"""
    
    def __init__(self):
        self.event_count = 0
        self.message_queue = asyncio.Queue() if asyncio.get_event_loop().is_running() else None
        self.mongo_client = None
        self.db = None
        self.redis_client = None
        
        # In-memory event buffer for SSE (últimos 100 eventos)
        self.recent_events: List[Dict[str, Any]] = []
        self.max_events = 100
        
        # Initialize MongoDB
        self._init_mongodb()
        
        # Initialize Redis with proper timeouts
        self._init_redis()
        
        logger.info("Event Publisher initialized (Phase 2 with MongoDB + Redis)")
    
    def _init_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            mongo_uri = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/botai_trading')
            self.mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.mongo_client.admin.command('ping')
            
            # Get database
            db_name = os.getenv('MONGO_DATABASE', 'botai_trading')
            self.db = self.mongo_client[db_name]
            
            # Create indexes
            self._create_indexes()
            
            logger.info(f"✅ MongoDB connected: {db_name}")
            
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e} - will work without persistence")
            self.mongo_client = None
            self.db = None
    
    def _init_redis(self):
        """Initialize Redis connection with proper timeouts"""
        try:
            import aioredis
            redis_host = os.getenv('REDIS_HOST', 'redis')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_url = f"redis://{redis_host}:{redis_port}"
            
            # Create Redis client with increased timeouts
            self.redis_client = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10,
                retry_on_timeout=True
            )
            
            logger.info(f"✅ Redis connected: {redis_url}")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} - pub/sub will not be available")
            self.redis_client = None
    
    def _create_indexes(self):
        """Create indexes for collections"""
        if not self.db:
            return
        
        try:
            # agent_decisions indexes
            self.db.agent_decisions.create_index([("agent_id", 1), ("timestamp", -1)])
            self.db.agent_decisions.create_index([("symbol", 1), ("timestamp", -1)])
            
            # agent_dialogs indexes
            self.db.agent_dialogs.create_index([("participants", 1), ("started_at", -1)])
            self.db.agent_dialogs.create_index([("topic", 1)])
            
            # agent_runs indexes
            self.db.agent_runs.create_index([("agent_id", 1), ("timestamp", -1)])
            
            logger.info("✅ MongoDB indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    def publish(self, event: Dict[str, Any]) -> bool:
        """
        Publish event
        
        Args:
            event: Event dictionary to publish
        
        Returns:
            Success status
        """
        self.event_count += 1
        event_type = event.get('type', 'unknown')
        
        # Adiciona ID sequencial e timestamp
        event['id'] = self.event_count
        if 'timestamp' not in event:
            event['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Armazena em buffer para SSE
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_events:
            self.recent_events.pop(0)  # Remove o mais antigo
        
        logger.debug(f"Event published: {event_type}")
        
        # Redis Pub/Sub with retry logic
        if self.redis_client:
            import json
            channel = f"orchestrator:events:{event_type}"
            
            # Retry up to 3 times
            for attempt in range(3):
                try:
                    asyncio.create_task(self._publish_to_redis(channel, json.dumps(event)))
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.warning(f"Redis publish failed after 3 attempts: {e}")
                    else:
                        asyncio.sleep(1)
        
        return True
    
    async def _publish_to_redis(self, channel: str, message: str):
        """Publish message to Redis with retry logic"""
        if not self.redis_client:
            return
        
        for attempt in range(3):
            try:
                await self.redis_client.publish(channel, message)
                break
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Redis publish failed: {e}")
                else:
                    await asyncio.sleep(1)
    
    def get_recent_events(self, since_id: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém eventos recentes desde um ID específico
        
        Args:
            since_id: ID do último evento recebido
            limit: Máximo de eventos a retornar
        
        Returns:
            Lista de eventos
        """
        # Filtra eventos com ID maior que since_id
        events = [e for e in self.recent_events if e.get('id', 0) > since_id]
        
        # Retorna até o limite
        return events[-limit:] if len(events) > limit else events
    
    def save_decision(self, decision_data: Dict[str, Any]) -> bool:
        """
        Save decision to MongoDB
        
        Args:
            decision_data: Decision data dictionary
        
        Returns:
            Success status
        """
        if not self.db:
            logger.warning("MongoDB not available, decision not persisted")
            return False
        
        try:
            # Add timestamp if not present
            if 'timestamp' not in decision_data:
                decision_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Insert into agent_decisions collection
            result = self.db.agent_decisions.insert_one(decision_data)
            
            logger.debug(f"Decision saved: {result.inserted_id}")
            return True
            
        except PyMongoError as e:
            logger.error(f"Failed to save decision: {e}")
            return False
    
    def save_dialog(self, dialog: AgentDialog) -> bool:
        """
        Save dialog to MongoDB
        
        Args:
            dialog: AgentDialog object
        
        Returns:
            Success status
        """
        if not self.db:
            logger.warning("MongoDB not available, dialog not persisted")
            return False
        
        try:
            # Insert into agent_dialogs collection
            result = self.db.agent_dialogs.insert_one(dialog.to_dict())
            
            logger.debug(f"Dialog saved: {result.inserted_id}")
            return True
            
        except PyMongoError as e:
            logger.error(f"Failed to save dialog: {e}")
            return False
    
    def save_consensus_round(self, consensus_data: Dict[str, Any]) -> bool:
        """
        Save consensus round to MongoDB - Phase 4
        
        Args:
            consensus_data: Consensus round data
        
        Returns:
            Success status
        """
        if not self.db:
            logger.warning("MongoDB not available, consensus not persisted")
            return False
        
        try:
            # Add timestamp if not present
            if 'timestamp' not in consensus_data:
                consensus_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Insert into agent_consensus collection
            result = self.db.agent_consensus.insert_one(consensus_data)
            
            logger.debug(f"Consensus round saved: {result.inserted_id}")
            return True
            
        except PyMongoError as e:
            logger.error(f"Failed to save consensus round: {e}")
            return False
    
    def save_agent_dialog(self, dialog_doc: Dict[str, Any]) -> bool:
        """
        Save agent dialog message to MongoDB - Phase 4
        
        Args:
            dialog_doc: Dialog message document with:
                - consensus_id
                - phase (propose, challenge, decide)
                - agent_id
                - symbol
                - timeframe
                - content (raw LLM response)
                - confidence (optional)
                - rationale (optional)
                - ts
        
        Returns:
            Success status
        """
        if not self.db:
            logger.warning("MongoDB not available, dialog not persisted")
            return False
        
        try:
            # Ensure timestamp
            if 'ts' not in dialog_doc:
                dialog_doc['ts'] = datetime.now(timezone.utc).isoformat()
            
            # Insert into agent_dialogs collection
            result = self.db.agent_dialogs.insert_one(dialog_doc)
            
            logger.debug(f"Agent dialog saved: {result.inserted_id}")
            return True
            
        except PyMongoError as e:
            logger.error(f"Failed to save agent dialog: {e}")
            return False
    
    def get_recent_consensus_rounds(
        self,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent consensus rounds from MongoDB - Phase 3
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum number of results
        
        Returns:
            List of consensus round dictionaries
        """
        if not self.db:
            return []
        
        try:
            query = {}
            if symbol:
                query['symbol'] = symbol
            
            cursor = self.db.agent_consensus.find(query).sort('timestamp', -1).limit(limit)
            rounds = list(cursor)
            
            # Convert ObjectId to string
            for r in rounds:
                r['_id'] = str(r['_id'])
            
            return rounds
            
        except PyMongoError as e:
            logger.error(f"Failed to get consensus rounds: {e}")
            return []
    
    def save_agent_run(self, agent_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Save agent run event (start, stop, error)
        
        Args:
            agent_id: Agent identifier
            event_type: Type of event (started, stopped, error)
            data: Additional data
        
        Returns:
            Success status
        """
        if not self.db:
            return False
        
        try:
            run_data = {
                "agent_id": agent_id,
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.db.agent_runs.insert_one(run_data)
            return True
            
        except PyMongoError as e:
            logger.error(f"Failed to save agent run: {e}")
            return False
    
    def get_recent_decisions(
        self,
        agent_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent decisions from MongoDB
        
        Args:
            agent_id: Filter by agent ID (optional)
            symbol: Filter by symbol (optional)
            limit: Maximum number of results
        
        Returns:
            List of decision dictionaries
        """
        if not self.db:
            return []
        
        try:
            query = {}
            if agent_id:
                query['agent_id'] = agent_id
            if symbol:
                query['symbol'] = symbol
            
            cursor = self.db.agent_decisions.find(query).sort('timestamp', -1).limit(limit)
            decisions = list(cursor)
            
            # Convert ObjectId to string
            for d in decisions:
                d['_id'] = str(d['_id'])
            
            return decisions
            
        except PyMongoError as e:
            logger.error(f"Failed to get decisions: {e}")
            return []
    
    def get_recent_dialogs(
        self,
        participant: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent dialogs from MongoDB
        
        Args:
            participant: Filter by participant (optional)
            limit: Maximum number of results
        
        Returns:
            List of dialog dictionaries
        """
        if not self.db:
            return []
        
        try:
            query = {}
            if participant:
                query['participants'] = participant
            
            cursor = self.db.agent_dialogs.find(query).sort('started_at', -1).limit(limit)
            dialogs = list(cursor)
            
            # Convert ObjectId to string
            for d in dialogs:
                d['_id'] = str(d['_id'])
            
            return dialogs
            
        except PyMongoError as e:
            logger.error(f"Failed to get dialogs: {e}")
            return []
    
    def send_message(self, message: AgentMessage) -> bool:
        """
        Send message between agents
        
        Args:
            message: AgentMessage object
        
        Returns:
            Success status
        """
        logger.info(
            f"Message: {message.from_agent} → {message.to_agent}: "
            f"{message.topic}"
        )
        
        # Add to queue if available
        if self.message_queue:
            try:
                self.message_queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Message queue full, message dropped")
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get publisher statistics"""
        stats = {
            'events_published': self.event_count,
            'mongodb_connected': self.db is not None,
            'phase': 2
        }
        
        if self.db:
            try:
                stats['total_decisions'] = self.db.agent_decisions.count_documents({})
                stats['total_dialogs'] = self.db.agent_dialogs.count_documents({})
                stats['total_runs'] = self.db.agent_runs.count_documents({})
            except Exception as e:
                logger.warning(f"Failed to get stats: {e}")
        
        return stats


# Global instance
event_publisher = EventPublisher()


# Helper functions for easy access
def save_decision(decision_data: Dict[str, Any]) -> bool:
    """Save decision to MongoDB"""
    return event_publisher.save_decision(decision_data)


def save_dialog(dialog: AgentDialog) -> bool:
    """Save dialog to MongoDB"""
    return event_publisher.save_dialog(dialog)


def create_dialog(topic: str, participants: List[str]) -> AgentDialog:
    """Create a new dialog"""
    return AgentDialog(topic, participants)


def save_consensus_round(consensus_data: Dict[str, Any]) -> bool:
    """Save consensus round to MongoDB - Phase 3"""
    return event_publisher.save_consensus_round(consensus_data)


def get_recent_consensus_rounds(symbol: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent consensus rounds - Phase 4"""
    return event_publisher.get_recent_consensus_rounds(symbol, limit)


def get_dialogs_by_consensus(consensus_id: str) -> List[Dict[str, Any]]:
    """Get all dialog messages for a consensus round - Phase 4"""
    if not event_publisher.db:
        return []
    
    try:
        cursor = event_publisher.db.agent_dialogs.find(
            {'consensus_id': consensus_id}
        ).sort('ts', 1)
        dialogs = list(cursor)
        
        # Convert ObjectId to string
        for d in dialogs:
            d['_id'] = str(d['_id'])
        
        return dialogs
    except Exception as e:
        logger.error(f"Failed to get dialogs for consensus {consensus_id}: {e}")
        return []
