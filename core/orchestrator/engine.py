# core/orchestrator/engine.py
"""Agent Engine - Manages agent lifecycle and decision loop (Phase 2)"""

import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from .loader import AgentConfig, load_agents_configs
from .llm_clients import llm_client_manager
from .metrics import update_agent_mode, update_agent_heartbeat, update_agent_running
from .events import event_publisher

logger = logging.getLogger(__name__)


class AgentState:
    """State of a single agent"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.status = 'stopped'  # stopped | running
        self.mode = config.execution_mode  # shadow | paper | live
        self.last_tick = 0
        self.tick_count = 0
        self.created_at = time.time()
        self.started_at = None
        self.stopped_at = None
        self._thread = None
        self._stop_flag = threading.Event()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            'agent_id': self.config.agent_id,
            'provider': self.config.provider,
            'model': self.config.model,
            'status': self.status,
            'mode': self.mode,
            'last_tick': self.last_tick,
            'tick_count': self.tick_count,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'stopped_at': self.stopped_at,
            'role': self.config.role,
            'exchanges': self.config.exchanges,
            'symbols': self.config.symbols
        }


class AgentEngine:
    """Main engine for managing agents"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or '/app/config/agents'
        self.agents: Dict[str, AgentState] = {}
        self._initialized = False
        self._lock = threading.Lock()
        
        logger.info("Agent Engine initializing...")
    
    def initialize(self) -> tuple[bool, str]:
        """Initialize engine by loading agent configurations"""
        try:
            # Load agent configs from YAML files
            configs = load_agents_configs(self.config_dir)
            
            if not configs:
                logger.warning("No agent configurations loaded")
                return True, "No agents configured"
            
            # Create agent states
            for agent_id, config in configs.items():
                # Validate provider
                valid, error = llm_client_manager.validate_provider(
                    config.provider, 
                    config.api_key_env
                )
                
                if not valid:
                    logger.error(f"Agent {agent_id} validation failed: {error}")
                    continue
                
                # Create agent state
                agent_state = AgentState(config)
                self.agents[agent_id] = agent_state
                
                # Initialize metrics
                update_agent_mode(agent_id, agent_state.mode)
                update_agent_running(agent_id, False)
                update_agent_heartbeat(agent_id, 0)
                
                # FIX P1: Load last policy from learning store
                try:
                    from core.learning.store import learning_store
                    
                    # Initialize learning store if not initialized
                    if hasattr(learning_store, 'initialize'):
                        await_init = learning_store.initialize()
                        if asyncio.iscoroutine(await_init):
                            # If it returns a coroutine, we can't await here (sync context)
                            # Mark for async loading later
                            pass
                    
                    # Try to load latest policy (sync version if available)
                    if hasattr(learning_store, 'get_latest_policy_sync'):
                        last_policy = learning_store.get_latest_policy_sync(agent_id)
                        if last_policy:
                            logger.info(f"📚 Loaded policy {last_policy.get('policy_id', 'unknown')} for {agent_id}")
                    else:
                        logger.debug(f"Learning store not ready for {agent_id}, will load policy async later")
                except Exception as e:
                    logger.warning(f"Could not load policy for {agent_id}: {e}")
                
                logger.info(f"✅ Agent {agent_id} initialized in {agent_state.mode} mode")
            
            self._initialized = True
            logger.info(f"Agent Engine initialized with {len(self.agents)} agent(s)")
            return True, f"Initialized {len(self.agents)} agent(s)"
            
        except Exception as e:
            logger.error(f"Failed to initialize Agent Engine: {e}")
            return False, str(e)
    
    def list_agents(self) -> Dict[str, Any]:
        """List all agents and their current state"""
        with self._lock:
            return {
                agent_id: state.to_dict() 
                for agent_id, state in self.agents.items()
            }
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get state of a specific agent"""
        with self._lock:
            state = self.agents.get(agent_id)
            return state.to_dict() if state else None
    
    def start_agent(self, agent_id: str) -> tuple[bool, str]:
        """Start an agent's shadow loop"""
        with self._lock:
            if agent_id not in self.agents:
                return False, f"Agent {agent_id} not found"
            
            state = self.agents[agent_id]
            
            if state.status == 'running':
                return False, f"Agent {agent_id} is already running"
            
            # Start the agent's tick loop
            state._stop_flag.clear()
            state._thread = threading.Thread(
                target=self._agent_tick_loop,
                args=(agent_id,),
                daemon=True
            )
            state._thread.start()
            
            state.status = 'running'
            state.started_at = time.time()
            
            # Update metrics
            update_agent_running(agent_id, True)
            
            # Publish event
            event_publisher.publish({
                'type': 'agent_started',
                'agent_id': agent_id,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"▶️ Agent {agent_id} started")
            return True, f"Agent {agent_id} started"
    
    def stop_agent(self, agent_id: str) -> tuple[bool, str]:
        """Stop an agent's shadow loop"""
        with self._lock:
            if agent_id not in self.agents:
                return False, f"Agent {agent_id} not found"
            
            state = self.agents[agent_id]
            
            if state.status == 'stopped':
                return False, f"Agent {agent_id} is already stopped"
            
            # Signal thread to stop
            state._stop_flag.set()
            
            state.status = 'stopped'
            state.stopped_at = time.time()
            
            # Update metrics
            update_agent_running(agent_id, False)
            
            # Publish event
            event_publisher.publish({
                'type': 'agent_stopped',
                'agent_id': agent_id,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"⏸️ Agent {agent_id} stopped")
            return True, f"Agent {agent_id} stopped"
    
    def set_mode(self, agent_id: str, mode: str) -> tuple[bool, str]:
        """Set agent execution mode (shadow/paper/live)"""
        if mode not in ['shadow', 'paper', 'live']:
            return False, f"Invalid mode: {mode}. Must be shadow, paper, or live"
        
        with self._lock:
            if agent_id not in self.agents:
                return False, f"Agent {agent_id} not found"
            
            state = self.agents[agent_id]
            old_mode = state.mode
            state.mode = mode
            
            # Update metrics
            update_agent_mode(agent_id, mode)
            
            # Publish event
            event_publisher.publish({
                'type': 'agent_mode_changed',
                'agent_id': agent_id,
                'old_mode': old_mode,
                'new_mode': mode,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"🔄 Agent {agent_id} mode changed: {old_mode} → {mode}")
            return True, f"Agent {agent_id} mode set to {mode}"
    
    def _agent_tick_loop(self, agent_id: str):
        """Real decision loop for an agent (Phase 2)"""
        state = self.agents[agent_id]
        config = state.config
        
        logger.info(f"Tick loop started for agent {agent_id} (mode: {state.mode})")
        
        # Debounce tracking: symbol -> last_decision_time
        last_decision_times: Dict[str, float] = {}
        
        while not state._stop_flag.is_set():
            try:
                # Update tick timestamp
                current_time = time.time()
                state.last_tick = current_time
                state.tick_count += 1
                
                # Update heartbeat metric
                update_agent_heartbeat(agent_id, current_time)
                
                # Phase 2: Real decision logic
                if state.status == 'running' and config.enabled:
                    self._make_decision(
                        agent_id,
                        state,
                        config,
                        current_time,
                        last_decision_times
                    )
                
                # Heartbeat log every 10 ticks
                if state.tick_count % 10 == 0:
                    logger.debug(
                        f"Agent {agent_id} heartbeat: tick #{state.tick_count}, "
                        f"mode={state.mode}, enabled={config.enabled}"
                    )
                
                # Sleep for tick interval (5 seconds)
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in tick loop for agent {agent_id}: {e}")
                time.sleep(5)
        
        logger.info(f"Tick loop stopped for agent {agent_id}")
    
    def run_consensus_round(
        self,
        symbol: str,
        participating_agents: List[str],
        timeframe: str = '5m'
    ) -> Dict[str, Any]:
        """
        Run a consensus round for a symbol with participating agents - Phase 4 (Real LLMs)
        
        Args:
            symbol: Trading symbol
            participating_agents: List of agent IDs to participate
            timeframe: Timeframe for analysis
        
        Returns:
            Consensus result dictionary
        """
        import uuid
        from .policy import build_proposal_prompt, build_challenge_prompt, evaluate_consensus
        from .events import save_consensus_round, event_publisher
        from .risk import evaluate_dynamic_risk, get_market_context_from_prometheus
        from .metrics import (
            increment_consensus_round, increment_consensus_approved,
            update_consensus_confidence, increment_dialog_message,
            update_rationale_length, observe_consensus_confidence,
            increment_risk_dynamic_blocked, update_adjusted_notional
        )
        
        consensus_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        logger.info(f"Starting consensus round {consensus_id} for {symbol}")
        
        # Increment consensus round metric
        increment_consensus_round(symbol)
        
        # Get market context
        market_ctx = get_market_context_from_prometheus(symbol)
        market_ctx['timeframe'] = timeframe
        
        # Publish consensus started event
        event_publisher.publish({
            'type': 'consensus_started',
            'consensus_id': consensus_id,
            'symbol': symbol,
            'timeframe': timeframe,
            'agents': participating_agents,
            'timestamp': started_at.isoformat()
        })
        
        # Phase 1: PROPOSE - Each agent makes a proposal using real LLM
        proposals = []
        for agent_id in participating_agents:
            if agent_id not in self.agents:
                continue
            
            agent_state = self.agents[agent_id]
            config = agent_state.config
            
            # Call real LLM for proposal
            success, proposal_data = self._call_agent_proposal(
                agent_id, config, symbol, market_ctx, consensus_id
            )
            
            if success and proposal_data:
                proposals.append(proposal_data)
                # Increment dialog message metric
                increment_dialog_message(agent_id, 'propose')
                
                logger.info(
                    f"Agent {agent_id} proposes: {proposal_data.get('action', 'unknown')} "
                    f"with confidence {proposal_data.get('confidence', 0):.2f}"
                )
            else:
                logger.warning(f"Agent {agent_id} failed to make proposal")
        
        if not proposals:
            logger.error(f"No proposals received for consensus {consensus_id}")
            return {
                'consensus_id': consensus_id,
                'symbol': symbol,
                'approved': False,
                'action': 'hold',
                'confidence_avg': 0.0,
                'reason': 'No proposals received from agents',
                'proposals': []
            }
        
        # Publish proposals event
        event_publisher.publish({
            'type': 'consensus_proposals',
            'consensus_id': consensus_id,
            'symbol': symbol,
            'proposals': proposals,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Phase 2: CHALLENGE - Agents review each other's proposals using real LLM
        challenges = []
        for proposal in proposals:
            for agent_id in participating_agents:
                if agent_id != proposal['agent_id'] and agent_id in self.agents:
                    # Call real LLM for challenge
                    success, challenge_data = self._call_agent_challenge(
                        agent_id, self.agents[agent_id].config,
                        proposal, market_ctx, consensus_id
                    )
                    
                    if success and challenge_data:
                        challenge_data['from_agent'] = agent_id
                        challenge_data['to_agent'] = proposal['agent_id']
                        challenges.append(challenge_data)
                        # Increment dialog message metric
                        increment_dialog_message(agent_id, 'challenge')
        
        # Publish challenges event
        event_publisher.publish({
            'type': 'consensus_challenges',
            'consensus_id': consensus_id,
            'symbol': symbol,
            'challenges': challenges,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Phase 3: DECIDE - Evaluate consensus
        consensus_result = evaluate_consensus(proposals, challenges, confidence_threshold=0.6)
        
        approved = consensus_result['approved']
        action = consensus_result['action']
        confidence_avg = consensus_result['confidence_avg']
        reason = consensus_result['reason']
        notional_usdt = consensus_result.get('notional_usdt', 300)
        tp_pct = consensus_result.get('tp_pct', 0.7)
        sl_pct = consensus_result.get('sl_pct', 0.4)
        
        # Observe confidence in histogram
        observe_consensus_confidence(symbol, confidence_avg)
        
        # Calculate average rationale length
        rationales = [p.get('rationale', '') for p in proposals]
        if rationales:
            avg_length = sum(len(r) for r in rationales) / len(rationales)
            update_rationale_length(symbol, int(avg_length))
        
        # Phase 4: DYNAMIC RISK EVALUATION - Before final approval
        if approved:
            risk_approved, adjusted_params, risk_reason = evaluate_dynamic_risk(
                {
                    'symbol': symbol,
                    'action': action,
                    'confidence_avg': confidence_avg,
                    'notional_usdt': notional_usdt,
                    'tp_pct': tp_pct,
                    'sl_pct': sl_pct
                },
                market_ctx,
                agent_metrics=None  # Could fetch from slot_manager if needed
            )
            
            if not risk_approved:
                # Risk blocked the consensus
                approved = False
                reason = f"Risk blocked: {risk_reason}"
                
                # Increment risk blocked metrics
                for agent_id in participating_agents:
                    if agent_id in self.agents:
                        increment_risk_dynamic_blocked(agent_id, 'consensus_blocked')
                
                logger.warning(f"Consensus {consensus_id} blocked by risk: {risk_reason}")
                
                # Publish risk blocked event
                event_publisher.publish({
                    'type': 'risk_blocked',
                    'consensus_id': consensus_id,
                    'symbol': symbol,
                    'reason': risk_reason,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            else:
                # Apply risk adjustments
                notional_usdt = adjusted_params.get('notional_usdt', notional_usdt)
                tp_pct = adjusted_params.get('tp_pct', tp_pct)
                sl_pct = adjusted_params.get('sl_pct', sl_pct)
                
                # Update adjusted notional metrics
                for agent_id in participating_agents:
                    if agent_id in self.agents:
                        update_adjusted_notional(agent_id, symbol, notional_usdt)
                
                if adjusted_params.get('adjustments'):
                    reason += f" | Risk adjustments: {'; '.join(adjusted_params['adjustments'])}"
                    logger.info(f"Consensus {consensus_id} risk adjustments: {adjusted_params['adjustments']}")
        
        # Update metrics
        if approved:
            increment_consensus_approved(symbol, action)
        update_consensus_confidence(symbol, confidence_avg)
        
        decided_at = datetime.now(timezone.utc)
        
        # Publish decision event
        event_publisher.publish({
            'type': 'consensus_decision',
            'consensus_id': consensus_id,
            'symbol': symbol,
            'approved': approved,
            'action': action,
            'confidence_avg': confidence_avg,
            'notional_usdt': notional_usdt,
            'tp_pct': tp_pct,
            'sl_pct': sl_pct,
            'reason': reason,
            'timestamp': decided_at.isoformat()
        })
        
        # Save to MongoDB - agent_consensus collection
        consensus_data = {
            'consensus_id': consensus_id,
            'symbols': [symbol],
            'participants': participating_agents,
            'approved': approved,
            'confidence_avg': confidence_avg,
            'action': action,
            'notional_usdt': notional_usdt,
            'tp_pct': tp_pct,
            'sl_pct': sl_pct,
            'rationale': reason,
            'started_at': started_at.isoformat(),
            'decided_at': decided_at.isoformat(),
            'proposals': proposals,
            'challenges': challenges
        }
        save_consensus_round(consensus_data)
        
        logger.info(
            f"Consensus {consensus_id} for {symbol}: "
            f"{'APPROVED' if approved else 'REJECTED'} - {action} "
            f"(conf: {confidence_avg:.2f}, notional: ${notional_usdt:.0f})"
        )
        
        # Phase 5: EXECUTE IN LIVE MODE - Integration with TradingEngine
        if approved and self._check_if_live_mode(participating_agents):
            logger.info(f"Consensus {consensus_id} approved in LIVE mode - executing trade...")
            self._execute_live_trade(
                consensus_id=consensus_id,
                symbol=symbol,
                action=action,
                notional_usdt=notional_usdt,
                tp_pct=tp_pct,
                sl_pct=sl_pct,
                agent_ids=participating_agents
            )
        
        return {
            'consensus_id': consensus_id,
            'symbol': symbol,
            'approved': approved,
            'action': action,
            'confidence_avg': confidence_avg,
            'notional_usdt': notional_usdt,
            'tp_pct': tp_pct,
            'sl_pct': sl_pct,
            'reason': reason,
            'proposals': proposals,
            'challenges': challenges
        }
    
    def _make_decision(
        self,
        agent_id: str,
        state: 'AgentState',
        config: AgentConfig,
        current_time: float,
        last_decision_times: Dict[str, float]
    ):
        """
        Make a trading decision
        
        Args:
            agent_id: Agent identifier
            state: Agent state
            config: Agent configuration
            current_time: Current timestamp
            last_decision_times: Dict tracking last decision time per symbol
        """
        from .metrics import (
            increment_agent_decision, observe_decision_latency,
            increment_risk_blocked, update_positions_open,
            update_realized_pnl, update_drawdown
        )
        from .events import event_publisher
        from core.slots.router import slot_router
        from core.slots.models import TradeDecision, TradeAction, SlotMode
        from core.slots.manager import slot_manager
        from core.market.regime_detector import regime_detector
        from core.market.whale_monitor import whale_monitor
        import random
        
        start_time = time.time()
        
        try:
            # Select symbol from config
            if not config.symbols:
                return
            
            symbol = random.choice(config.symbols)
            
            # Check debounce: don't decide on same symbol within debounce_sec
            last_decision_key = f"{agent_id}_{symbol}"
            last_decision_time = last_decision_times.get(last_decision_key, 0)
            
            if current_time - last_decision_time < config.debounce_sec:
                logger.debug(
                    f"Agent {agent_id} skipping {symbol} "
                    f"(debounce: {config.debounce_sec}s)"
                )
                return
            
            # NEW: Detect market regime
            try:
                from core.data.ohlcv_loader import get_recent_ohlcv
                df = get_recent_ohlcv(symbol, timeframe='5m', limit=100)
                
                if df is not None and len(df) > 50:
                    regime, regime_confidence = regime_detector.detect_regime(df)
                    
                    # Check whale activity
                    whale_zones = whale_monitor.get_whale_zones(symbol)
                    
                    logger.debug(
                        f"Market context for {symbol}: regime={regime.value} "
                        f"(conf: {regime_confidence:.2%}), whale_zones={len(whale_zones)}"
                    )
                    
                    # Adjust strategy based on regime
                    if regime.value == 'volatile' and regime_confidence > 0.8:
                        logger.warning(f"High volatility detected for {symbol}, reducing exposure")
                        # Skip decision in extreme volatility
                        increment_risk_blocked(agent_id, "high_volatility")
                        return
                    
            except Exception as e:
                logger.error(f"Error in regime detection: {e}")
            
            # Get active slot (simplified for Phase 2)
            active_slots = slot_manager.get_active_slots()
            if not active_slots:
                logger.warning(f"No active slots available for {agent_id}")
                return
            
            slot_id = random.choice(active_slots)
            
            # Simulate decision making (Phase 2: simplified, no LLM call yet)
            # In Phase 3, this would call the LLM for actual analysis
            action, confidence, reason = self._simulate_decision(
                agent_id, symbol, config
            )
            
            # Check confidence threshold
            if confidence < config.confidence_min:
                logger.debug(
                    f"Agent {agent_id} confidence too low: "
                    f"{confidence:.2f} < {config.confidence_min}"
                )
                increment_risk_blocked(agent_id, "low_confidence")
                return
            
            # Check if dialog needed (Phase 2: basic logic)
            if self._should_trigger_dialog(config, confidence, reason):
                self._trigger_dialog(agent_id, symbol, action, confidence, config)
            
            # Create decision
            decision = TradeDecision(
                agent_id=agent_id,
                slot_id=slot_id,
                symbol=symbol,
                action=action,
                confidence=confidence,
                mode=SlotMode(state.mode),
                reason=reason,
                size=0.01  # Default size for Phase 2
            )
            
            # Execute decision through slot router
            success, message, details = slot_router.execute_decision(decision)
            
            # Record execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            increment_agent_decision(
                agent_id,
                action.value,
                symbol,
                state.mode
            )
            observe_decision_latency(agent_id, execution_time_ms)
            
            # Update position and PnL metrics
            metrics = slot_manager.get_metrics(slot_id)
            if metrics:
                update_positions_open(agent_id, metrics.positions_open)
                update_realized_pnl(agent_id, metrics.realized_pnl)
                update_drawdown(agent_id, metrics.drawdown_pct)
            
            # Save decision to MongoDB
            decision_data = decision.to_dict()
            decision_data.update({
                "success": success,
                "message": message,
                "details": details
            })
            event_publisher.save_decision(decision_data)
            
            # Update debounce tracking
            last_decision_times[last_decision_key] = current_time
            
            logger.info(
                f"Agent {agent_id} decision: {action.value} {symbol} "
                f"(confidence: {confidence:.2f}, mode: {state.mode}) - {message}"
            )
            
        except Exception as e:
            logger.error(f"Error making decision for {agent_id}: {e}")
    
    def _call_agent_proposal(
        self,
        agent_id: str,
        config: AgentConfig,
        symbol: str,
        market_ctx: Dict[str, Any],
        consensus_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Call agent LLM for proposal - Phase 4
        
        Args:
            agent_id: Agent identifier
            config: Agent configuration
            symbol: Trading symbol
            market_ctx: Market context
            consensus_id: Consensus round ID
        
        Returns:
            Tuple of (success, proposal_data)
        """
        from .policy import build_proposal_prompt
        from .events import event_publisher
        
        try:
            # Build agent config dict for policy
            agent_cfg = {
                'agent_id': agent_id,
                'role': config.role,
                'risk': {
                    'max_position_notional_usdt': config.risk.get('max_position_notional_usdt', 1000) if hasattr(config, 'risk') else 1000,
                    'max_daily_drawdown_pct': config.risk.get('max_daily_drawdown_pct', 2.0) if hasattr(config, 'risk') else 2.0
                }
            }
            
            # Build prompt
            prompt = build_proposal_prompt(agent_cfg, market_ctx)
            
            # Call LLM
            success, response_text, error = llm_client_manager.call_llm(
                provider=config.provider,
                model=config.model,
                prompt=prompt,
                max_tokens=500,
                temperature=0.7
            )
            
            if not success:
                logger.error(f"LLM call failed for {agent_id}: {error}")
                return False, None
            
            # Parse response
            parsed = llm_client_manager.parse_llm_response(response_text)
            if not parsed:
                logger.error(f"Failed to parse LLM response for {agent_id}")
                return False, None
            
            # Build proposal data
            proposal_data = {
                'agent_id': agent_id,
                'action': parsed.get('action', 'hold'),
                'confidence': parsed.get('confidence', 0.5),
                'rationale': parsed.get('rationale', 'No rationale provided'),
                'suggested_notional_usdt': parsed.get('suggested_notional_usdt', 300),
                'tp_pct': parsed.get('tp_pct', 0.7),
                'sl_pct': parsed.get('sl_pct', 0.4),
                'phase': 'propose'
            }
            
            # Save to agent_dialogs collection
            dialog_doc = {
                'consensus_id': consensus_id,
                'phase': 'propose',
                'agent_id': agent_id,
                'symbol': symbol,
                'timeframe': market_ctx.get('timeframe', '5m'),
                'content': response_text,
                'confidence': proposal_data['confidence'],
                'rationale': proposal_data['rationale'],
                'ts': datetime.now(timezone.utc).isoformat()
            }
            event_publisher.save_agent_dialog(dialog_doc)
            
            # Publish proposal text event for SSE
            event_publisher.publish({
                'type': 'consensus_proposal_text',
                'consensus_id': consensus_id,
                'agent_id': agent_id,
                'symbol': symbol,
                'action': proposal_data['action'],
                'confidence': proposal_data['confidence'],
                'rationale': proposal_data['rationale'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            return True, proposal_data
            
        except Exception as e:
            logger.error(f"Error in _call_agent_proposal for {agent_id}: {e}")
            return False, None
    
    def _call_agent_challenge(
        self,
        agent_id: str,
        config: AgentConfig,
        proposal: Dict[str, Any],
        market_ctx: Dict[str, Any],
        consensus_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Call agent LLM for challenge - Phase 4
        
        Args:
            agent_id: Challenging agent identifier
            config: Agent configuration
            proposal: Proposal to challenge
            market_ctx: Market context
            consensus_id: Consensus round ID
        
        Returns:
            Tuple of (success, challenge_data)
        """
        from .policy import build_challenge_prompt
        from .events import event_publisher
        
        try:
            # Build agent config dict for policy
            agent_cfg = {
                'agent_id': agent_id,
                'role': config.role
            }
            
            # Build prompt
            prompt = build_challenge_prompt(agent_cfg, proposal, market_ctx)
            
            # Call LLM
            success, response_text, error = llm_client_manager.call_llm(
                provider=config.provider,
                model=config.model,
                prompt=prompt,
                max_tokens=400,
                temperature=0.6
            )
            
            if not success:
                logger.error(f"LLM call failed for {agent_id} challenge: {error}")
                return False, None
            
            # Parse response
            parsed = llm_client_manager.parse_llm_response(response_text)
            if not parsed:
                logger.error(f"Failed to parse LLM challenge response for {agent_id}")
                return False, None
            
            # Build challenge data
            challenge_data = {
                'agree': parsed.get('agree', True),
                'comment': parsed.get('comment', 'No comment'),
                'confidence_adjustment': parsed.get('confidence_adjustment', 0.0),
                'suggested_changes': parsed.get('suggested_changes', {}),
                'phase': 'challenge'
            }
            
            # Save to agent_dialogs collection
            dialog_doc = {
                'consensus_id': consensus_id,
                'phase': 'challenge',
                'agent_id': agent_id,
                'symbol': market_ctx.get('symbol'),
                'timeframe': market_ctx.get('timeframe', '5m'),
                'content': response_text,
                'confidence': None,
                'rationale': challenge_data['comment'],
                'ts': datetime.now(timezone.utc).isoformat()
            }
            event_publisher.save_agent_dialog(dialog_doc)
            
            # Publish challenge text event for SSE
            event_publisher.publish({
                'type': 'consensus_challenge_text',
                'consensus_id': consensus_id,
                'agent_id': agent_id,
                'symbol': market_ctx.get('symbol'),
                'agree': challenge_data['agree'],
                'comment': challenge_data['comment'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            return True, challenge_data
            
        except Exception as e:
            logger.error(f"Error in _call_agent_challenge for {agent_id}: {e}")
            return False, None
    
    def _simulate_decision(
        self,
        agent_id: str,
        symbol: str,
        config: AgentConfig
    ) -> tuple:
        """
        Simulate a trading decision (Phase 2 placeholder - kept for compatibility)
        
        In Phase 4, real LLM calls are used in run_consensus_round.
        
        Returns:
            Tuple of (action, confidence, reason)
        """
        import random
        from core.slots.models import TradeAction
        
        # Simulate decision based on agent role
        role_lower = config.role.lower()
        
        if 'scalp' in role_lower:
            # Scalper: more frequent, small positions
            actions = [TradeAction.OPEN_LONG, TradeAction.OPEN_SHORT, TradeAction.HOLD]
            weights = [0.3, 0.3, 0.4]
            action = random.choices(actions, weights=weights)[0]
            confidence = random.uniform(0.65, 0.90)
            reason = "Scalping opportunity detected"
            
        elif 'trend' in role_lower:
            # Trend follower: less frequent, hold longer
            actions = [TradeAction.OPEN_LONG, TradeAction.HOLD, TradeAction.CLOSE_LONG]
            weights = [0.2, 0.6, 0.2]
            action = random.choices(actions, weights=weights)[0]
            confidence = random.uniform(0.70, 0.95)
            reason = "Trend following signal"
            
        else:
            # Default: balanced
            actions = [TradeAction.OPEN_LONG, TradeAction.HOLD]
            weights = [0.3, 0.7]
            action = random.choices(actions, weights=weights)[0]
            confidence = random.uniform(0.60, 0.85)
            reason = "General market analysis"
        
        return action, confidence, reason
    
    def _should_trigger_dialog(
        self,
        config: AgentConfig,
        confidence: float,
        reason: str
    ) -> bool:
        """
        Determine if a dialog should be triggered
        
        Args:
            config: Agent configuration
            confidence: Decision confidence
            reason: Decision reason
        
        Returns:
            True if dialog should be triggered
        """
        # Dialog triggers:
        # 1. Low confidence
        if confidence < 0.7:
            return True
        
        # 2. High risk keyword in reason
        high_risk_keywords = ['high risk', 'volatile', 'uncertain']
        if any(keyword in reason.lower() for keyword in high_risk_keywords):
            return True
        
        # 3. Random dialog (10% chance) for testing
        import random
        if random.random() < 0.1:
            return True
        
        return False
    
    def _trigger_dialog(
        self,
        agent_id: str,
        symbol: str,
        action,
        confidence: float,
        config: AgentConfig
    ):
        """
        Trigger a dialog between agents
        
        Args:
            agent_id: Agent identifier
            symbol: Trading symbol
            action: Proposed action
            confidence: Decision confidence
            config: Agent configuration
        """
        from .events import create_dialog, save_dialog, AgentMessage, event_publisher
        from .metrics import increment_dialog
        
        try:
            # Get agents this agent talks with
            partners = config.talks_with
            if not partners:
                return
            
            # Create dialog
            participants = [agent_id] + partners
            topic = f"Decision on {symbol}: {action.value}"
            dialog = create_dialog(topic, participants)
            
            # Add proposal message
            proposal = AgentMessage(
                from_agent=agent_id,
                to_agent=partners[0] if partners else "system",
                topic=topic,
                message=f"Proposing {action.value} on {symbol} with confidence {confidence:.2f}",
                metadata={
                    "symbol": symbol,
                    "action": action.value,
                    "confidence": confidence
                }
            )
            dialog.add_message(proposal)
            event_publisher.send_message(proposal)
            
            # Simulate response (Phase 2: simplified)
            if partners:
                response = AgentMessage(
                    from_agent=partners[0],
                    to_agent=agent_id,
                    topic=topic,
                    message=f"{'Approved' if confidence > 0.75 else 'Challenged'}: {action.value} on {symbol}",
                    metadata={"approval": confidence > 0.75}
                )
                dialog.add_message(response)
                event_publisher.send_message(response)
                
                # Increment dialog metrics
                increment_dialog(agent_id, partners[0])
            
            # Close dialog
            dialog.close(outcome="approved" if confidence > 0.75 else "challenged")
            
            # Save to MongoDB
            save_dialog(dialog)
            
            logger.info(f"Dialog triggered: {agent_id} ↔ {partners} on {symbol}")
            
        except Exception as e:
            logger.error(f"Error triggering dialog: {e}")
    
    def _check_if_live_mode(self, agent_ids: List[str]) -> bool:
        """
        Check if any participating agent is in LIVE mode
        
        Args:
            agent_ids: List of agent IDs
        
        Returns:
            True if any agent is in LIVE mode
        """
        with self._lock:
            for agent_id in agent_ids:
                if agent_id in self.agents:
                    if self.agents[agent_id].mode == 'live':
                        return True
            return False
    
    def _execute_live_trade(
        self,
        consensus_id: str,
        symbol: str,
        action: str,
        notional_usdt: float,
        tp_pct: float,
        sl_pct: float,
        agent_ids: List[str]
    ):
        """
        Execute a live trade through TradingEngine/PositionManager
        
        Args:
            consensus_id: Consensus round ID
            symbol: Trading symbol
            action: Trade action ('open_long', 'open_short', etc.)
            notional_usdt: Position size in USDT
            tp_pct: Take profit percentage
            sl_pct: Stop loss percentage
            agent_ids: Participating agent IDs
        """
        try:
            # Import here to avoid circular dependency
            from core.positions.position_manager import position_manager
            from core.exchanges.exchange_manager import get_exchange_manager
            
            # Check if position manager is initialized
            if position_manager is None:
                logger.error("Position manager not initialized - cannot execute live trade")
                
                # Try to initialize
                logger.info("Attempting to initialize position manager...")
                from core.execution.order_executor import OrderExecutor
                from core.positions.position_manager import PositionManager
                
                try:
                    exchange_mgr = get_exchange_manager()
                    if not exchange_mgr:
                        logger.error("Exchange manager not available")
                        return
                    
                    order_executor = OrderExecutor(exchange_mgr)
                    pm = PositionManager(order_executor=order_executor)
                    
                    # Store globally
                    import core.positions.position_manager as pm_module
                    pm_module.position_manager = pm
                    
                    logger.info("Position manager initialized successfully")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize position manager: {e}")
                    return
            
            # Get position manager instance
            from core.positions.position_manager import position_manager as pm
            
            if pm is None:
                logger.error("Position manager still not available")
                return
            
            # Determine exchange
            exchange_name = os.getenv('EXCHANGE', 'binance')
            
            logger.info(
                f"Executing LIVE trade: {action} {symbol} "
                f"(${notional_usdt:.0f}, TP={tp_pct:.1f}%, SL={sl_pct:.1f}%)"
            )
            
            # Execute the trade
            if action in ['open_long', 'open_short']:
                success, message, trade = pm.open_live_trade(
                    consensus_id=consensus_id,
                    agent_ids=agent_ids,
                    action=action,
                    symbol=symbol,
                    notional_usdt=notional_usdt,
                    tp_pct=tp_pct,
                    sl_pct=sl_pct,
                    exchange=exchange_name
                )
                
                if success:
                    logger.info(f"✅ LIVE trade executed successfully: {message}")
                    
                    # Publish event
                    event_publisher.publish({
                        'type': 'live_trade_opened',
                        'consensus_id': consensus_id,
                        'symbol': symbol,
                        'action': action,
                        'trade_id': trade.trade_id if trade else None,
                        'notional_usdt': notional_usdt,
                        'entry_price': trade.entry_price if trade else None,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                else:
                    logger.error(f"❌ Failed to execute LIVE trade: {message}")
                    
                    # Publish error event
                    event_publisher.publish({
                        'type': 'live_trade_failed',
                        'consensus_id': consensus_id,
                        'symbol': symbol,
                        'action': action,
                        'error': message,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            elif action in ['close_long', 'close_short']:
                # Find open trade for this symbol
                open_trades = pm.get_open_trades()
                
                for trade in open_trades:
                    if trade['symbol'] == symbol:
                        trade_id = trade['trade_id']
                        
                        success, message, result = pm.close_live_trade(
                            trade_id=trade_id,
                            reason="consensus_decision"
                        )
                        
                        if success:
                            logger.info(f"✅ LIVE trade closed successfully: {message}")
                            
                            # Publish event
                            event_publisher.publish({
                                'type': 'live_trade_closed',
                                'consensus_id': consensus_id,
                                'symbol': symbol,
                                'action': action,
                                'trade_id': trade_id,
                                'realized_pnl': result.get('realized_pnl', 0) if result else 0,
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            })
                        else:
                            logger.error(f"❌ Failed to close LIVE trade: {message}")
                        
                        break
            
            else:
                logger.warning(f"Action {action} not supported for live execution")
            
        except Exception as e:
            logger.error(f"Error executing live trade: {e}")
            import traceback
            traceback.print_exc()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        with self._lock:
            running_count = sum(1 for s in self.agents.values() if s.status == 'running')
            mode_counts = {}
            for mode in ['shadow', 'paper', 'live']:
                mode_counts[mode] = sum(
                    1 for s in self.agents.values() if s.mode == mode
                )
            
            return {
                'initialized': self._initialized,
                'total_agents': len(self.agents),
                'running_agents': running_count,
                'stopped_agents': len(self.agents) - running_count,
                'modes': mode_counts
            }


# Global instance
agent_engine = AgentEngine()
