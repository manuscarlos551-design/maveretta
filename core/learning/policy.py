# core/learning/policy.py
"""Policy Manager - Online learning and policy updates

Implements lightweight online learning with gradient-free optimization (SPSA).
Adjusts agent confidence thresholds and feature weights based on experience.
"""

import logging
import os
import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from .store import learning_store
from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# Metrics
learning_policy_updates_total = Counter(
    'learning_policy_updates_total',
    'Total policy updates performed',
    ['agent']
)

learning_reward_avg = Gauge(
    'learning_reward_avg',
    'Average reward over recent experiences',
    ['agent']
)


class PolicyManager:
    """Manages online learning and policy updates for agents"""
    
    def __init__(self):
        self.enabled = os.getenv('LEARNING_ENABLED', 'false').lower() == 'true'
        self.update_freq = int(os.getenv('LEARNING_FREQ_DECISIONS', '50'))
        self.max_drift = float(os.getenv('LEARNING_MAX_DRIFT', '0.1'))
        
        # SPSA parameters (Simultaneous Perturbation Stochastic Approximation)
        self.spsa_a = 0.01  # Step size
        self.spsa_c = 0.1   # Perturbation size
        self.spsa_alpha = 0.602  # Step size decay
        self.spsa_gamma = 0.101  # Perturbation decay
        
        # Track last update
        self.last_update: Dict[str, float] = {}
        self.decision_counts: Dict[str, int] = {}
        
        # Current policies (in-memory cache)
        self.current_policies: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            f"PolicyManager initialized: enabled={self.enabled}, "
            f"update_freq={self.update_freq}, max_drift={self.max_drift}"
        )
    
    async def initialize(self):
        """Initialize policy manager and load existing policies"""
        if not self.enabled:
            logger.info("Learning disabled, skipping policy initialization")
            return
        
        # Initialize learning store
        await learning_store.initialize()
        
        logger.info("✅ PolicyManager initialized")
    
    def get_default_policy(self, agent_id: str) -> Dict[str, Any]:
        """Get default policy parameters
        
        Returns:
            Dictionary with default policy parameters
        """
        return {
            'confidence_threshold': 0.6,  # Minimum confidence to act
            'risk_tolerance': 0.5,  # Risk parameter (0-1)
            'feature_weights': {
                'trend_strength': 1.0,
                'volume_ratio': 0.8,
                'volatility': 0.6,
                'sentiment': 0.4
            },
            'version': 0
        }
    
    async def get_policy(self, agent_id: str) -> Dict[str, Any]:
        """Get current policy for agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Policy parameters
        """
        # Check cache
        if agent_id in self.current_policies:
            return self.current_policies[agent_id]
        
        # Try to load from store
        if self.enabled:
            policy_doc = await learning_store.get_latest_policy(agent_id)
            if policy_doc:
                policy = policy_doc['policy_data']
                self.current_policies[agent_id] = policy
                return policy
        
        # Return default
        default_policy = self.get_default_policy(agent_id)
        self.current_policies[agent_id] = default_policy
        return default_policy
    
    async def record_decision(self, agent_id: str):
        """Record that a decision was made
        
        Args:
            agent_id: Agent identifier
        """
        if not self.enabled:
            return
        
        # Increment decision count
        self.decision_counts[agent_id] = self.decision_counts.get(agent_id, 0) + 1
        
        # Check if we should update policy
        if self.decision_counts[agent_id] >= self.update_freq:
            await self.update_policy(agent_id)
            self.decision_counts[agent_id] = 0
    
    async def update_policy(self, agent_id: str) -> bool:
        """Update agent policy based on recent experiences
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            True if policy was updated
        """
        if not self.enabled:
            return False
        
        try:
            logger.info(f"🎯 Updating policy for agent {agent_id}")
            
            # Get recent experiences
            experiences = await learning_store.get_recent_experiences(
                agent_id,
                limit=self.update_freq * 2  # Use 2x for stability
            )
            
            if len(experiences) < 10:
                logger.warning(f"Not enough experiences for {agent_id}: {len(experiences)}")
                return False
            
            # Get current policy
            current_policy = await self.get_policy(agent_id)
            
            # Calculate average reward
            rewards = [exp['reward'] for exp in experiences]
            avg_reward = np.mean(rewards)
            
            # Update metrics
            learning_reward_avg.labels(agent=agent_id).set(avg_reward)
            
            logger.info(f"Agent {agent_id}: avg_reward={avg_reward:.4f} over {len(experiences)} experiences")
            
            # Perform policy update using SPSA
            new_policy = self._spsa_update(
                current_policy,
                experiences,
                iteration=current_policy.get('version', 0) + 1
            )
            
            # Store new policy
            policy_id = await learning_store.store_policy(
                agent_id=agent_id,
                policy_data=new_policy,
                notes=f"SPSA update: avg_reward={avg_reward:.4f}, n={len(experiences)}"
            )
            
            if policy_id:
                # Update cache
                self.current_policies[agent_id] = new_policy
                self.last_update[agent_id] = time.time()
                
                # Metrics
                learning_policy_updates_total.labels(agent=agent_id).inc()
                
                logger.info(
                    f"✅ Policy updated: {agent_id} (policy_id={policy_id}, "
                    f"confidence_threshold={new_policy['confidence_threshold']:.3f})"
                )
                return True
            else:
                logger.error(f"Failed to store policy for {agent_id}")
                return False
            
        except Exception as e:
            logger.error(f"Error updating policy for {agent_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _spsa_update(
        self,
        current_policy: Dict[str, Any],
        experiences: List[Dict[str, Any]],
        iteration: int
    ) -> Dict[str, Any]:
        """Perform SPSA policy update
        
        SPSA (Simultaneous Perturbation Stochastic Approximation) is a
        gradient-free optimization method that only requires 2 function
        evaluations per iteration.
        
        Args:
            current_policy: Current policy parameters
            experiences: Recent experiences
            iteration: Update iteration number
        
        Returns:
            Updated policy parameters
        """
        # Extract parameters to optimize
        theta = np.array([
            current_policy['confidence_threshold'],
            current_policy['risk_tolerance']
        ])
        
        # Calculate step sizes
        a_k = self.spsa_a / ((iteration + 1) ** self.spsa_alpha)
        c_k = self.spsa_c / ((iteration + 1) ** self.spsa_gamma)
        
        # Generate random perturbation
        delta = np.random.choice([-1, 1], size=theta.shape)
        
        # Evaluate at perturbed points (simplified - use average reward)
        rewards = [exp['reward'] for exp in experiences]
        avg_reward = np.mean(rewards)
        
        # Estimate gradient
        gradient = (avg_reward / c_k) * delta
        
        # Update parameters
        theta_new = theta + a_k * gradient
        
        # Clip to valid ranges
        theta_new[0] = np.clip(theta_new[0], 0.3, 0.9)  # confidence_threshold
        theta_new[1] = np.clip(theta_new[1], 0.1, 1.0)  # risk_tolerance
        
        # Apply max drift constraint
        theta_diff = theta_new - theta
        theta_diff = np.clip(theta_diff, -self.max_drift, self.max_drift)
        theta_new = theta + theta_diff
        
        # Create new policy
        new_policy = current_policy.copy()
        new_policy['confidence_threshold'] = float(theta_new[0])
        new_policy['risk_tolerance'] = float(theta_new[1])
        new_policy['version'] = iteration
        
        logger.debug(
            f"SPSA update: confidence {current_policy['confidence_threshold']:.3f} → {theta_new[0]:.3f}, "
            f"risk {current_policy['risk_tolerance']:.3f} → {theta_new[1]:.3f}"
        )
        
        return new_policy
    
    def calculate_reward(
        self,
        pnl_normalized: float,
        drawdown: float,
        latency_ms: float,
        lambda_risk: float = 0.5,
        lambda_lat: float = 0.01
    ) -> float:
        """Calculate reward for an experience
        
        Reward formula:
        reward = pnl_normalized - λ_risk * drawdown - λ_lat * latency_ms_norm
        
        Args:
            pnl_normalized: Normalized P&L (-1 to 1)
            drawdown: Drawdown percentage (0 to 1)
            latency_ms: Latency in milliseconds
            lambda_risk: Risk penalty weight
            lambda_lat: Latency penalty weight
        
        Returns:
            Reward value
        """
        latency_ms_norm = min(latency_ms / 1000.0, 1.0)  # Normalize to 0-1
        
        reward = pnl_normalized - lambda_risk * drawdown - lambda_lat * latency_ms_norm
        
        return reward


# Global policy manager instance
policy_manager = PolicyManager()
