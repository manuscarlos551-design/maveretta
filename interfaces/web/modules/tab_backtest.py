"""Aba: Backtests."""
import streamlit as st

def render():
    """Renderiza a aba Backtests."""
    st.markdown('<div class="section-header">🔬 Backtests</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")
    
    # Placeholder para backtests
    st.markdown("""
    ### 📈 Features Planejadas:
    
    - **Executar Backtest**: Interface para configurar e executar backtests
    - **Histórico**: Lista de backtests executados
    - **Resultados**: Visualização detalhada de resultados
    - **Comparação**: Comparar múltiplos backtests
    - **Métricas**: Sharpe Ratio, Max Drawdown, Win Rate, etc
    - **Export**: Exportar resultados para análise externa
    """)
    
    st.markdown("---")
    
    # Backtest configurator placeholder
    st.subheader("⚙️ Configurar Novo Backtest")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.date_input("Data Início", key="backtest_start_date")
        st.selectbox("Símbolo", ["BTC/USDT", "ETH/USDT", "BNB/USDT"], key="backtest_symbol")
        st.number_input("Capital Inicial (USD)", value=1000, key="backtest_capital")
    
    with col2:
        st.date_input("Data Fim", key="backtest_end_date")
        st.selectbox("Estratégia", ["AI Multi-Agent", "Scalping", "Tendência"], key="backtest_strategy")
        st.number_input("Risco por Trade (%)", value=2.0, key="backtest_risk")
    
    if st.button("🚀 Executar Backtest", key="run_backtest", use_container_width=True, type="primary"):
        st.info("🚧 Funcionalidade em desenvolvimento")
