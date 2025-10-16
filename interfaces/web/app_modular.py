# interfaces/web/app_modular.py
"""
Maveretta Bot - Dashboard Principal Modularizado
Versão: 2.1.0
Interface Streamlit com 13 abas organizadas em módulos separados
"""
import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

# Import modules
from modules import (
    tab_overview,
    tab_operations,
    tab_slots,
    tab_treasury,
    tab_controls,
    tab_ia_insights,
    tab_audit,
    tab_logs,
    tab_alerts,
    tab_backtest,
    tab_strategies,
    tab_orchestration,
    tab_wallet,
)

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
    <p class="main-subtitle">Dashboard Modular v2.1 | Atualização em Tempo Real</p>
</div>
''', unsafe_allow_html=True)

# -------------------------
# 13 ABAS
# -------------------------
tabs = st.tabs([
    "📊 Visão Geral",
    "📈 Operações",
    "🎰 Slots",
    "🏦 Tesouraria",
    "🎮 Controles",
    "🧠 IA Insights",
    "📋 Auditoria",
    "📏 Logs",
    "🚨 Alertas",
    "🔬 Backtests",
    "🎯 Estratégias",
    "🎼 Orquestração",
    "💰 Carteira"
])

# Render each tab
with tabs[0]:
    tab_overview.render()

with tabs[1]:
    tab_operations.render()

with tabs[2]:
    tab_slots.render()

with tabs[3]:
    tab_treasury.render()

with tabs[4]:
    tab_controls.render()

with tabs[5]:
    tab_ia_insights.render()

with tabs[6]:
    tab_audit.render()

with tabs[7]:
    tab_logs.render()

with tabs[8]:
    tab_alerts.render()

with tabs[9]:
    tab_backtest.render()

with tabs[10]:
    tab_strategies.render()

with tabs[11]:
    tab_orchestration.render()

with tabs[12]:
    tab_wallet.render()

# -------------------------
# FOOTER
# -------------------------
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: var(--muted); font-size: 12px; padding: 1rem 0;">'
    'Maveretta Trading Bot v2.1.0 | '
    '© 2025 | '
    'Dashboard Otimizado e Modularizado'
    '</div>',
    unsafe_allow_html=True
)
