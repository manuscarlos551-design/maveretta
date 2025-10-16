# interfaces/web/treasury_tab.py
"""
Aba Treasury - Dashboard de Cascata e Roteamento de Lucros
100% embedado com painéis nativos do Grafana
LEGACY: Removido todos os st.metric, gráficos locais (Plotly), consultas API diretas
"""

import os
import urllib.parse
import streamlit as st
import logging

logger = logging.getLogger(__name__)


# ========== HELPER: EMBED GRAFANA PANEL ==========
def grafana_panel(uid: str, slug: str, panel_id: int, height: int = 300,
                  time_from: str = "now-6h", time_to: str = "now"):
    """
    Renderiza painel nativo do Grafana via iframe /d-solo
    """
    base = os.getenv("GRAFANA_BASE_URL", "http://localhost/grafana").rstrip("/")
    params = {
        "orgId": "1",
        "panelId": str(panel_id),
        "theme": "dark",
        "kiosk": "",
        "from": time_from,
        "to": time_to,
    }
    url = f"{base}/d-solo/{uid}/{urllib.parse.quote(slug)}?{urllib.parse.urlencode(params)}"
    st.components.v1.iframe(url, height=height, scrolling=False)


def render_treasury_tab():
    """🏦 Treasury - Sistema de Cascata e Roteamento de Lucros"""
    
    st.markdown('<div class="section-header">🏦 Treasury - Sistema de Cascata</div>', unsafe_allow_html=True)
    
    # ========== KPIs PRINCIPAIS (Grafana Embeds) ==========
    st.markdown("### 📊 KPIs do Sistema de Cascata")
    
    # LEGACY: st.metric removidos, substituídos por painéis Grafana
    # Painel de KPIs consolidados do dashboard treasury-cascade
    # Assumindo dashboard treasury-cascade.json com painéis de métricas
    
    # Treasury Balance (Panel ID: 1)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=1, height=260)
    
    # Slots Status Overview (Panel ID: 2)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=2, height=260)
    
    # Cascade Completion Progress (Panel ID: 3)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=3, height=260)
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== VISUALIZAÇÃO DOS SLOTS ==========
    st.markdown("### 🎰 Slots da Cascata")
    
    # Slot Performance Grid (Panel ID: 4)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=4, height=460)
    
    # Slots Timeline (Panel ID: 1 do orchestration_slots_timeline)
    grafana_panel(uid="orchestration-slots-timeline", slug="orchestration-slots-timeline", panel_id=1, height=400)
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== FLUXO DE CAPITAL ==========
    st.markdown("### 💸 Fluxo de Capital na Cascata")
    
    # LEGACY: Sankey diagram local (Plotly) substituído por painel Grafana
    # Capital Flow Timeline (Panel ID: 5)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=5, height=500)
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== MÉTRICAS CONSOLIDADAS ==========
    st.markdown("### 📈 Métricas Consolidadas")
    
    # LEGACY: st.metric removidos
    # Settlements Metrics (Panel ID: 6)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=6, height=280)
    
    # Win Rate & P/L (Panel ID: 7)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=7, height=280)
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== HISTÓRICO DE SETTLEMENTS ==========
    st.markdown("### 📜 Histórico de Settlements")
    
    # LEGACY: st.dataframe com dados da API substituído por tabela Grafana
    # Settlements History Table (Panel ID: 8)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=8, height=520)
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== AÇÕES (mantido - são botões interativos, não dados) ==========
    st.markdown("### 🛠️ Ações")
    
    st.info("ℹ️ Ações disponíveis via API Gateway - implemente endpoints de controle conforme necessário")


# LEGACY: Funções removidas (não mais necessárias com embeds Grafana)
# - fmt_money(): formatação agora é feita no Grafana
# - render_slot_card(): visualização agora é nativa do Grafana
# - create_sankey_diagram(): substituído por painel Grafana de fluxo
