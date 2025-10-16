"""Aba: Estratégias."""
import streamlit as st

def render():
    """Renderiza a aba Estratégias."""
    st.markdown('<div class="section-header">🎯 Estratégias</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")
    
    # Placeholder para strategies
    st.markdown("""
    ### 📚 Features Planejadas:
    
    - **Estratégias Ativas**: Lista de estratégias em uso
    - **Performance**: Métricas de performance por estratégia
    - **Configuração**: Criar e editar estratégias
    - **Backtesting**: Testar estratégias antes de ativar
    - **Marketplace**: Importar estratégias da comunidade
    """)
    
    st.markdown("---")
    
    # Active strategies list
    st.subheader("🏁 Estratégias Ativas")
    
    strategies = [
        {"name": "AI Multi-Agent Consensus", "status": "✅ Ativa", "win_rate": "65%", "trades_24h": 12},
        {"name": "Scalping G1", "status": "✅ Ativa", "win_rate": "58%", "trades_24h": 45},
        {"name": "Tendência G2", "status": "⏸️ Pausada", "win_rate": "72%", "trades_24h": 3},
    ]
    
    for strat in strategies:
        with st.expander(f"{strat['name']} - {strat['status']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Win Rate", strat['win_rate'])
            with col2:
                st.metric("Trades (24h)", strat['trades_24h'])
            with col3:
                st.button("⚙️ Configurar", key=f"config_{strat['name']}", disabled=True)
