# interfaces/web/helpers/__init__.py
"""Helpers utilitarios"""
from .grafana import (
    grafana_panel,
    panel_from_registry,
    section_header,
    metric_row,
    load_panel_registry
)
from .api import (
    get_agents,
    get_slots,
    start_agent,
    stop_agent,
    set_agent_mode,
    get_consensus_history,
    get_trades,
    trigger_consensus
)
from .mongodb import (
    get_consensus_rounds,
    get_agent_decisions,
    get_paper_trades,
    get_live_trades
)

__all__ = [
    'grafana_panel',
    'panel_from_registry',
    'section_header',
    'metric_row',
    'load_panel_registry',
    'get_agents',
    'get_slots',
    'start_agent',
    'stop_agent',
    'set_agent_mode',
    'get_consensus_history',
    'get_trades',
    'trigger_consensus',
    'get_consensus_rounds',
    'get_agent_decisions',
    'get_paper_trades',
    'get_live_trades'
]
