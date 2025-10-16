# interfaces/web/operacoes_tab_fase3.py
"""
Aba de Operações - FASE 3 Implementation
Lista e gerencia operações (trades) do sistema
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime


def render_operacoes_tab_fase3(api_client):
    """📈 Operações - Histórico de Trades (FASE 3)"""
    st.markdown('<div class="section-header">📈 Operações</div>', unsafe_allow_html=True)
    
    if not api_client.is_api_available():
        st.error("🚨 API INDISPONÍVEL")
        return
    
    # ========== RESUMO ESTATÍSTICO ==========
    st.markdown("### 📊 Visão Geral das Operações")
    
    try:
        stats = api_client.get("/v1/operations/stats/summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total de Operações",
                stats.get("total_operations", 0),
                delta=f"{stats.get('closed', 0)} fechadas"
            )
        
        with col2:
            st.metric(
                "Operações Abertas",
                stats.get("open", 0),
                delta="Em andamento"
            )
        
        with col3:
            total_pnl = stats.get("total_pnl", 0)
            st.metric(
                "P&L Total",
                f"${total_pnl:,.2f}",
                delta=f"Média: ${stats.get('avg_pnl', 0):.2f}"
            )
        
        with col4:
            win_rate = stats.get("win_rate", 0)
            st.metric(
                "Taxa de Sucesso",
                f"{win_rate:.1f}%",
                delta=f"{stats.get('winning_trades', 0)} wins"
            )
    
    except Exception as e:
        st.error(f"Erro ao carregar estatísticas: {e}")
    
    # ========== FILTROS ==========
    st.markdown("### 🔍 Filtrar Operações")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_status = st.selectbox(
            "Status",
            ["Todas", "Abertas", "Fechadas", "Canceladas"],
            help="Filtrar por status da operação"
        )
    
    with col2:
        filter_exchange = st.selectbox(
            "Exchange",
            ["Todas", "Binance", "KuCoin", "Bybit", "Coinbase", "OKX"]
        )
    
    with col3:
        filter_symbol = st.text_input(
            "Par",
            placeholder="Ex: BTC/USDT",
            help="Deixe vazio para ver todos"
        )
    
    with col4:
        limit = st.number_input(
            "Limite",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
            help="Número máximo de operações"
        )
    
    # ========== BUSCAR OPERAÇÕES ==========
    try:
        params = {"limit": limit}
        
        status_map = {
            "Todas": None,
            "Abertas": "open",
            "Fechadas": "closed",
            "Canceladas": "cancelled"
        }
        selected_status = status_map.get(filter_status)
        if selected_status:
            params["status"] = selected_status
        
        if filter_exchange != "Todas":
            params["exchange"] = filter_exchange.lower()
        
        if filter_symbol:
            params["symbol"] = filter_symbol.upper()
        
        operations = api_client.get("/v1/operations", params=params)
        
        if operations and len(operations) > 0:
            # Converter para DataFrame
            df = pd.DataFrame(operations)
            
            # Formatar colunas
            if "pnl" in df.columns:
                df["P&L USD"] = df["pnl"].apply(lambda x: f"${x:,.2f}" if x is not None else "–")
            else:
                df["P&L USD"] = "–"
            
            if "pnl_pct" in df.columns:
                df["P&L %"] = df["pnl_pct"].apply(lambda x: f"{x:.2f}%" if x is not None else "–")
            else:
                df["P&L %"] = "–"
            
            if "opened_at" in df.columns:
                try:
                    df["Abertura"] = pd.to_datetime(df["opened_at"]).dt.strftime("%Y-%m-%d %H:%M")
                except:
                    df["Abertura"] = df["opened_at"]
            else:
                df["Abertura"] = "–"
            
            if "closed_at" in df.columns:
                try:
                    df["Fechamento"] = pd.to_datetime(df["closed_at"]).dt.strftime("%Y-%m-%d %H:%M")
                except:
                    df["Fechamento"] = df["closed_at"]
            else:
                df["Fechamento"] = "–"
            
            # Renomear colunas para exibição
            df = df.rename(columns={
                "id": "ID",
                "symbol": "Par",
                "exchange": "Exchange",
                "side": "Lado",
                "status": "Status",
                "entry_price": "Preço Entrada",
                "exit_price": "Preço Saída",
                "quantity": "Qtd"
            })
            
            # Selecionar colunas para exibir
            display_columns = ["ID", "Par", "Exchange", "Lado", "Status", "Preço Entrada", "Preço Saída", "Qtd", "P&L USD", "P&L %", "Abertura", "Fechamento"]
            display_columns = [col for col in display_columns if col in df.columns]
            
            # Exibir tabela
            st.dataframe(
                df[display_columns],
                use_container_width=True,
                height=400,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="medium"),
                    "Par": st.column_config.TextColumn("Par", width="medium"),
                    "Exchange": st.column_config.TextColumn("Exchange", width="medium"),
                    "Lado": st.column_config.TextColumn("Lado", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Preço Entrada": st.column_config.NumberColumn("Preço Entrada", format="$%.2f", width="medium"),
                    "Preço Saída": st.column_config.NumberColumn("Preço Saída", format="$%.2f", width="medium"),
                    "Qtd": st.column_config.NumberColumn("Qtd", format="%.8f", width="medium"),
                    "Abertura": st.column_config.TextColumn("Abertura", width="large"),
                    "Fechamento": st.column_config.TextColumn("Fechamento", width="large"),
                }
            )
            
            # ========== AÇÕES SOBRE OPERAÇÕES ==========
            st.markdown("### 🎯 Ações")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Seletor de operação
                open_operations_df = df[df["Status"] == "open"]
                open_operations_ids = open_operations_df["ID"].tolist()
                
                if open_operations_ids:
                    selected_op_id = st.selectbox(
                        "Selecione uma operação aberta:",
                        open_operations_ids,
                        help="Escolha uma operação para forçar fechamento"
                    )
                    
                    if st.button("🚨 Forçar Fechamento", type="primary"):
                        try:
                            response = api_client.post(f"/v1/operations/{selected_op_id}/close")
                            if response.get("status") == "ok":
                                st.success("✅ Comando de fechamento enviado. Verifique o status da operação.")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.warning(response.get("message", "Resposta inesperada"))
                        except Exception as e:
                            st.error(f"❌ Erro ao fechar operação: {e}")
                else:
                    st.info("Nenhuma operação aberta no momento para forçar fechamento.")
            
            with col2:
                if st.button("🔄 Atualizar Lista", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
        
        else:
            st.info("📭 Nenhuma operação encontrada com os filtros selecionados")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar operações: {e}")
