# core/learning/store.py
"""Learning Store - Persistent storage for agent experiences and policies

Stores experiences and policy versions in MongoDB for continuous learning.
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import hashlib
import json

logger = logging.getLogger(__name__)


class LearningStore:
    """Manages persistent storage of agent learning data"""
    
    def __init__(self):
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://mongodb:27017')
        self.db_name = 'botai_trading'
        
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.experiences_col = None
        self.policies_col = None
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize MongoDB connection"""
        if self._initialized:
            return True
        
        try:
            self.client = AsyncIOMotorClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            
            # Collections
            self.experiences_col = self.db['agent_experiences']
            self.policies_col = self.db['policy_versions']
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Create indexes
            await self._create_indexes()
            
            self._initialized = True
            logger.info(f"✅ LearningStore initialized: {self.mongo_uri}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LearningStore: {e}")
            return False
    
    async def _create_indexes(self):
        """Create necessary indexes"""
        # Experiences indexes
        await self.experiences_col.create_index('agent')
        await self.experiences_col.create_index('t')
        await self.experiences_col.create_index([('agent', 1), ('t', -1)])
        
        # Policies indexes
        await self.policies_col.create_index('agent')
        await self.policies_col.create_index('created_at')
        await self.policies_col.create_index([('agent', 1), ('created_at', -1)])
        
        logger.info("Indexes created for learning collections")
    
    async def store_experience(
        self,
        agent_id: str,
        state_features: Dict[str, Any],
        decision: Dict[str, Any],
        outcome: Dict[str, Any],
        reward: float,
        consensus_meta: Optional[Dict[str, Any]] = None,
        market_ctx: Optional[Dict[str, Any]] = None,
        policy_id: Optional[str] = None
    ) -> bool:
        """Store an agent experience
        
        Args:
            agent_id: Agent identifier
            state_features: State representation (will be hashed)
            decision: Decision details (action, size, slot, etc.)
            outcome: Outcome metrics (pnl, slippage, latency)
            reward: Calculated reward value
            consensus_meta: Consensus metadata (conf_avg, peers)
            market_ctx: Market context (symbol, exchange)
            policy_id: Policy version used for this decision
        
        Returns:
            True if stored successfully
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Create state digest (hash of features)
            state_digest = self._hash_state(state_features)
            
            experience = {
                't': time.time(),
                'timestamp': datetime.now(timezone.utc),
                'agent': agent_id,
                'state_digest': state_digest,
                'state_features': state_features,
                'decision': decision,
                'outcome': outcome,
                'reward': reward,
                'consensus_meta': consensus_meta or {},
                'market_ctx': market_ctx or {},
                'policy_id': policy_id or 'default'
            }
            
            await self.experiences_col.insert_one(experience)
            
            logger.debug(f"Experience stored: agent={agent_id}, reward={reward:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing experience: {e}")
            return False
    
    def _hash_state(self, state_features: Dict[str, Any]) -> str:
        """Create a hash digest of state features"""
        # Sort keys for consistent hashing
        state_str = json.dumps(state_features, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]
    
    async def get_recent_experiences(
        self,
        agent_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent experiences for an agent
        
        Args:
            agent_id: Agent identifier
            limit: Maximum number of experiences to return
        
        Returns:
            List of experience documents
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            cursor = self.experiences_col.find(
                {'agent': agent_id}
            ).sort('t', -1).limit(limit)
            
            experiences = await cursor.to_list(length=limit)
            return experiences
            
        except Exception as e:
            logger.error(f"Error getting experiences: {e}")
            return []
    
    async def store_policy(
        self,
        agent_id: str,
        policy_data: Dict[str, Any],
        notes: str = ""
    ) -> Optional[str]:
        """Store a new policy version
        
        Args:
            agent_id: Agent identifier
            policy_data: Policy parameters (weights, thresholds, etc.)
            notes: Description of changes
        
        Returns:
            Policy ID if stored successfully, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate policy ID
            timestamp = int(time.time())
            policy_id = f"{agent_id}_{timestamp}"
            
            policy = {
                'policy_id': policy_id,
                'agent': agent_id,
                'created_at': datetime.now(timezone.utc),
                'timestamp': timestamp,
                'policy_data': policy_data,
                'notes': notes
            }
            
            await self.policies_col.insert_one(policy)
            
            logger.info(f"✅ Policy stored: {policy_id}")
            return policy_id
            
        except Exception as e:
            logger.error(f"Error storing policy: {e}")
            return None
    
    async def get_latest_policy(
        self,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the latest policy for an agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Policy document if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            policy = await self.policies_col.find_one(
                {'agent': agent_id},
                sort=[('created_at', -1)]
            )
            
            return policy
            
        except Exception as e:
            logger.error(f"Error getting latest policy: {e}")
            return None
    
    async def get_experience_stats(
        self,
        agent_id: str,
        since_timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get statistics about agent experiences
        
        Args:
            agent_id: Agent identifier
            since_timestamp: Only count experiences after this timestamp
        
        Returns:
            Statistics dictionary
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            query = {'agent': agent_id}
            if since_timestamp:
                query['t'] = {'$gte': since_timestamp}
            
            # Count total experiences
            total = await self.experiences_col.count_documents(query)
            
            # Calculate average reward
            pipeline = [
                {'$match': query},
                {'$group': {
                    '_id': None,
                    'avg_reward': {'$avg': '$reward'},
                    'max_reward': {'$max': '$reward'},
                    'min_reward': {'$min': '$reward'}
                }}
            ]
            
            cursor = self.experiences_col.aggregate(pipeline)
            agg_result = await cursor.to_list(length=1)
            
            stats = {
                'total_experiences': total,
                'avg_reward': agg_result[0]['avg_reward'] if agg_result else 0.0,
                'max_reward': agg_result[0]['max_reward'] if agg_result else 0.0,
                'min_reward': agg_result[0]['min_reward'] if agg_result else 0.0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting experience stats: {e}")
            return {'total_experiences': 0, 'avg_reward': 0.0}


# Global store instance
learning_store = LearningStore()
