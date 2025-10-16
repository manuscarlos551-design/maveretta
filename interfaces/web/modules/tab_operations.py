"""Aba: Operações."""
import streamlit as st
from helpers.grafana_helper import grafana_panel

def render():
    """Renderiza a aba Operações."""
    st.markdown('<div class="section-header">📈 Operações</div>', unsafe_allow_html=True)

    # Paper Trades Unrealized PnL
    grafana_panel(uid="agents-overview-phase3", slug="agents-overview-phase-3", panel_id=5, height=400)

    # CPU Usage
    grafana_panel(uid="maveretta-infrastructure", slug="maveretta-infrastructure-system", panel_id=1, height=400)

    # Memory Usage
    grafana_panel(uid="maveretta-infrastructure", slug="maveretta-infrastructure-system", panel_id=2, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Disk Usage
    grafana_panel(uid="maveretta-infrastructure", slug="maveretta-infrastructure-system", panel_id=3, height=400)

    # Container CPU Usage
    grafana_panel(uid="maveretta-infrastructure", slug="maveretta-infrastructure-system", panel_id=5, height=400)

    # Container Memory Usage
    grafana_panel(uid="maveretta-infrastructure", slug="maveretta-infrastructure-system", panel_id=6, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Latência Média
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=18, height=400)

    # Exchange Latency
    grafana_panel(uid="orchestration-venue-health", slug="orchestration-venue-health", panel_id=1, height=400)

    # Clock Skew
    grafana_panel(uid="orchestration-venue-health", slug="orchestration-venue-health", panel_id=2, height=400)
