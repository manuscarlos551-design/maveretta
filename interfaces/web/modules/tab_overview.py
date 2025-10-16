"""Aba: Visão Geral."""
import streamlit as st
from helpers.grafana_helper import grafana_panel

def render():
    """Renderiza a aba Visão Geral."""
    st.markdown('<div class="section-header">📊 Visão Geral</div>', unsafe_allow_html=True)

    # Consensus Approval Rate
    grafana_panel(uid="agent-drilldown-phase3", slug="agent-drilldown-phase-3", panel_id=3, height=260)

    # Risk Blocked Reasons
    grafana_panel(uid="agent-drilldown-phase3", slug="agent-drilldown-phase-3", panel_id=5, height=400)

    # Consensus Approved (by Symbol)
    grafana_panel(uid="agents-overview-phase3", slug="agents-overview-phase-3", panel_id=3, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Total Open Positions
    grafana_panel(uid="agents-overview-phase3", slug="agents-overview-phase-3", panel_id=6, height=260)

    # Consensus Rounds (1h)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=1, height=400)

    # Consensus Approved (1h)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=2, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Approval Rate (1h)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=3, height=260)

    # Risk Blocked by Reason
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=7, height=400)

    # Exchange Status
    grafana_panel(uid="orchestration-venue-health", slug="orchestration-venue-health", panel_id=3, height=260)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Services Status
    grafana_panel(uid="maveretta-infrastructure", slug="maveretta-infrastructure-system", panel_id=4, height=260)

    # Health / Uptime - All Services
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=21, height=400)
