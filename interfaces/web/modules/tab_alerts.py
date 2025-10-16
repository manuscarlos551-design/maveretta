"""Aba: Alertas do Sistema."""
import streamlit as st

def render():
    """Renderiza a aba Alertas."""
    st.markdown('<div class="section-header">🚨 Alertas</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")
    
    # Placeholder para alertas
    st.markdown("""
    ### 🔔 Features Planejadas:
    
    - **Alertas Ativos**: Lista de alertas em tempo real
    - **Histórico**: Histórico de alertas disparados
    - **Configuração**: Criar e editar regras de alerta
    - **Notificações**: Integração com Telegram/Discord/Slack/Email
    - **Severidade**: Filtro por nível de severidade (Info, Warning, Critical)
    """)
    
    # Mock alerts table
    st.subheader("📊 Alertas Recentes (Mock)")
    
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Sample data
    alerts_data = [
        {"Horário": (datetime.now() - timedelta(minutes=5)).strftime("%H:%M:%S"),
         "Tipo": "INFO", "Mensagem": "Sistema iniciado com sucesso"},
        {"Horário": (datetime.now() - timedelta(minutes=15)).strftime("%H:%M:%S"),
         "Tipo": "WARNING", "Mensagem": "Alta volatilidade detectada em BTC/USDT"},
        {"Horário": (datetime.now() - timedelta(minutes=30)).strftime("%H:%M:%S"),
         "Tipo": "INFO", "Mensagem": "Trade fechado com lucro de 2.5%"},
    ]
    
    df = pd.DataFrame(alerts_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
