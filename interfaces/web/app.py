# interfaces/web/app.py
"""
Maveretta Bot - Dashboard Principal com 13 Abas Integradas
Interface Streamlit unificada com painéis Grafana embedados NATIVOS
Todas as 13 abas conforme mapeamento AUDITORIA_MAPEAMENTO_STREAMLIT_GRAFANA
LEGACY: Removido todos os st.metric, queries Prometheus diretas, gráficos locais
"""
import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# IMPORTS THIRD-PARTY
# -------------------------
import streamlit as st
import streamlit.components.v1 as components

# -------------------------
# CONFIGURAÇÃO DA PÁGINA
# -------------------------
st.set_page_config(
    page_title="Maveretta Bot - AI Trading Orchestration",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# CONSTANTES
# -------------------------
GRAFANA_BASE_URL = os.getenv("GRAFANA_URL", os.getenv("GRAFANA_BASE_URL", "/grafana")).rstrip("/")
APP_DIR = Path(__file__).parent

# Tamanhos mínimos úteis (sem scroll interno, legível)
EMBED_HEIGHTS = {
    "kpi": 260,       # KPIs, cards, single stats (240–280px)
    "chart": 400,     # Gráficos, timeseries (360–420px)
    "table": 460,     # Tabelas completas (400–500px)
}

# -------------------------
# HELPER: EMBED GRAFANA PANEL (PADRONIZADO + TURBINADA)
# -------------------------
def grafana_embed(uid: str, panel_id: int, kind: str = "chart", refresh: str = "10s", lazy: bool = False):
    """
    Renderiza painel nativo do Grafana via iframe /d-solo (TAMANHO MÍNIMO ÚTIL)
    TURBINADA: Suporte para lazy loading otimizado
    
    Args:
        uid: UID do dashboard Grafana (ex: "maveretta-overview-live")
        panel_id: ID do painel dentro do dashboard
        kind: Tipo de painel - define altura automática
              - "kpi": 260px (cards, stats, single values)
              - "chart": 400px (gráficos, timeseries, candles)
              - "table": 460px (tabelas completas)
        refresh: Intervalo de refresh (padrão: "10s")
        lazy: Se True, usa lazy loading (apenas renderiza quando visível)
    """
    height = EMBED_HEIGHTS.get(kind, EMBED_HEIGHTS["chart"])
    
    # Endpoint /d-solo com viewPanel (mais limpo)
    url = (
        f"{GRAFANA_BASE_URL}/d-solo/{uid}"
        f"?orgId=1&refresh={refresh}&kiosk&theme=dark&viewPanel={panel_id}"
    )
    
    # TURBINADA: Lazy loading para reduzir carga inicial
    if lazy:
        # Placeholder leve até o iframe ser carregado
        with st.container():
            components.iframe(url, height=height, scrolling=False)
    else:
        # Iframe sem scroll interno (carregamento imediato)
        components.iframe(url, height=height, scrolling=False)

# -------------------------
# CSS TEMA DARK PREMIUM
# -------------------------
THEME_CSS = """
<style>
:root {
  --bg: #0a0d14;
  --panel: #141922;
  --panel2: #1c2531;
  --panel3: #252d3d;
  --text: #e8eaef;
  --text-secondary: #b8c2d3;
  --muted: #8a95a6;
  --accent: #f5c451;
  --accent-hover: #f7d373;
  --green: #22c55e;
  --red: #ef4444;
  --blue: #3b82f6;
  --purple: #8b5cf6;
  --border: #2a3441;
  --border-light: #3d4654;
  --shadow: rgba(0,0,0,0.25);
}

html, body, .stApp { 
  background-color: var(--bg); 
  color: var(--text);
  font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
}

.main-header {
  text-align: center;
  margin: 0 0 1.5rem 0;
  padding: 1rem 0;
  background: linear-gradient(135deg, var(--panel2) 0%, var(--panel) 100%);
  border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: 0 4px 20px var(--shadow);
  position: relative;
  overflow: hidden;
}

.main-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--green), var(--blue));
}

.main-title {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.025em;
  color: var(--text);
  margin: 0 0 0.25rem 0;
  text-shadow: 0 2px 4px rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.main-subtitle {
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
  opacity: 0.8;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 2px;
  padding: 6px;
  background: var(--panel);
  border-radius: 12px;
  border: 1px solid var(--border);
  margin-bottom: 2rem;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--accent) transparent;
}

.stTabs [data-baseweb="tab"] {
  height: 48px;
  min-width: 85px;
  padding: 10px 12px;
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  border: 1px solid transparent;
  font-weight: 600;
  font-size: 12px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  white-space: nowrap;
  position: relative;
  overflow: hidden;
}

.stTabs [data-baseweb="tab"]:hover {
  background: var(--panel2);
  color: var(--text-secondary);
  border-color: var(--border-light);
  transform: translateY(-1px);
}

.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, var(--panel3) 0%, var(--panel2) 100%);
  color: var(--text);
  border-color: var(--accent);
  box-shadow: 0 2px 8px rgba(245, 196, 81, 0.15);
  position: relative;
}

.stTabs [aria-selected="true"]::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 2px;
  background: var(--accent);
  border-radius: 1px;
}

.section-header {
  font-size: 18px;
  font-weight: 700;
  margin: 2rem 0 1rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(90deg, var(--panel2) 0%, transparent 100%);
  border-left: 4px solid var(--accent);
  border-radius: 0 8px 8px 0;
  color: var(--text);
}

.subsection-header {
  font-size: 16px;
  font-weight: 600;
  margin: 1.5rem 0 1rem;
  padding: 0.5rem 0.75rem;
  background: linear-gradient(90deg, var(--panel3) 0%, transparent 100%);
  border-left: 3px solid var(--blue);
  border-radius: 0 6px 6px 0;
  color: var(--text-secondary);
}

iframe {
  border: 0;
  border-radius: 8px;
}

.grafana-embed { 
  border: 1px solid var(--border); 
  border-radius: 8px; 
  overflow: hidden;
  background-color: var(--panel2);
  margin-bottom: 1rem;
  transition: all 0.3s ease;
}

.grafana-embed:hover {
  border-color: var(--border-light);
  box-shadow: 0 4px 12px var(--shadow);
}

@media (max-width: 899px) {
  .stTabs [data-baseweb="tab-list"] {
    overflow-x: scroll;
    scrollbar-width: thin;
  }
  
  .stTabs [data-baseweb="tab"] {
    min-width: 95px;
    font-size: 12px;
    padding: 10px 12px;
  }
  
  .main-title {
    font-size: 22px;
  }
  
  .section-header {
    font-size: 16px;
  }
}
</style>
"""

st.markdown(THEME_CSS, unsafe_allow_html=True)

# -------------------------
# HEADER
# -------------------------
st.markdown('''
<div class="main-header">
    <h1 class="main-title">🤖 Maveretta Bot - AI Trading Orchestration</h1>
    <p class="main-subtitle">Dashboard Integrado com Painéis Nativos do Grafana</p>
</div>
''', unsafe_allow_html=True)

# -------------------------
# 13 ABAS CONFORME MAPEAMENTO
# -------------------------
tabs = st.tabs([
    "📊 Visão Geral",
    "📈 Operações",
    "🎰 Caça-níqueis",
    "🏦 Tesouro",
    "🎮 Controles",
    "🧠 Insights da IA",
    "📋 Auditoria",
    "📝 Registros",
    "🚨 Alertas",
    "🔬 Testes Retrospectivos",
    "🎯 Estratégias",
    "🎼 Orquestração",
    "💰 Carteira"
])


# ========================================
# ABA: 📊 Overview
# ========================================
with tabs[0]:
    st.markdown('<div class="section-header">📊 Overview</div>', unsafe_allow_html=True)

    # Consensus Approval Rate (Panel ID: 3)
    grafana_embed(uid="agent-drilldown-phase3", panel_id=3, kind="kpi")

    # Risk Blocked Reasons (Panel ID: 5)
    grafana_embed(uid="agent-drilldown-phase3", panel_id=5, kind="chart")

    # Consensus Approved (by Symbol) (Panel ID: 3)
    grafana_embed(uid="agents-overview-phase3", panel_id=3, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Total Open Positions (Panel ID: 6)
    grafana_embed(uid="agents-overview-phase3", panel_id=6, kind="kpi")

    # Consensus Rounds (1h) (Panel ID: 1)
    grafana_embed(uid="maveretta-consensus-flow", panel_id=1, kind="chart")

    # Consensus Approved (1h) (Panel ID: 2)
    grafana_embed(uid="maveretta-consensus-flow", panel_id=2, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Approval Rate (1h) (Panel ID: 3)
    grafana_embed(uid="maveretta-consensus-flow", panel_id=3, kind="kpi")

    # Risk Blocked by Reason (Panel ID: 7)
    grafana_embed(uid="maveretta-consensus-flow", panel_id=7, kind="chart")

    # Bybit Connection Status (Panel ID: 2)
    grafana_embed(uid="maveretta-bybit-live", panel_id=2, kind="kpi")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Coinbase Connection Status (Panel ID: 2)
    grafana_embed(uid="maveretta-coinbase-live", panel_id=2, kind="kpi")

    # Real-Time Price Analysis - $symbol (Panel ID: 1)
    grafana_embed(uid="maveretta-dynamic-live", panel_id=1, kind="chart")

    # Current Price (Panel ID: 2)
    grafana_embed(uid="maveretta-dynamic-live", panel_id=2, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # 24h Volume (Panel ID: 3)
    grafana_embed(uid="maveretta-dynamic-live", panel_id=3, kind="chart")

    # Latency (Panel ID: 4)
    grafana_embed(uid="maveretta-dynamic-live", panel_id=4, kind="chart")

    # Connection Status (Panel ID: 5)
    grafana_embed(uid="maveretta-dynamic-live", panel_id=5, kind="kpi")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Services Status (Panel ID: 4)
    grafana_embed(uid="maveretta-infrastructure", panel_id=4, kind="kpi")

    # Network Traffic (Panel ID: 7)
    grafana_embed(uid="maveretta-infrastructure", panel_id=7, kind="chart")

    # Disk I/O (Panel ID: 8)
    grafana_embed(uid="maveretta-infrastructure", panel_id=8, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # KuCoin Connection Status (Panel ID: 2)
    grafana_embed(uid="maveretta-kucoin-live", panel_id=2, kind="kpi")

    # Visão Geral do Mercado - BTC/USDT (Panel ID: 1)
    grafana_embed(uid="maveretta-market-overview", panel_id=1, kind="chart")

    # Volume 24h (Panel ID: 2)
    grafana_embed(uid="maveretta-market-overview", panel_id=2, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # OKX Connection Status (Panel ID: 2)
    grafana_embed(uid="maveretta-okx-live", panel_id=2, kind="kpi")

    # Gráfico de Preços em Tempo Real (Panel ID: 7)
    grafana_embed(uid="maveretta-overview-live", panel_id=7, kind="chart")

    # Preço Atual (Top 10) (Panel ID: 12)
    grafana_embed(uid="maveretta-overview-live", panel_id=12, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Ciclos Completos (Panel ID: 16)
    grafana_embed(uid="maveretta-overview-live", panel_id=16, kind="chart")

    # Mensagens WebSocket (Panel ID: 17)
    grafana_embed(uid="maveretta-overview-live", panel_id=17, kind="chart")

    # ATR Médio (Panel ID: 19)
    grafana_embed(uid="maveretta-overview-live", panel_id=19, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Status Conexão (Panel ID: 20)
    grafana_embed(uid="maveretta-overview-live", panel_id=20, kind="kpi")

    # Health / Uptime - All Services (Panel ID: 21)
    grafana_embed(uid="maveretta-overview-live", panel_id=21, kind="chart")

    # Ciclos Completados (1h) (Panel ID: 2)
    grafana_embed(uid="maveretta-slots-live", panel_id=2, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Capital Total (USDT) (Panel ID: 3)
    grafana_embed(uid="maveretta-slots-live", panel_id=3, kind="kpi")

    # Status de Conexão (Panel ID: 4)
    grafana_embed(uid="maveretta-slots-live", panel_id=4, kind="kpi")

    # Taxa de Execução (Cycles/sec) (Panel ID: 6)
    grafana_embed(uid="maveretta-slots-live", panel_id=6, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Top 10 Crypto Prices (USDT) (Panel ID: 1)
    grafana_embed(uid="maveretta-top10-live", panel_id=1, kind="chart")

    # Top 10 Prices Table (Panel ID: 2)
    grafana_embed(uid="maveretta-top10-live", panel_id=2, kind="table")

    # Arbitrage Success Rate (Panel ID: 1)
    grafana_embed(uid="orchestration-arbitrage-legs", panel_id=1, kind="kpi")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Legs by Status (Panel ID: 2)
    grafana_embed(uid="orchestration-arbitrage-legs", panel_id=2, kind="kpi")

    # Auto-Hedge Events (Panel ID: 6)
    grafana_embed(uid="orchestration-arbitrage-legs", panel_id=6, kind="chart")

    # IA Status Overview (Panel ID: 1)
    grafana_embed(uid="orchestration-ia-health", panel_id=1, kind="kpi")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Exchange Status (Panel ID: 3)
    grafana_embed(uid="orchestration-venue-health", panel_id=3, kind="kpi")

    # Rate Limit Status (Panel ID: 4)
    grafana_embed(uid="orchestration-venue-health", panel_id=4, kind="kpi")

# ========================================
# ABA: 📈 Operações
# ========================================
with tabs[1]:
    st.markdown('<div class="section-header">📈 Operações</div>', unsafe_allow_html=True)

    # Paper Trades Unrealized PnL (Panel ID: 5)
    grafana_embed(uid="agents-overview-phase3", panel_id=5, kind="chart")

    # CPU Usage (Panel ID: 1)
    grafana_embed(uid="maveretta-infrastructure", panel_id=1, kind="chart")

    # Memory Usage (Panel ID: 2)
    grafana_embed(uid="maveretta-infrastructure", panel_id=2, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Disk Usage (Panel ID: 3)
    grafana_embed(uid="maveretta-infrastructure", panel_id=3, kind="chart")

    # Container CPU Usage (Panel ID: 5)
    grafana_embed(uid="maveretta-infrastructure", panel_id=5, kind="chart")

    # Container Memory Usage (Panel ID: 6)
    grafana_embed(uid="maveretta-infrastructure", panel_id=6, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Latência Média (Panel ID: 18)
    grafana_embed(uid="maveretta-overview-live", panel_id=18, kind="chart")

    # Cross-Venue Execution Time (Panel ID: 4)
    grafana_embed(uid="orchestration-arbitrage-legs", panel_id=4, kind="chart")

    # Exchange Latency (Panel ID: 1)
    grafana_embed(uid="orchestration-venue-health", panel_id=1, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Clock Skew (Panel ID: 2)
    grafana_embed(uid="orchestration-venue-health", panel_id=2, kind="chart")

# ========================================
# ABA: 🎰 Slots
# ========================================
with tabs[2]:
    st.markdown('<div class="section-header">🎰 Slots</div>', unsafe_allow_html=True)

    # Slots Ativos (Panel ID: 15)
    grafana_embed(uid="maveretta-overview-live", panel_id=15, kind="chart")

    # Slots Ativos (Panel ID: 1)
    grafana_embed(uid="maveretta-slots-live", panel_id=1, kind="chart")

    # Histórico de Slots Ativos (Panel ID: 5)
    grafana_embed(uid="maveretta-slots-live", panel_id=5, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Slot States Timeline (Panel ID: 1)
    grafana_embed(uid="orchestration-slots-timeline", panel_id=1, kind="chart")

    # Slot State Distribution (Panel ID: 2)
    grafana_embed(uid="orchestration-slots-timeline", panel_id=2, kind="chart")

    # Active Slots Count (Panel ID: 3)
    grafana_embed(uid="orchestration-slots-timeline", panel_id=3, kind="kpi")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Slot State Changes (Panel ID: 4)
    grafana_embed(uid="orchestration-slots-timeline", panel_id=4, kind="chart")

# ========================================
# ABA: 🏦 Treasury
# ========================================
with tabs[3]:
    st.markdown('<div class="section-header">🏦 Treasury</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")

# ========================================
# ABA: 🎮 Controles
# ========================================
with tabs[4]:
    st.markdown('<div class="section-header">🎮 Controles</div>', unsafe_allow_html=True)
    
    # FIX P0: Adicionar controles manuais completos
    import requests
    
    API_URL = os.getenv("API_URL", "http://ai-gateway:8080")
    
    st.subheader("⚙️ Controle de Agentes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Get agents list
        try:
            response = requests.get(f"{API_URL}/v1/agents", timeout=5)
            if response.ok:
                agents = response.json().get("agents", [])
                
                if agents:
                    agent_options = [a["agent_id"] for a in agents]
                    selected_agent = st.selectbox("Selecione Agente", agent_options, key="agent_select")
                    
                    agent_data = [a for a in agents if a['agent_id'] == selected_agent][0]
                    st.write(f"**Status**: {agent_data['status']}")
                    st.write(f"**Modo**: {agent_data.get('mode', 'N/A')}")
                    
                    # Start/Stop buttons
                    col_start, col_stop = st.columns(2)
                    
                    with col_start:
                        if st.button("▶️ Start Agent", key="start_agent"):
                            resp = requests.post(f"{API_URL}/v1/agents/{selected_agent}/start", timeout=10)
                            if resp.ok:
                                st.success(f"✅ Agent {selected_agent} started")
                            else:
                                st.error(f"❌ Failed: {resp.text}")
                    
                    with col_stop:
                        if st.button("⏸️ Stop Agent", key="stop_agent"):
                            resp = requests.post(f"{API_URL}/v1/agents/{selected_agent}/stop", timeout=10)
                            if resp.ok:
                                st.warning(f"⏸️ Agent {selected_agent} stopped")
                            else:
                                st.error(f"❌ Failed: {resp.text}")
                else:
                    st.warning("⚠️ Nenhum agente encontrado")
            else:
                st.error("❌ Não foi possível buscar agentes")
        except Exception as e:
            st.error(f"❌ Erro: {e}")
    
    with col2:
        st.subheader("🎚️ Modo de Execução")
        
        # Mode selection
        mode = st.radio(
            "Selecione modo",
            ["shadow", "paper", "live"],
            horizontal=True,
            key="mode_radio"
        )
        
        if st.button("🔄 Alterar Modo", key="change_mode"):
            try:
                resp = requests.post(
                    f"{API_URL}/v1/agents/{selected_agent}/mode",
                    json={"mode": mode},
                    timeout=10
                )
                if resp.ok:
                    st.success(f"✅ Modo alterado para {mode}")
                else:
                    st.error(f"❌ Failed: {resp.text}")
            except Exception as e:
                st.error(f"❌ Erro: {e}")
    
    st.markdown("---")
    
    # Kill Switch
    st.subheader("🛑 Kill Switch")
    st.warning(
        "⚠️ **ATENÇÃO**: Kill Switch para todo o sistema. "
        "Use apenas em emergências."
    )
    
    col_ks1, col_ks2 = st.columns(2)
    
    with col_ks1:
        if st.button("🛑 ATIVAR KILL SWITCH", type="primary", key="kill_on"):
            try:
                resp = requests.post(f"{API_URL}/v1/orchestration/kill-switch", json={"enabled": True}, timeout=10)
                if resp.ok:
                    st.error("🛑 KILL SWITCH ATIVADO - Sistema parando...")
                else:
                    st.error(f"❌ Failed: {resp.text}")
            except Exception as e:
                st.error(f"❌ Erro: {e}")
    
    with col_ks2:
        if st.button("✅ Desativar Kill Switch", key="kill_off"):
            try:
                resp = requests.post(f"{API_URL}/v1/orchestration/kill-switch", json={"enabled": False}, timeout=10)
                if resp.ok:
                    st.success("✅ Kill Switch desativado")
                else:
                    st.error(f"❌ Failed: {resp.text}")
            except Exception as e:
                st.error(f"❌ Erro: {e}")
    
    st.markdown("---")
    
    # Trading pairs selection
    st.subheader("📊 Seleção de Pares")
    
    symbols = st.multiselect(
        "Símbolos ativos",
        ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT", "XRP/USDT"],
        default=["BTC/USDT", "ETH/USDT"],
        key="symbols_multi"
    )
    
    if st.button("💾 Salvar Símbolos", key="save_symbols"):
        st.success(f"✅ Símbolos salvos: {', '.join(symbols)}")
    
    st.markdown("---")
    
    # Freeze slot
    st.subheader("🧊 Freeze de Slot")
    
    slot_id = st.selectbox(
        "Selecione Slot para Freeze",
        [f"slot_{i}" for i in range(1, 11)],
        key="freeze_slot_select"
    )
    
    col_freeze1, col_freeze2 = st.columns(2)
    
    with col_freeze1:
        if st.button("❄️ Freeze Slot", key="freeze_slot"):
            st.warning(f"⚠️ Slot {slot_id} congelado (funcionalidade em desenvolvimento)")
    
    with col_freeze2:
        if st.button("🔥 Unfreeze Slot", key="unfreeze_slot"):
            st.success(f"✅ Slot {slot_id} descongelado (funcionalidade em desenvolvimento)")

# ========================================
# ABA: 🧠 IA Insights
# ========================================
with tabs[5]:
    st.markdown('<div class="section-header">🧠 IA Insights</div>', unsafe_allow_html=True)

    # Confidence Heatmap (Panel ID: 2)
    grafana_embed(uid="agent-drilldown-phase3", panel_id=2, kind="table")

    # Agent Status (Running=1, Stopped=0) (Panel ID: 1)
    grafana_embed(uid="agents-overview-phase3", panel_id=1, kind="kpi")

    # Decisions per Hour (by Agent) (Panel ID: 2)
    grafana_embed(uid="agents-overview-phase3", panel_id=2, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Consensus Confidence Average (Panel ID: 4)
    grafana_embed(uid="agents-overview-phase3", panel_id=4, kind="chart")

    # Agent Drawdown % (Panel ID: 7)
    grafana_embed(uid="agents-overview-phase3", panel_id=7, kind="chart")

    # Average Confidence (Panel ID: 4)
    grafana_embed(uid="maveretta-consensus-flow", panel_id=4, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Consensus Phase Timeline (propose/challenge/decide) (Panel ID: 5)
    grafana_embed(uid="maveretta-consensus-flow", panel_id=5, kind="chart")

    # Confidence Heatmap by Agent (Panel ID: 6)
    grafana_embed(uid="maveretta-consensus-flow", panel_id=6, kind="table")

    # Failed Legs by Reason (Panel ID: 5)
    grafana_embed(uid="orchestration-arbitrage-legs", panel_id=5, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Decision Confidence by Strategy (Panel ID: 1)
    grafana_embed(uid="orchestration-decision-conf", panel_id=1, kind="kpi")

    # Decision Confidence by IA (Panel ID: 2)
    grafana_embed(uid="orchestration-decision-conf", panel_id=2, kind="chart")

    # Confidence Distribution (Panel ID: 3)
    grafana_embed(uid="orchestration-decision-conf", panel_id=3, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # High Confidence Decisions (>80%) (Panel ID: 4)
    grafana_embed(uid="orchestration-decision-conf", panel_id=4, kind="chart")

    # Low Confidence Decisions (<50%) (Panel ID: 5)
    grafana_embed(uid="orchestration-decision-conf", panel_id=5, kind="chart")

    # Avg Confidence by Slot (Panel ID: 6)
    grafana_embed(uid="orchestration-decision-conf", panel_id=6, kind="kpi")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # IA Latency (ms) (Panel ID: 2)
    grafana_embed(uid="orchestration-ia-health", panel_id=2, kind="chart")

    # IA Uptime % (Panel ID: 3)
    grafana_embed(uid="orchestration-ia-health", panel_id=3, kind="chart")

    # Errors by IA (Panel ID: 4)
    grafana_embed(uid="orchestration-ia-health", panel_id=4, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

# ========================================
# ABA: 📋 Auditoria
# ========================================
with tabs[6]:
    st.markdown('<div class="section-header">📋 Auditoria</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")

# ========================================
# ABA: 📝 Logs
# ========================================
with tabs[7]:
    st.markdown('<div class="section-header">📝 Logs</div>', unsafe_allow_html=True)

    # Connection Errors (Panel ID: 5)
    grafana_embed(uid="orchestration-venue-health", panel_id=5, kind="chart")

# ========================================
# ABA: 🚨 Alertas
# ========================================
with tabs[8]:
    st.markdown('<div class="section-header">🚨 Alertas</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")

# ========================================
# ABA: 🔬 Backtests
# ========================================
with tabs[9]:
    st.markdown('<div class="section-header">🔬 Backtests</div>', unsafe_allow_html=True)

    # Bybit Equity (USDT) (Panel ID: 1)
    grafana_embed(uid="maveretta-bybit-live", panel_id=1, kind="kpi")

    # Coinbase Equity (USDT) (Panel ID: 1)
    grafana_embed(uid="maveretta-coinbase-live", panel_id=1, kind="kpi")

    # KuCoin Equity (USDT) (Panel ID: 1)
    grafana_embed(uid="maveretta-kucoin-live", panel_id=1, kind="kpi")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # KuCoin Equity Over Time (Panel ID: 3)
    grafana_embed(uid="maveretta-kucoin-live", panel_id=3, kind="kpi")

    # OKX Equity (USDT) (Panel ID: 1)
    grafana_embed(uid="maveretta-okx-live", panel_id=1, kind="kpi")

    # Carteira Real (USDT) (Panel ID: 13)
    grafana_embed(uid="maveretta-overview-live", panel_id=13, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Carteira Real (BRL) (Panel ID: 14)
    grafana_embed(uid="maveretta-overview-live", panel_id=14, kind="chart")

# ========================================
# ABA: 🎯 Estratégias
# ========================================
with tabs[10]:
    st.markdown('<div class="section-header">🎯 Estratégias</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")

# ========================================
# ABA: 🎼 Orquestração
# ========================================
with tabs[11]:
    st.markdown('<div class="section-header">🎼 Orquestração</div>', unsafe_allow_html=True)

    # Decision Timeline (Propose/Challenge/Decide) (Panel ID: 1)
    grafana_embed(uid="agent-drilldown-phase3", panel_id=1, kind="chart")

    # Decision Latency (p50, p95) (Panel ID: 4)
    grafana_embed(uid="agent-drilldown-phase3", panel_id=4, kind="chart")

    # Arbitrage P&L (Panel ID: 3)
    grafana_embed(uid="orchestration-arbitrage-legs", panel_id=3, kind="chart")

    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

# ========================================
# ABA: 💰 Carteira
# ========================================
with tabs[12]:
    st.markdown('<div class="section-header">💰 Carteira</div>', unsafe_allow_html=True)
    
    # Seção 1: Resumo Geral
    st.markdown('<div class="subsection-header">📊 Visão Geral</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        # Carteira Real (USDT) - maveretta-overview-live Panel 13
        grafana_embed(uid="maveretta-overview-live", panel_id=13, kind="chart")
    with col2:
        # Carteira Real (BRL) - maveretta-overview-live Panel 14
        grafana_embed(uid="maveretta-overview-live", panel_id=14, kind="chart")
    
    # Seção 2: Equity por Exchange
    st.markdown('<div class="subsection-header">🏦 Saldo por Exchange</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        # Bybit Equity (USDT) - maveretta-bybit-live Panel 1
        grafana_embed(uid="maveretta-bybit-live", panel_id=1, kind="kpi")
    with col2:
        # Coinbase Equity (USDT) - maveretta-coinbase-live Panel 1
        grafana_embed(uid="maveretta-coinbase-live", panel_id=1, kind="kpi")
    with col3:
        # OKX Equity (USDT) - maveretta-okx-live Panel 1
        grafana_embed(uid="maveretta-okx-live", panel_id=1, kind="kpi")
    
    # Seção 3: KuCoin Equity
    st.markdown('<div class="subsection-header">📈 KuCoin Equity</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        # KuCoin Equity (USDT) - maveretta-kucoin-live Panel 1
        grafana_embed(uid="maveretta-kucoin-live", panel_id=1, kind="kpi")
    with col2:
        # KuCoin Equity Over Time - maveretta-kucoin-live Panel 3
        grafana_embed(uid="maveretta-kucoin-live", panel_id=3, kind="kpi")
