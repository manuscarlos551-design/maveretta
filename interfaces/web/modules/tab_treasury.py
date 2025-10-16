"""Aba: Tesouraria."""
import streamlit as st
from helpers.grafana_helper import grafana_panel

def render():
    """Renderiza a aba Tesouraria."""
    st.markdown('<div class="section-header">🏦 Tesouraria</div>', unsafe_allow_html=True)

    # Capital Total (USDT)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=3, height=260)

    # Carteira Real (USDT)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=13, height=400)

    # Carteira Real (BRL)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=14, height=400)

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Exchange Balances
    st.subheader("🏛️ Saldo por Exchange")

    col1, col2 = st.columns(2)
    
    with col1:
        # Bybit Equity
        grafana_panel(uid="maveretta-bybit-live", slug="maveretta-bybit-live", panel_id=1, height=260)
        
        # KuCoin Equity
        grafana_panel(uid="maveretta-kucoin-live", slug="maveretta-kucoin-live", panel_id=1, height=260)
        
        # OKX Equity
        grafana_panel(uid="maveretta-okx-live", slug="maveretta-okx-live", panel_id=1, height=260)
    
    with col2:
        # Coinbase Equity
        grafana_panel(uid="maveretta-coinbase-live", slug="maveretta-coinbase-live", panel_id=1, height=260)
        
        # KuCoin Equity Over Time
        grafana_panel(uid="maveretta-kucoin-live", slug="maveretta-kucoin-live", panel_id=3, height=260)
        
        st.markdown('<div style="height: 260px;"></div>', unsafe_allow_html=True)  # Placeholder
