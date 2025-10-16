"""Aba: Auditoria."""
import streamlit as st

def render():
    """Renderiza a aba Auditoria."""
    st.markdown('<div class="section-header">📋 Auditoria</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")
    
    # Placeholder para futuras features
    st.markdown("""
    ### 📄 Features Planejadas:
    
    - **Histórico de Decisões**: Todas as decisões tomadas pelos agentes
    - **Rastro de Auditoria**: Log completo de ações no sistema
    - **Compliance**: Validação de regras de negocio
    - **Relatórios**: Geração de relatórios diários/semanais/mensais
    - **Export**: Exportação de dados para CSV/Excel
    """)
