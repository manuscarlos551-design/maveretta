# core/orchestrator/loader.py
"""Agent Configuration Loader - Loads agent configs from YAML files"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AgentConfig:
    """Agent configuration data class"""
    
    def __init__(self, data: Dict[str, Any]):
        self.agent_id = data.get('agent_id')
        self.provider = data.get('provider')
        self.model = data.get('model')
        self.api_key_env = data.get('api_key_env')
        self.role = data.get('role', '')
        self.exchanges = data.get('exchanges', [])
        self.symbols = data.get('symbols', [])
        self.timeframes = data.get('timeframes', [])
        self.execution_mode = data.get('execution_mode', 'shadow')
        self.risk = data.get('risk', {})
        self.talks_with = data.get('talks_with', [])
        
        # Phase 2 fields
        self.enabled = data.get('enabled', True)
        self.confidence_min = data.get('confidence_min', 0.7)
        self.debounce_sec = data.get('debounce_sec', 30)
        self.decision_timeout_sec = data.get('decision_timeout_sec', 10)
        self.dialog_on_conflict = data.get('dialog_on_conflict', True)
        
        # Risk thresholds
        risk_config = data.get('risk', {})
        self.risk_high_threshold = risk_config.get('high_threshold', 1000.0)
        self.max_daily_drawdown_pct = risk_config.get('max_daily_drawdown_pct', 5.0)
        self.max_position_notional_usdt = risk_config.get('max_position_notional_usdt', 1000.0)
        self.max_open_positions = risk_config.get('max_open_positions', 3)
        
        self._raw_data = data
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate required fields"""
        if not self.agent_id:
            return False, "Missing agent_id"
        if not self.provider:
            return False, f"Missing provider for {self.agent_id}"
        if not self.api_key_env:
            return False, f"Missing api_key_env for {self.agent_id}"
        if not os.getenv(self.api_key_env):
            return False, f"Environment variable {self.api_key_env} not set for {self.agent_id}"
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self._raw_data


def load_agents_configs(config_dir: str = None) -> Dict[str, AgentConfig]:
    """
    Load all agent configurations from YAML files
    
    Args:
        config_dir: Directory containing agent YAML files. 
                   Defaults to /app/config/agents
    
    Returns:
        Dictionary mapping agent_id to AgentConfig
    """
    if config_dir is None:
        config_dir = '/app/config/agents'
    
    config_path = Path(config_dir)
    
    if not config_path.exists():
        logger.warning(f"Agent config directory not found: {config_dir}")
        return {}
    
    agents = {}
    
    # Load all YAML files in the directory
    for yaml_file in config_path.glob('*.yaml'):
        try:
            logger.info(f"Loading agent config from {yaml_file.name}")
            
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"Empty config file: {yaml_file.name}")
                continue
            
            # Create AgentConfig object
            agent_config = AgentConfig(data)
            
            # Validate configuration
            valid, error = agent_config.validate()
            if not valid:
                logger.error(f"Invalid config in {yaml_file.name}: {error}")
                continue
            
            # Store by agent_id
            agents[agent_config.agent_id] = agent_config
            logger.info(f"✅ Loaded agent: {agent_config.agent_id} (provider: {agent_config.provider})")
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parse error in {yaml_file.name}: {e}")
        except Exception as e:
            logger.error(f"Error loading {yaml_file.name}: {e}")
    
    logger.info(f"Loaded {len(agents)} agent configuration(s)")
    return agents
