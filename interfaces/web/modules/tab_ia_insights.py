"""Aba: IA Insights."""
import streamlit as st
from helpers.grafana_helper import grafana_panel

def render():
    """Renderiza a aba IA Insights."""
    st.markdown('<div class="section-header">🧠 IA Insights</div>', unsafe_allow_html=True)

    # Confidence Heatmap
    grafana_panel(uid="agent-drilldown-phase3", slug="agent-drilldown-phase-3", panel_id=2, height=500)

    # Agent Status (Running=1, Stopped=0)
    grafana_panel(uid="agents-overview-phase3", slug="agents-overview-phase-3", panel_id=1, height=260)

    # Decisions per Hour (by Agent)
    grafana_panel(uid="agents-overview-phase3", slug="agents-overview-phase-3", panel_id=2, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Consensus Confidence Average
    grafana_panel(uid="agents-overview-phase3", slug="agents-overview-phase-3", panel_id=4, height=400)

    # Agent Drawdown %
    grafana_panel(uid="agents-overview-phase3", slug="agents-overview-phase-3", panel_id=7, height=400)

    # Average Confidence
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=4, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Consensus Phase Timeline
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=5, height=400)

    # Confidence Heatmap by Agent
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=6, height=500)

    # Decision Confidence by Strategy
    grafana_panel(uid="orchestration-decision-conf", slug="orchestration-decision-conf", panel_id=1, height=260)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Decision Confidence by IA
    grafana_panel(uid="orchestration-decision-conf", slug="orchestration-decision-conf", panel_id=2, height=400)

    # Confidence Distribution
    grafana_panel(uid="orchestration-decision-conf", slug="orchestration-decision-conf", panel_id=3, height=400)

    # High Confidence Decisions (>80%)
    grafana_panel(uid="orchestration-decision-conf", slug="orchestration-decision-conf", panel_id=4, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Low Confidence Decisions (<50%)
    grafana_panel(uid="orchestration-decision-conf", slug="orchestration-decision-conf", panel_id=5, height=400)

    # Avg Confidence by Slot
    grafana_panel(uid="orchestration-decision-conf", slug="orchestration-decision-conf", panel_id=6, height=260)

    # IA Latency (ms)
    grafana_panel(uid="orchestration-ia-health", slug="orchestration-ia-health", panel_id=2, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # IA Uptime %
    grafana_panel(uid="orchestration-ia-health", slug="orchestration-ia-health", panel_id=3, height=400)

    # Errors by IA
    grafana_panel(uid="orchestration-ia-health", slug="orchestration-ia-health", panel_id=4, height=400)
