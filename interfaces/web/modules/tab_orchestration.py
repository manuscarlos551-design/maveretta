"""Aba: Orquestração - Tempo Real."""
import streamlit as st
import os
import requests
import time
from helpers.grafana_helper import grafana_panel

API_URL = os.getenv("API_URL", "http://ai-gateway:8080")

def render():
    """Renderiza a aba Orquestração com atualização em tempo real."""
    st.markdown('<div class="section-header">🎼 Orquestração</div>', unsafe_allow_html=True)

    # ============== LIVE WORK BOX - CAIXA DE TRABALHO AO VIVO ==============
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1c2531 0%, #252d3d 100%); 
                border: 2px solid #f5c451; border-radius: 12px; padding: 1.5rem; 
                margin-bottom: 2rem; box-shadow: 0 4px 12px rgba(245, 196, 81, 0.2);">
        <h3 style="margin: 0 0 1rem 0; color: #f5c451; display: flex; align-items: center;">
            <span style="margin-right: 0.5rem;">📡</span> Live Work Box - Orquestração em Tempo Real
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Placeholder for real-time updates (atualização a cada 2-5s)
    live_box = st.container()
    
    with live_box:
        col1, col2, col3, col4 = st.columns(4)
        
        # Fetch orchestration status
        try:
            response = requests.get(f"{API_URL}/v1/orchestration/status", timeout=3)
            if response.ok:
                data = response.json()
                
                with col1:
                    status = data.get("status", "Unknown").upper()
                    status_color = "🟢" if status == "RUNNING" else "🔴"
                    st.metric("Status", f"{status_color} {status}")
                with col2:
                    st.metric("🧠 Agentes Ativos", data.get("active_agents", 0))
                with col3:
                    last_tick = data.get('last_tick_seconds', 0)
                    st.metric("⏱️ Último Tick", f"{last_tick}s atrás")
                with col4:
                    consensus = data.get("consensus_status", "N/A")
                    st.metric("🎯 Consenso", consensus)
                
                # Decisões recentes (últimas 5)
                st.markdown("#### 🎯 Decisões Recentes (últimas execuções)")
                decisions = data.get("recent_decisions", [])[:5]
                
                if decisions:
                    for idx, dec in enumerate(decisions, 1):
                        action = dec.get('action', 'N/A')
                        symbol = dec.get('symbol', 'N/A')
                        confidence = dec.get('confidence', 0)
                        timestamp = dec.get('timestamp', 'N/A')
                        
                        emoji = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "⚪"
                        st.markdown(
                            f"**{idx}.** {emoji} **{action}** `{symbol}` | "
                            f"Confiança: `{confidence:.1%}` | {timestamp}"
                        )
                else:
                    st.info("🔍 Aguardando decisões...")
                    
                # Votos dos agentes (atualizações ao vivo)
                st.markdown("#### 🗳️ Votos dos Agentes (última rodada)")
                votes = data.get("agent_votes", [])
                
                if votes:
                    vote_cols = st.columns(min(len(votes), 4))
                    for idx, vote in enumerate(votes[:4]):
                        with vote_cols[idx]:
                            agent_name = vote.get('agent', 'Unknown')
                            vote_action = vote.get('vote', 'HOLD')
                            vote_conf = vote.get('confidence', 0)
                            
                            st.markdown(f"""
                            <div style="background: #252d3d; padding: 0.75rem; border-radius: 8px; text-align: center;">
                                <div style="font-size: 0.85rem; color: #8a95a6; margin-bottom: 0.25rem;">
                                    {agent_name}
                                </div>
                                <div style="font-size: 1.1rem; font-weight: bold; color: #f5c451;">
                                    {vote_action}
                                </div>
                                <div style="font-size: 0.8rem; color: #b8c2d3;">
                                    {vote_conf:.0%}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("⏳ Aguardando votos...")
                    
            else:
                st.warning(f"⚠️ API retornou status {response.status_code}")
        except requests.exceptions.Timeout:
            st.warning("⏱️ Timeout ao conectar com API (>3s)")
        except Exception as e:
            st.error(f"❌ Erro: {str(e)[:100]}")
    
    st.markdown("---")
    
    # Grafana panels
    st.subheader("📊 Painéis de Orquestração")
    
    # Decision Timeline
    grafana_panel(uid="agent-drilldown-phase3", slug="agent-drilldown-phase-3", panel_id=1, height=400)

    # Decision Latency (p50, p95)
    grafana_panel(uid="agent-drilldown-phase3", slug="agent-drilldown-phase-3", panel_id=4, height=400)

    # Arbitrage P&L
    grafana_panel(uid="orchestration-arbitrage-legs", slug="orchestration-arbitrage-legs", panel_id=3, height=400)
    
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    
    # IA Status Overview
    grafana_panel(uid="orchestration-ia-health", slug="orchestration-ia-health", panel_id=1, height=260)
    
    # Auto-refresh toggle
    st.markdown("---")
    auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=False, key="auto_refresh_orch")
    
    if auto_refresh:
        time.sleep(5)
        st.rerun()
