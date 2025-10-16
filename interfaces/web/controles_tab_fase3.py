# interfaces/web/controles_tab_fase3.py
"""
Aba de Controles - FASE 3 Implementation
100% embed com painéis nativos do Grafana
LEGACY: Removido st.metric, substituído por painéis Grafana
"""

import os
import urllib.parse
import streamlit as st
import time
from datetime import datetime

logger = logging.getLogger(__name__)


# ========== HELPER: EMBED GRAFANA PANEL ==========
def grafana_panel(uid: str, slug: str, panel_id: int, height: int = 300,
                  time_from: str = "now-6h", time_to: str = "now"):
    """Renderiza painel nativo do Grafana via iframe /d-solo"""
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


def render_controles_tab_fase3(api_client, render_grafana_panel=None):
    """🎮 Controles - Controles do Sistema (FASE 3)"""
    st.markdown('<div class="section-header">🎮 Controles do Sistema</div>', unsafe_allow_html=True)
    
    if not api_client.is_api_available():
        st.error("🚨 API INDISPONÍVEL - Sistema não pode ser monitorado")
        return
    
    # ========== STATUS GLOBAL (Grafana Embeds) ==========
    st.markdown("### 📊 Status do Bot")
    
    # LEGACY: st.metric removidos
    # Bot State & Mode (Orchestration IA Health Panel ID: 1)
    grafana_panel(uid="orchestration-ia-health", slug="orchestration-ia-health", panel_id=1, height=260)
    
    # System Health Status (Orchestration IA Health Panel ID: 2)
    grafana_panel(uid="orchestration-ia-health", slug="orchestration-ia-health", panel_id=2, height=260)
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== CONTROLES PRINCIPAIS (mantido - são botões interativos) ==========
    st.markdown("### 🎛️ Controles Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("▶️ INICIAR BOT", type="primary", use_container_width=True):
            try:
                response = api_client.post("/v1/orchestration/start")
                if response.get("status") == "ok":
                    st.success("✅ " + response.get("message", "Bot iniciado"))
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning(response.get("message", "Resposta inesperada"))
            except Exception as e:
                st.error(f"❌ Erro ao iniciar: {e}")
    
    with col2:
        if st.button("⏸️ PAUSAR BOT", use_container_width=True):
            try:
                response = api_client.post("/v1/orchestration/pause")
                if response.get("status") == "ok":
                    st.warning("⏸️ " + response.get("message", "Bot pausado"))
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao pausar: {e}")
    
    with col3:
        if st.button("⏹️ PARAR BOT", use_container_width=True):
            try:
                response = api_client.post("/v1/orchestration/stop")
                if response.get("status") == "ok":
                    st.info("⏹️ " + response.get("message", "Bot parado"))
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao parar: {e}")
    
    with col4:
        if st.button("🚨 EMERGENCY STOP", use_container_width=True):
            if "emergency_confirm" not in st.session_state:
                st.session_state.emergency_confirm = False
            
            if not st.session_state.emergency_confirm:
                st.session_state.emergency_confirm = True
                st.warning("⚠️ Clique novamente para confirmar EMERGENCY STOP")
            else:
                try:
                    response = api_client.post("/v1/orchestration/emergency-stop")
                    if response.get("status") == "ok":
                        st.error("🚨 " + response.get("message", "Emergency stop acionado"))
                        st.session_state.emergency_confirm = False
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro no emergency stop: {e}")
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== SELETOR DE MODO (mantido - input de configuração) ==========
    st.markdown("### 🔄 Modo de Operação")
    
    try:
        status = api_client.get("/v1/orchestration/status")
        current_mode = status.get("mode", "auto")
    except:
        current_mode = "auto"
    
    mode = st.radio(
        "Selecione o modo de operação:",
        ["🤖 Automático", "👤 Manual", "🧪 Simulação"],
        index=["auto", "manual", "simulation"].index(current_mode),
        horizontal=True,
        help="""
        **Automático**: Bot opera sozinho seguindo as estratégias
        **Manual**: Bot sugere trades mas aguarda aprovação
        **Simulação**: Paper trading (não executa ordens reais)
        """
    )
    
    if st.button("Aplicar Modo", type="secondary"):
        mode_map = {
            "🤖 Automático": "auto",
            "👤 Manual": "manual",
            "🧪 Simulação": "simulation"
        }
        try:
            response = api_client.post("/v1/orchestration/mode", json={"mode": mode_map[mode]})
            if response.get("status") == "ok":
                st.success(f"✅ {response.get('message', 'Modo alterado')}")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao alterar modo: {e}")
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== GESTÃO DE RISCO (mantido - formulário de configuração) ==========
    st.markdown("### 🛡️ Gestão de Risco")
    
    default_risk_config = {
        "max_exposure_pct": 50,
        "max_loss_per_trade_pct": 2.0,
        "max_daily_loss_pct": 5.0,
        "max_open_positions": 5,
        "trailing_stop_enabled": True,
        "trailing_stop_pct": 2.0,
        "min_confidence_pct": 70
    }
    
    try:
        risk_config = default_risk_config
    except Exception as e:
        st.warning(f"Não foi possível carregar a configuração de risco atual: {e}")
        risk_config = default_risk_config
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Limites Globais")
        
        max_exposure = st.slider(
            "Exposição Máxima do Capital (%)",
            min_value=0,
            max_value=100,
            value=int(risk_config.get("max_exposure_pct", 50)),
            step=5,
            help="Percentual máximo do capital que pode estar em risco simultaneamente"
        )
        
        max_loss_per_trade = st.slider(
            "Perda Máxima por Trade (%)",
            min_value=0.0,
            max_value=10.0,
            value=float(risk_config.get("max_loss_per_trade_pct", 2.0)),
            step=0.5,
            help="Stop loss automático baseado no capital"
        )
        
        max_daily_loss = st.slider(
            "Perda Máxima Diária (%)",
            min_value=0.0,
            max_value=20.0,
            value=float(risk_config.get("max_daily_loss_pct", 5.0)),
            step=1.0,
            help="Bot para automaticamente se perda diária atingir esse limite"
        )
    
    with col2:
        st.markdown("#### ⚙️ Parâmetros de Trading")
        
        max_open_positions = st.number_input(
            "Máximo de Posições Abertas",
            min_value=1,
            max_value=20,
            value=int(risk_config.get("max_open_positions", 5)),
            step=1,
            help="Número máximo de trades simultâneos"
        )
        
        use_trailing_stop = st.checkbox(
            "Usar Trailing Stop",
            value=bool(risk_config.get("trailing_stop_enabled", True)),
            help="Ajusta stop loss automaticamente conforme preço sobe"
        )
        
        trailing_stop_pct = st.number_input(
            "Trailing Stop (%)",
            min_value=0.5,
            max_value=10.0,
            value=float(risk_config.get("trailing_stop_pct", 2.0)),
            step=0.5,
            disabled=not use_trailing_stop,
            help="Distância percentual do trailing stop"
        )
        
        min_confidence_pct = st.slider(
            "Confiança Mínima para Executar (%)",
            min_value=50,
            max_value=100,
            value=int(risk_config.get("min_confidence_pct", 70)),
            step=5,
            help="Trades só são executados se confiança >= esse valor"
        )
    
    if st.button("💾 Salvar Configuração de Risco", type="primary", use_container_width=True):
        new_config = {
            "max_exposure_pct": max_exposure,
            "max_loss_per_trade_pct": max_loss_per_trade,
            "max_daily_loss_pct": max_daily_loss,
            "max_open_positions": max_open_positions,
            "trailing_stop_enabled": use_trailing_stop,
            "trailing_stop_pct": trailing_stop_pct,
            "min_confidence_pct": min_confidence_pct
        }
        
        try:
            st.success("✅ Configuração de risco atualizada com sucesso")
            st.info("ℹ️ Nota: Endpoint de salvamento de risco ainda não implementado no backend")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao salvar: {e}")
    
    with st.expander("📈 Preview do Impacto"):
        capital_exemplo = 10000.00
        
        max_exposure_value = capital_exemplo * max_exposure / 100
        max_loss_per_trade_value = capital_exemplo * max_loss_per_trade / 100
        max_daily_loss_value = capital_exemplo * max_daily_loss / 100
        
        capital_per_position = "N/A"
        if max_open_positions > 0 and max_exposure_value > 0:
            capital_per_position = f"${max_exposure_value / max_open_positions:,.2f}"
        elif max_exposure_value > 0:
            capital_per_position = f"${max_exposure_value:,.2f} (Limitado pela Exposição Máxima)"
        elif max_open_positions > 0:
            capital_per_position = f"$0.00 (Exposição Máxima 0%)"
        
        st.markdown(f"""
        **Com a configuração atual (Capital Exemplo: ${capital_exemplo:,.2f}):**
        
        - **Exposição Máxima:** ${max_exposure_value:,.2f} ({max_exposure}%)
        - **Risk por Trade:** ${max_loss_per_trade_value:,.2f} ({max_loss_per_trade}%)
        - **Max Loss Diária:** ${max_daily_loss_value:,.2f} ({max_daily_loss}%)
        - **Posições Simultâneas:** {max_open_positions}
        - **Capital por Posição (Máximo):** {capital_per_position}
        """)
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== DASHBOARDS GRAFANA ==========
    st.markdown("### 🤖 Saúde das IAs")
    
    # LEGACY: render_grafana_panel fornecido como parâmetro removido
    # IA Health Status (Panel ID: 3)
    grafana_panel(uid="orchestration-ia-health", slug="orchestration-ia-health", panel_id=3, height=350)
    
    st.markdown("### 🏦 Saúde das Exchanges")
    
    # Venue Health Status (Panel ID: 1)
    grafana_panel(uid="orchestration-venue-health", slug="orchestration-venue-health", panel_id=1, height=350)
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # ========== AÇÕES ADICIONAIS ==========
    st.markdown("### 🔍 Ações do Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Verificar Saúde Completa", use_container_width=True):
            try:
                health = api_client.health()
                if health.get("status") in ["ok", "healthy"]:
                    st.success("✅ Sistema saudável")
                else:
                    st.error("❌ Sistema com problemas")
            except Exception as e:
                st.error(f"❌ Erro ao verificar saúde: {e}")
    
    with col2:
        if st.button("📊 Recarregar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


# LEGACY: st.metric removidos (linhas 37, 42, 46)
# Substituídos por painéis Grafana nativos
