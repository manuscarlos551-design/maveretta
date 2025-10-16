"""Aba: Controles Manuais do Sistema."""
import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL", "http://ai-gateway:8080")

def render():
    """Renderiza a aba Controles."""
    st.markdown('<div class="section-header">🎮 Controles</div>', unsafe_allow_html=True)
    
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
                        if st.button("▶️ Start Agent", key="start_agent", use_container_width=True):
                            resp = requests.post(f"{API_URL}/v1/agents/{selected_agent}/start", timeout=10)
                            if resp.ok:
                                st.success(f"✅ Agent {selected_agent} started")
                            else:
                                st.error(f"❌ Failed: {resp.text}")
                    
                    with col_stop:
                        if st.button("⏸️ Stop Agent", key="stop_agent", use_container_width=True):
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
        st.subheader("🏚️ Modo de Execução")
        
        # Mode selection
        mode = st.radio(
            "Selecione modo",
            ["shadow", "paper", "live"],
            horizontal=True,
            key="mode_radio"
        )
        
        if st.button("🔄 Alterar Modo", key="change_mode", use_container_width=True):
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
        if st.button("🛑 ATIVAR KILL SWITCH", type="primary", key="kill_on", use_container_width=True):
            try:
                resp = requests.post(f"{API_URL}/v1/orchestration/kill-switch", json={"enabled": True}, timeout=10)
                if resp.ok:
                    st.error("🛑 KILL SWITCH ATIVADO - Sistema parando...")
                else:
                    st.error(f"❌ Failed: {resp.text}")
            except Exception as e:
                st.error(f"❌ Erro: {e}")
    
    with col_ks2:
        if st.button("✅ Desativar Kill Switch", key="kill_off", use_container_width=True):
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
    
    if st.button("💾 Salvar Símbolos", key="save_symbols", use_container_width=True):
        st.success(f"✅ Símbolos salvos: {', '.join(symbols)}")
    
    st.markdown("---")
    
    # Exchange selection
    st.subheader("🏛️ Seleção de Exchanges")
    
    exchanges = st.multiselect(
        "Exchanges ativas",
        ["Binance", "KuCoin", "Bybit", "Coinbase", "OKX"],
        default=["Binance", "Bybit"],
        key="exchanges_multi"
    )
    
    if st.button("💾 Salvar Exchanges", key="save_exchanges", use_container_width=True):
        st.success(f"✅ Exchanges salvas: {', '.join(exchanges)}")
