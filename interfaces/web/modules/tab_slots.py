"""Aba: Slots."""
import streamlit as st
from helpers.grafana_helper import grafana_panel

def render():
    """Renderiza a aba Slots."""
    st.markdown('<div class="section-header">🎰 Slots</div>', unsafe_allow_html=True)

    # Slots Ativos
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=15, height=400)

    # Slots Ativos (Slots Dashboard)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=1, height=400)

    # Histórico de Slots Ativos
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=5, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Slot States Timeline
    grafana_panel(uid="orchestration-slots-timeline", slug="orchestration-slots-timeline", panel_id=1, height=400)

    # Slot State Distribution
    grafana_panel(uid="orchestration-slots-timeline", slug="orchestration-slots-timeline", panel_id=2, height=400)

    # Active Slots Count
    grafana_panel(uid="orchestration-slots-timeline", slug="orchestration-slots-timeline", panel_id=3, height=260)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Slot State Changes
    grafana_panel(uid="orchestration-slots-timeline", slug="orchestration-slots-timeline", panel_id=4, height=400)

    # Ciclos Completados (1h)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=2, height=400)

    # Taxa de Execução (Cycles/sec)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=6, height=400)
