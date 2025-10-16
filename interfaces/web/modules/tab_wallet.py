"""Aba: Carteira / Wallet."""
import streamlit as st

def render():
    """Renderiza a aba Carteira."""
    st.markdown('<div class="section-header">💰 Carteira</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")
    
    # Placeholder para wallet
    st.markdown("""
    ### 👛 Features Planejadas:
    
    - **Saldo Total**: Visualização consolidada de todos os saldos
    - **Por Exchange**: Saldo detalhado em cada exchange
    - **Por Moeda**: Distribuição de ativos
    - **Histórico**: Evolução do patrimônio ao longo do tempo
    - **Depósitos/Saques**: Histórico de movimentações
    - **DEX Wallet**: Integração com carteiras Web3 (MetaMask)
    """)
    
    st.markdown("---")
    
    # Mock wallet summary
    st.subheader("📊 Resumo da Carteira (Mock)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "💵 Saldo Total (USDT)",
            "$1,234.56",
            "+5.2%",
            help="Saldo total em todas as exchanges"
        )
    
    with col2:
        st.metric(
            "📈 Lucro (24h)",
            "$45.67",
            "+3.8%",
            help="Lucro nas últimas 24 horas"
        )
    
    with col3:
        st.metric(
            "🎯 ROI Total",
            "23.4%",
            help="Return on Investment desde o início"
        )
    
    st.markdown("---")
    
    # Distribution by exchange (mock)
    st.subheader("🏛️ Distribuição por Exchange")
    
    import pandas as pd
    
    exchange_data = [
        {"Exchange": "Binance", "Saldo (USDT)": "$450.00", "Alocação": "36.4%"},
        {"Exchange": "Bybit", "Saldo (USDT)": "$350.00", "Alocação": "28.3%"},
        {"Exchange": "KuCoin", "Saldo (USDT)": "$250.00", "Alocação": "20.3%"},
        {"Exchange": "OKX", "Saldo (USDT)": "$150.00", "Alocação": "12.2%"},
        {"Exchange": "Coinbase", "Saldo (USDT)": "$34.56", "Alocação": "2.8%"},
    ]
    
    df = pd.DataFrame(exchange_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
