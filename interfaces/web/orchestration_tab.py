# interfaces/web/orchestration_tab.py
"""
Aba Orquestração Completa - Layout Oficial G1|Centro|G2|Footer
Implementa a interface avançada de orquestração conforme especificações
"""

import streamlit as st
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import api_client
import requests
import json as json_lib

def safe_get(data, key, default=None):
    """Safely get value from dict/list"""
    if isinstance(data, dict):
        return data.get(key, default)
    elif isinstance(data, list) and isinstance(key, int) and 0 <= key < len(data):
        return data[key]
    return default

def fmt_money(v, sym: str = "") -> str:
    """Format money values"""
    try:
        if v is None:
            return "–"
        val = float(v)
        if abs(val) >= 1e6:
            return f"{sym}{val/1e6:.1f}M"
        elif abs(val) >= 1e3:
            return f"{sym}{val/1e3:.1f}k"
        else:
            return f"{sym}{val:.2f}"
    except (ValueError, TypeError):
        return str(v) if v is not None else "–"

def fmt_pct(value, default="–"):
    """Formatar percentuais seguros"""
    if value is None:
        return default
    try:
        return f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return default

def map_ia_status(status: str) -> str:
    """Mapeia status das IAs para semáforo"""
    if not status:
        return "🔴"
    
    status_upper = str(status).upper()
    
    if status_upper == "GREEN":
        return "🟢"
    elif status_upper in ["AMBER", "YELLOW", "PENDING", "STANDBY"]:
        return "🟡"
    else:
        return "🔴"

def map_slot_status(status: str) -> str:
    """Mapeia status dos slots para semáforo"""
    if not status:
        return "🔴"
    
    status_upper = str(status).upper()
    
    if status_upper in ["ACTIVE", "RUNNING", "ON", "GREEN"]:
        return "🟢"
    elif status_upper in ["PAUSED", "PENDING", "AMBER"]:
        return "🟡"
    else:
        return "🔴"

def _is_odd_slot(slot_id: str) -> bool:
    """Detecta se slot é ímpar baseado no ID"""
    try:
        import re
        numbers = re.findall(r'\d+', str(slot_id))
        if numbers:
            return int(numbers[0]) % 2 == 1
        return hash(str(slot_id)) % 2 == 1
    except:
        return True

def get_avatar_path(avatar_number: int) -> str:
    """Retorna path do avatar com fallback automático"""
    from pathlib import Path
    
    avatar_path = f"/interfaces/web/static/avatares/avatar{avatar_number}.png"
    full_path = Path(__file__).parent / "static" / "avatares" / f"avatar{avatar_number}.png"
    
    if full_path.exists():
        return avatar_path
    return None

def render_avatar_with_fallback(avatar_number: int, size: int = 60) -> str:
    """Renderiza avatar com fallback automático para placeholder"""
    avatar_path = get_avatar_path(avatar_number)
    
    if avatar_path:
        return f"""
        <div style="width: {size}px; height: {size}px; border-radius: 50%; overflow: hidden; border: 2px solid var(--border);">
            <img src="{avatar_path}" style="width: 100%; height: 100%; object-fit: cover;" />
        </div>
        """
    else:
        return f"""
        <div style="width: {size}px; height: {size}px; border-radius: 50%; background: var(--panel2); 
                    border: 2px solid var(--border); display: flex; align-items: center; justify-content: center;">
            <span style="font-size: {size//3}px;">🤖</span>
        </div>
        """

def render_strategy_badge(strategy: str) -> str:
    """Renderiza badge da estratégia ativa"""
    if not strategy or strategy == "N/A":
        return '<span style="background: var(--muted); color: var(--bg); padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">—</span>'
    
    # Cores por tipo de estratégia
    color_map = {
        "scalp": "#ff6b35",
        "momentum": "#4ecdc4", 
        "mean_reversion": "#45b7d1",
        "breakout": "#f9ca24",
        "trend_following": "#6c5ce7",
        "arbitrage": "#a29bfe",
        "grid": "#fd79a8",
        "pairs_trading": "#fdcb6e",
        "ml_predictive": "#e17055",
        "volatility_breakout": "#d63031",
        "carry": "#00b894",
        "liquidity_sweep": "#e84393",
        "orderbook_imbalance": "#0984e3",
        "news_sentiment": "#fd79a8"
    }
    
    color = color_map.get(strategy.lower(), "#74b9ff")
    display_name = strategy.replace("_", " ").title()
    
    return f'''
    <span style="background: {color}; color: white; padding: 3px 8px; border-radius: 12px; 
                 font-size: 0.75rem; font-weight: 600; white-space: nowrap;">
        {display_name}
    </span>
    '''


def render_consensus_timeline():
    """Render real-time consensus timeline with SSE fallback to polling - Phase 4"""
    st.subheader("📡 Consensus Timeline (Real-Time)")
    
    # Try to get recent consensus rounds
    try:
        api_url = os.getenv('API_URL', 'http://ai-gateway:8080')
        # Use polling as fallback (SSE not fully implemented in Streamlit without custom components)
        response = requests.get(
            f"{api_url}/v1/orchestration/consensus/recent",
            params={"limit": 10},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            rounds = data.get('data', {}).get('rounds', [])
            
            if rounds:
                for round_data in rounds[:5]:  # Show last 5
                    consensus_id = round_data.get('consensus_id', 'unknown')
                    symbol = round_data.get('symbols', ['UNKNOWN'])[0] if round_data.get('symbols') else 'UNKNOWN'
                    approved = round_data.get('approved', False)
                    confidence = round_data.get('confidence_avg', 0)
                    action = round_data.get('action', 'hold')
                    
                    # Create expander for each consensus
                    status_icon = "✅" if approved else "❌"
                    with st.expander(f"{status_icon} {symbol} - {action.upper()} (conf: {confidence:.2f})", expanded=False):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Consensus ID:** `{consensus_id[:8]}...`")
                            st.write(f"**Symbol:** {symbol}")
                            st.write(f"**Action:** {action}")
                        with col2:
                            st.write(f"**Confidence:** {confidence:.2%}")
                            st.write(f"**Approved:** {'Yes' if approved else 'No'}")
                            st.write(f"**Participants:** {len(round_data.get('participants', []))}")
                        
                        # Show proposals
                        proposals = round_data.get('proposals', [])
                        if proposals:
                            st.write("**Proposals:**")
                            for prop in proposals:
                                agent_id = prop.get('agent_id', 'unknown')
                                prop_action = prop.get('action', 'unknown')
                                prop_conf = prop.get('confidence', 0)
                                rationale = prop.get('rationale', 'No rationale')
                                
                                st.markdown(f"""
                                <div style="background: #1e1e1e; padding: 8px; border-radius: 4px; margin: 4px 0;">
                                    <strong>🤖 {agent_id}</strong>: {prop_action} (conf: {prop_conf:.2f})<br>
                                    <em style="color: #888;">{rationale}</em>
                                </div>
                                """, unsafe_allow_html=True)
            else:
                st.info("No recent consensus rounds")
        else:
            st.warning(f"Failed to fetch consensus rounds: {response.status_code}")
    except Exception as e:
        st.error(f"Error fetching consensus timeline: {e}")


def render_orchestration_tab():
    """🎼 Aba Orquestração Completa - Layout Oficial"""
    
    if not api_client.is_api_available():
        st.error("🚨 API INDISPONÍVEL - Sistema não pode ser monitorado")
        return
    
    # ========== CARREGA DADOS REAIS ==========
    try:
        # Usa os novos endpoints estendidos se disponíveis
        if hasattr(api_client, 'get_orchestration_state_extended'):
            state = api_client.get_orchestration_state_extended()
            ias_health = api_client.get_ias_health_extended()
            ias = ias_health.get("ias", [])
        else:
            # Fallback para endpoints antigos
            state = api_client.get_orchestration_state() 
            ias = api_client.get_ia_health()
            
        # Estratégias disponíveis
        if hasattr(api_client, 'list_strategies'):
            strategies_data = api_client.list_strategies()
        else:
            strategies_data = []
            
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return
    
    # ========== DETERMINA LÍDER ==========
    leader_id = safe_get(state, "leader_id")
    leader_ia = None
    
    if leader_id:
        leader_ia = next((ia for ia in ias if safe_get(ia, "id") == leader_id), None)
    
    if not leader_ia:
        # Fallback: primeira IA GREEN ou primeira disponível
        leader_ia = next((ia for ia in ias if safe_get(ia, "status") == "GREEN"), None)
        if not leader_ia and ias:
            leader_ia = ias[0]
    
    # ========== DISTRIBUI IAs PARA G1 e G2 ==========
    available_ias = [ia for ia in ias if ia != leader_ia] if leader_ia else ias[:]
    
    g1_ias = [ia for ia in available_ias if safe_get(ia, "group") == "G1"][:3]
    g2_ias = [ia for ia in available_ias if safe_get(ia, "group") == "G2"][:3]
    
    # Se não tiver grupos definidos, distribui sequencialmente
    if not g1_ias and not g2_ias:
        g1_ias = available_ias[:3]
        g2_ias = available_ias[3:6]
    
    # ========== SEPARA SLOTS ÍMPARES E PARES ==========
    slots = safe_get(state, "slots", [])
    odd_slots = [slot for slot in slots if _is_odd_slot(safe_get(slot, "id", ""))]
    even_slots = [slot for slot in slots if not _is_odd_slot(safe_get(slot, "id", ""))]
    
    # ========== LAYOUT PRINCIPAL: G1 | CENTRO | G2 ==========
    st.markdown('<div class="section-header">🎼 Estado da Orquestração</div>', unsafe_allow_html=True)
    
    col_g1, col_centro, col_g2 = st.columns([2.5, 5, 2.5])
    
    # ===== COLUNA G1 (ESQUERDA) =====
    with col_g1:
        st.markdown("**🤖 Grupo G1 (Ímpares)**")
        
        if g1_ias:
            for i, ia in enumerate(g1_ias):
                ia_id = safe_get(ia, "id", "N/A")
                ia_name = safe_get(ia, "name", ia_id.split("_")[-1] if "_" in ia_id else ia_id)
                ia_status = safe_get(ia, "status", "RED")
                latency_ms = safe_get(ia, "latency_ms", 0)
                decisions_1h = safe_get(ia, "decisions_last_1h", 0)
                confidence = safe_get(ia, "avg_confidence", 0)
                
                semaforo = map_ia_status(ia_status)
                avatar_html = render_avatar_with_fallback(i + 1, 45)
                
                st.markdown(f"""
                <div class="metric-card" style="text-align: center; padding: 0.75rem; margin-bottom: 0.5rem;">
                    {avatar_html}
                    <div style="margin-top: 0.5rem;">
                        <div style="font-size: 0.9rem; font-weight: bold; color: var(--text);">{ia_name}</div>
                        <div style="font-size: 1.5rem; margin: 0.25rem 0;">{semaforo}</div>
                        <div style="font-size: 0.7rem; color: var(--muted); line-height: 1.2;">
                            Latência: {latency_ms}ms<br>
                            Decisões/h: {decisions_1h}<br>
                            Confiança: {confidence:.1f}%
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("🤖 Sem IAs G1 disponíveis")
    
    # ===== COLUNA CENTRO (LÍDER + SLOTS) =====
    with col_centro:
        # === LÍDER ===
        st.markdown("**👑 Líder da Orquestração**")
        
        if leader_ia:
            leader_name = safe_get(leader_ia, "name", safe_get(leader_ia, "id", "Líder"))
            leader_status = safe_get(leader_ia, "status", "RED")
            leader_decisions = safe_get(leader_ia, "decisions_last_1h", 0)
            leader_confidence = safe_get(leader_ia, "avg_confidence", 0)
            leader_semaforo = map_ia_status(leader_status)
            leader_avatar_html = render_avatar_with_fallback(4, 50)
            
            st.markdown(f"""
            <div class="metric-card-success" style="text-align: center; padding: 1rem; margin-bottom: 1rem;">
                {leader_avatar_html}
                <div style="margin-top: 0.5rem;">
                    <div style="font-size: 1rem; font-weight: bold; color: var(--text);">{leader_name}</div>
                    <div style="font-size: 1.8rem; margin: 0.25rem 0;">{leader_semaforo}</div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">
                        Decisões/h: {leader_decisions} | Confiança: {leader_confidence:.1f}%
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card-warning" style="text-align: center; padding: 1rem; margin-bottom: 1rem;">
                {render_avatar_with_fallback(4, 50)}
                <div style="margin-top: 0.5rem;">
                    <div style="font-size: 1rem; font-weight: bold; color: var(--text);">Sem Líder Ativo</div>
                    <div style="font-size: 1.8rem;">🔴</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # === SLOTS ÍMPARES E PARES ===
        st.markdown("**🎰 Slots de Trading**")
        
        col_impares, col_pares = st.columns(2)
        
        # SLOTS ÍMPARES (G1)
        with col_impares:
            st.markdown("*Slots Ímpares (G1)*")
            if odd_slots:
                for slot in odd_slots:
                    slot_id = safe_get(slot, "id", "N/A")
                    slot_status = safe_get(slot, "status", "UNKNOWN")
                    strategy_name = safe_get(slot, "strategy", "N/A")
                    strategy_mode = safe_get(slot, "strategy_mode", "auto")
                    
                    status_icon = map_slot_status(slot_status)
                    strategy_badge = render_strategy_badge(strategy_name)
                    
                    # Controles de estratégia
                    with st.container():
                        col_info, col_control = st.columns([2, 1])
                        
                        with col_info:
                            st.markdown(f"""
                            <div style="padding: 0.5rem; margin: 0.3rem 0; background: var(--panel); 
                                        border-radius: 8px; border-left: 3px solid var(--accent);">
                                <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
                                    {status_icon} <strong style="margin-left: 0.5rem;">{slot_id}</strong>
                                </div>
                                <div style="margin: 0.25rem 0;">
                                    {strategy_badge}
                                    <span style="margin-left: 0.5rem; font-size: 0.7rem; color: var(--muted);">
                                        ({strategy_mode})
                                    </span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_control:
                            # Controle de modo
                            mode_key = f"mode_{slot_id}"
                            current_mode = st.selectbox(
                                "Modo",
                                ["Auto", "Manual"],
                                index=0 if strategy_mode == "auto" else 1,
                                key=mode_key,
                                label_visibility="collapsed"
                            )
                            
                            # Se modo manual, mostrar seletor de estratégia
                            if current_mode == "Manual":
                                strategy_options = ["momentum", "scalp", "mean_reversion", "grid", "breakout"]
                                strategy_key = f"strategy_{slot_id}"
                                selected_strategy = st.selectbox(
                                    "Estratégia",
                                    strategy_options,
                                    index=strategy_options.index(strategy_name) if strategy_name in strategy_options else 0,
                                    key=strategy_key,
                                    label_visibility="collapsed"
                                )
                                
                                # Botão para aplicar mudança
                                if st.button("💾", key=f"apply_{slot_id}", help="Aplicar estratégia"):
                                    try:
                                        if hasattr(api_client, 'set_slot_strategy'):
                                            result = api_client.set_slot_strategy(
                                                slot_id, "manual", selected_strategy, "UI manual selection"
                                            )
                                            if result.get("success"):
                                                st.success(f"✅ Estratégia {selected_strategy} aplicada ao slot {slot_id}")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ Erro: {result.get('error', 'Falha desconhecida')}")
                                        else:
                                            st.warning("⚠️ Função set_slot_strategy não disponível")
                                    except Exception as e:
                                        st.error(f"❌ Erro ao aplicar estratégia: {e}")
            else:
                st.info("📊 Nenhum slot ímpar configurado")
        
        # SLOTS PARES (G2)
        with col_pares:
            st.markdown("*Slots Pares (G2)*")
            if even_slots:
                for slot in even_slots:
                    slot_id = safe_get(slot, "id", "N/A")
                    slot_status = safe_get(slot, "status", "UNKNOWN")
                    strategy_name = safe_get(slot, "strategy", "N/A")
                    strategy_mode = safe_get(slot, "strategy_mode", "auto")
                    
                    status_icon = map_slot_status(slot_status)
                    strategy_badge = render_strategy_badge(strategy_name)
                    
                    # Controles de estratégia (mesmo padrão dos ímpares)
                    with st.container():
                        col_info, col_control = st.columns([2, 1])
                        
                        with col_info:
                            st.markdown(f"""
                            <div style="padding: 0.5rem; margin: 0.3rem 0; background: var(--panel); 
                                        border-radius: 8px; border-left: 3px solid var(--green);">
                                <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
                                    {status_icon} <strong style="margin-left: 0.5rem;">{slot_id}</strong>
                                </div>
                                <div style="margin: 0.25rem 0;">
                                    {strategy_badge}
                                    <span style="margin-left: 0.5rem; font-size: 0.7rem; color: var(--muted);">
                                        ({strategy_mode})
                                    </span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_control:
                            # Controles similares aos slots ímpares
                            mode_key = f"mode_{slot_id}_even"
                            current_mode = st.selectbox(
                                "Modo",
                                ["Auto", "Manual"],
                                index=0 if strategy_mode == "auto" else 1,
                                key=mode_key,
                                label_visibility="collapsed"
                            )
                            
                            if current_mode == "Manual":
                                strategy_options = ["trend_following", "ml_predictive", "pairs_trading", "carry", "arbitrage"]
                                strategy_key = f"strategy_{slot_id}_even"
                                selected_strategy = st.selectbox(
                                    "Estratégia",
                                    strategy_options,
                                    index=strategy_options.index(strategy_name) if strategy_name in strategy_options else 0,
                                    key=strategy_key,
                                    label_visibility="collapsed"
                                )
                                
                                if st.button("💾", key=f"apply_{slot_id}_even", help="Aplicar estratégia"):
                                    try:
                                        if hasattr(api_client, 'set_slot_strategy'):
                                            result = api_client.set_slot_strategy(
                                                slot_id, "manual", selected_strategy, "UI manual selection"
                                            )
                                            if result.get("success"):
                                                st.success(f"✅ Estratégia {selected_strategy} aplicada ao slot {slot_id}")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ Erro: {result.get('error', 'Falha desconhecida')}")
                                        else:
                                            st.warning("⚠️ Função set_slot_strategy não disponível")
                                    except Exception as e:
                                        st.error(f"❌ Erro ao aplicar estratégia: {e}")
            else:
                st.info("📊 Nenhum slot par configurado")
    
    # ===== COLUNA G2 (DIREITA) =====
    with col_g2:
        st.markdown("**🤖 Grupo G2 (Pares)**")
        
        if g2_ias:
            for i, ia in enumerate(g2_ias):
                ia_id = safe_get(ia, "id", "N/A")
                ia_name = safe_get(ia, "name", ia_id.split("_")[-1] if "_" in ia_id else ia_id)
                ia_status = safe_get(ia, "status", "RED")
                latency_ms = safe_get(ia, "latency_ms", 0)
                decisions_1h = safe_get(ia, "decisions_last_1h", 0)
                confidence = safe_get(ia, "avg_confidence", 0)
                
                semaforo = map_ia_status(ia_status)
                avatar_html = render_avatar_with_fallback(i + 5, 45)  # avatars 5, 6, 7
                
                st.markdown(f"""
                <div class="metric-card" style="text-align: center; padding: 0.75rem; margin-bottom: 0.5rem;">
                    {avatar_html}
                    <div style="margin-top: 0.5rem;">
                        <div style="font-size: 0.9rem; font-weight: bold; color: var(--text);">{ia_name}</div>
                        <div style="font-size: 1.5rem; margin: 0.25rem 0;">{semaforo}</div>
                        <div style="font-size: 0.7rem; color: var(--muted); line-height: 1.2;">
                            Latência: {latency_ms}ms<br>
                            Decisões/h: {decisions_1h}<br>
                            Confiança: {confidence:.1f}%
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("🤖 Sem IAs G2 disponíveis")
    
    # ========== RODAPÉ: TABELAS DENSAS (ÍMPAR | PAR) ==========
    st.markdown("---")
    st.markdown("### 📊 Resumo Detalhado dos Slots")
    
    col_impares_table, col_pares_table = st.columns(2)
    
    # TABELA SLOTS ÍMPARES
    with col_impares_table:
        st.markdown("**📈 Slots Ímpares (G1)**")
        
        if odd_slots:
            for slot in odd_slots:
                slot_id = safe_get(slot, "id", "N/A")
                exchange = safe_get(slot, "exchange", "N/A")
                assigned_ia = safe_get(slot, "assigned_ia", "N/A")
                strategy_name = safe_get(slot, "strategy", "N/A")
                capital_base = safe_get(slot, "capital_base", 0)
                capital_current = safe_get(slot, "capital_current", 0)
                pnl = safe_get(slot, "pnl", 0)
                pnl_pct = safe_get(slot, "pnl_percentage", 0)
                cascade_target = safe_get(slot, "cascade_target", 10.0)
                next_slot = safe_get(slot, "next_slot", "—")
                ready = safe_get(slot, "status") == "ACTIVE"
                
                # Última ordem
                last_trade = safe_get(slot, "last_trade", {})
                if last_trade:
                    symbol = safe_get(last_trade, "symbol", "")
                    side = safe_get(last_trade, "side", "")
                    price = safe_get(last_trade, "price", 0)
                    last_order_text = f"{side} {symbol} @ {fmt_money(price)}" if symbol and side else "—"
                else:
                    last_order_text = "—"
                
                status_icon = map_slot_status(safe_get(slot, "status", "UNKNOWN"))
                ia_name = assigned_ia.split("_")[-1] if assigned_ia and "_" in assigned_ia else assigned_ia
                
                # Progress da meta de cascade
                cascade_progress = min(pnl_pct / cascade_target * 100, 100) if cascade_target > 0 else 0
                
                st.markdown(f"""
                <div class="metric-card-neutral" style="padding: 0.5rem; margin-bottom: 0.5rem; font-size: 0.8rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.25rem; line-height: 1.3;">
                        <div><strong>{status_icon} {slot_id}</strong></div>
                        <div>{exchange}</div>
                        <div>IA: {ia_name}</div>
                        <div>Estratégia: {strategy_name}</div>
                        <div>Cap.Base: {fmt_money(capital_base, '$')}</div>
                        <div>Cap.Atual: {fmt_money(capital_current, '$')}</div>
                        <div>P&L: {fmt_money(pnl, '$')}</div>
                        <div>P&L%: {fmt_pct(pnl_pct)}</div>
                        <div>Meta%: {cascade_target:.0f}% ({cascade_progress:.1f}%)</div>
                        <div>Próximo: {next_slot}</div>
                        <div>Ready: {'✅' if ready else '❌'}</div>
                        <div style="grid-column: 1 / -1; color: var(--muted);">
                            Últ.Ordem: {last_order_text}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📊 Nenhum slot ímpar configurado")
    
    # TABELA SLOTS PARES
    with col_pares_table:
        st.markdown("**📈 Slots Pares (G2)**")
        
        if even_slots:
            for slot in even_slots:
                slot_id = safe_get(slot, "id", "N/A")
                exchange = safe_get(slot, "exchange", "N/A")
                assigned_ia = safe_get(slot, "assigned_ia", "N/A")
                strategy_name = safe_get(slot, "strategy", "N/A")
                capital_base = safe_get(slot, "capital_base", 0)
                capital_current = safe_get(slot, "capital_current", 0)
                pnl = safe_get(slot, "pnl", 0)
                pnl_pct = safe_get(slot, "pnl_percentage", 0)
                cascade_target = safe_get(slot, "cascade_target", 10.0)
                next_slot = safe_get(slot, "next_slot", "—")
                ready = safe_get(slot, "status") == "ACTIVE"
                
                # Última ordem
                last_trade = safe_get(slot, "last_trade", {})
                if last_trade:
                    symbol = safe_get(last_trade, "symbol", "")
                    side = safe_get(last_trade, "side", "")
                    price = safe_get(last_trade, "price", 0)
                    last_order_text = f"{side} {symbol} @ {fmt_money(price)}" if symbol and side else "—"
                else:
                    last_order_text = "—"
                
                status_icon = map_slot_status(safe_get(slot, "status", "UNKNOWN"))
                ia_name = assigned_ia.split("_")[-1] if assigned_ia and "_" in assigned_ia else assigned_ia
                
                # Progress da meta de cascade
                cascade_progress = min(pnl_pct / cascade_target * 100, 100) if cascade_target > 0 else 0
                
                st.markdown(f"""
                <div class="metric-card-neutral" style="padding: 0.5rem; margin-bottom: 0.5rem; font-size: 0.8rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.25rem; line-height: 1.3;">
                        <div><strong>{status_icon} {slot_id}</strong></div>
                        <div>{exchange}</div>
                        <div>IA: {ia_name}</div>
                        <div>Estratégia: {strategy_name}</div>
                        <div>Cap.Base: {fmt_money(capital_base, '$')}</div>
                        <div>Cap.Atual: {fmt_money(capital_current, '$')}</div>
                        <div>P&L: {fmt_money(pnl, '$')}</div>
                        <div>P&L%: {fmt_pct(pnl_pct)}</div>
                        <div>Meta%: {cascade_target:.0f}% ({cascade_progress:.1f}%)</div>
                        <div>Próximo: {next_slot}</div>
                        <div>Ready: {'✅' if ready else '❌'}</div>
                        <div style="grid-column: 1 / -1; color: var(--muted);">
                            Últ.Ordem: {last_order_text}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📊 Nenhum slot par configurado")
    
    # ========== SEÇÃO CONSENSO (PHASE 3) ==========
    st.markdown("---")
    st.markdown("### 🤝 Rodadas de Consenso")
    
    col_consensus_action, col_consensus_info = st.columns([1, 3])
    
    with col_consensus_action:
        if st.button("🔄 Forçar Rodada de Consenso", key="force_consensus", use_container_width=True):
            try:
                import requests
                backend_url = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:9200')
                response = requests.post(f"{backend_url}/api/orchestration/consensus/force?symbol=BTCUSDT", timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        data = result.get('data', {})
                        st.success(f"✅ Consenso {'APROVADO' if data.get('approved') else 'REJEITADO'}: {data.get('action', 'N/A')}")
                        st.rerun()
                    else:
                        st.error(f"❌ Erro: {result.get('error', 'Desconhecido')}")
                else:
                    st.error(f"❌ Erro HTTP {response.status_code}")
            except Exception as e:
                st.error(f"❌ Erro ao forçar consenso: {e}")
    
    with col_consensus_info:
        st.info("💡 Força uma rodada de consenso entre agentes ativos para o símbolo BTCUSDT")
    
    # Timeline de consensos recentes - Phase 4
    st.markdown("---")
    render_consensus_timeline()
    try:
        import requests
        backend_url = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:9200')
        response = requests.get(f"{backend_url}/api/orchestration/consensus/rounds?limit=10", timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                rounds = result.get('data', {}).get('rounds', [])
                
                if rounds:
                    st.markdown("**📊 Últimas Rodadas de Consenso:**")
                    
                    for round_data in rounds[:5]:
                        symbol = round_data.get('symbol', 'N/A')
                        approved = round_data.get('approved', False)
                        action = round_data.get('action', 'hold')
                        confidence_avg = round_data.get('confidence_avg', 0)
                        reason = round_data.get('reason', '')
                        timestamp = round_data.get('timestamp', '')
                        
                        status_icon = "✅" if approved else "❌"
                        bg_color = "var(--success)" if approved else "var(--danger)"
                        
                        st.markdown(f"""
                        <div style="padding: 0.75rem; margin: 0.5rem 0; background: var(--panel); 
                                    border-radius: 8px; border-left: 4px solid {bg_color};">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                <div style="font-weight: bold; color: var(--text);">
                                    {status_icon} {symbol} - {action.upper()}
                                </div>
                                <div style="color: var(--muted); font-size: 0.8rem;">
                                    Conf: {confidence_avg:.2%}
                                </div>
                            </div>
                            <div style="color: var(--text-secondary); font-size: 0.85rem;">
                                {reason}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("📊 Nenhuma rodada de consenso registrada ainda")
    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar rodadas de consenso: {e}")
    
    # ========== SEÇÃO PAPER TRADING (PHASE 3) ==========
    st.markdown("---")
    st.markdown("### 📄 Execução Paper")
    
    try:
        import requests
        backend_url = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:9200')
        response = requests.get(f"{backend_url}/api/orchestration/paper/open", timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                paper_trades = result.get('data', {}).get('trades', [])
                
                if paper_trades:
                    st.markdown(f"**🔓 {len(paper_trades)} Paper Trade(s) Aberto(s):**")
                    
                    for trade in paper_trades:
                        paper_id = trade.get('paper_id', 'N/A')
                        symbol = trade.get('symbol', 'N/A')
                        action = trade.get('action', 'N/A')
                        entry_price = trade.get('entry_price', 0)
                        current_price = trade.get('current_price', 0)
                        unrealized_pnl = trade.get('unrealized_pnl', 0)
                        tp_pct = trade.get('tp_pct', 0)
                        sl_pct = trade.get('sl_pct', 0)
                        
                        pnl_color = "var(--success)" if unrealized_pnl >= 0 else "var(--danger)"
                        
                        col_trade_info, col_trade_action = st.columns([3, 1])
                        
                        with col_trade_info:
                            st.markdown(f"""
                            <div style="padding: 0.75rem; margin: 0.5rem 0; background: var(--panel); 
                                        border-radius: 8px; border-left: 4px solid var(--accent);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                    <div style="font-weight: bold; color: var(--text);">
                                        {symbol} - {action.upper()}
                                    </div>
                                    <div style="color: {pnl_color}; font-weight: bold;">
                                        PnL: ${unrealized_pnl:.2f}
                                    </div>
                                </div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem; font-size: 0.85rem; color: var(--text-secondary);">
                                    <div>Entrada: ${entry_price:.2f}</div>
                                    <div>Atual: ${current_price:.2f}</div>
                                    <div>TP: {tp_pct}% | SL: {sl_pct}%</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_trade_action:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("🔒 Encerrar", key=f"close_paper_{paper_id}", use_container_width=True):
                                try:
                                    close_response = requests.post(
                                        f"{backend_url}/api/orchestration/paper/close",
                                        json={"paper_id": paper_id, "close_price": current_price},
                                        timeout=5
                                    )
                                    
                                    if close_response.status_code == 200:
                                        close_result = close_response.json()
                                        if close_result.get('ok'):
                                            st.success(f"✅ Paper trade {paper_id[:8]}... encerrado!")
                                            st.rerun()
                                        else:
                                            st.error(f"❌ Erro: {close_result.get('error', 'Desconhecido')}")
                                    else:
                                        st.error(f"❌ Erro HTTP {close_response.status_code}")
                                except Exception as e:
                                    st.error(f"❌ Erro ao encerrar: {e}")
                else:
                    st.info("📄 Nenhum paper trade aberto no momento")
        else:
            st.warning(f"⚠️ Erro ao carregar paper trades: HTTP {response.status_code}")
    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar paper trades: {e}")
    
    # Links para Grafana
    st.markdown("---")
    st.markdown("### 📊 Painéis Grafana")
    
    col_grafana1, col_grafana2 = st.columns(2)
    
    with col_grafana1:
        st.markdown("""
        <a href="/grafana/d/agents-overview-phase3/agents-overview-phase-3" target="_blank" 
           style="display: block; padding: 1rem; background: var(--panel); border-radius: 8px; 
                  text-align: center; text-decoration: none; color: var(--text); font-weight: bold;">
            📈 Agents Overview
        </a>
        """, unsafe_allow_html=True)
    
    with col_grafana2:
        st.markdown("""
        <a href="/grafana/d/agent-drilldown-phase3/agent-drilldown-phase-3" target="_blank" 
           style="display: block; padding: 1rem; background: var(--panel); border-radius: 8px; 
                  text-align: center; text-decoration: none; color: var(--text); font-weight: bold;">
            🔍 Agent Drilldown
        </a>
        """, unsafe_allow_html=True)
    
    # ========== FEED DE DECISÕES ==========
    st.markdown("---")
    st.markdown("### 📋 Feed de Decisões das IAs")
    
    # Controles do feed
    col_feed_filters, col_feed_refresh = st.columns([4, 1])
    
    with col_feed_filters:
        col_slot_filter, col_ia_filter, col_limit = st.columns(3)
        
        with col_slot_filter:
            slot_filter = st.selectbox(
                "Filtrar por Slot",
                ["Todos"] + [slot["id"] for slot in slots],
                key="decisions_slot_filter"
            )
        
        with col_ia_filter:
            ia_filter = st.selectbox(
                "Filtrar por IA", 
                ["Todas"] + [ia["id"] for ia in ias],
                key="decisions_ia_filter"
            )
        
        with col_limit:
            limit = st.selectbox(
                "Mostrar",
                [20, 50, 100],
                key="decisions_limit"
            )
    
    with col_feed_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar Feed", key="refresh_decisions"):
            st.rerun()
    
    # Busca decisões
    try:
        if hasattr(api_client, 'get_decisions'):
            decisions_data = api_client.get_decisions(
                slot_id=slot_filter if slot_filter != "Todos" else None,
                ia_id=ia_filter if ia_filter != "Todas" else None,
                limit=limit
            )
            decisions = decisions_data.get("decisions", [])
        else:
            decisions = []
        
        if decisions:
            st.markdown(f"**Exibindo {len(decisions)} decisões mais recentes:**")
            
            # Container scrollável para as decisões
            with st.container():
                for i, decision in enumerate(decisions[:20]):  # Limita a 20 na UI
                    timestamp = decision.get("timestamp", 0)
                    dt = datetime.fromtimestamp(timestamp) if timestamp > 0 else datetime.now()
                    
                    ia_id = decision.get("ia_id", "N/A")
                    slot_id = decision.get("slot_id", "N/A")
                    result = decision.get("result", "unknown")
                    confidence = decision.get("confidence", 0)
                    latency_ms = decision.get("latency_ms", 0)
                    reason = decision.get("reason", "")
                    
                    # Cor baseada no resultado
                    result_colors = {
                        "approve": "#22c55e",
                        "reject": "#ef4444", 
                        "defer": "#f59e0b"
                    }
                    result_color = result_colors.get(result, "#6b7280")
                    
                    # Nome simplificado da IA
                    ia_name = ia_id.split("_")[-1] if "_" in ia_id else ia_id
                    
                    st.markdown(f"""
                    <div style="padding: 0.5rem; margin: 0.25rem 0; background: var(--panel); 
                                border-radius: 6px; border-left: 3px solid {result_color}; font-size: 0.85rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                            <div style="font-weight: bold; color: var(--text);">
                                {ia_name} → {slot_id}
                            </div>
                            <div style="color: var(--muted); font-size: 0.75rem;">
                                {dt.strftime("%H:%M:%S")}
                            </div>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="color: {result_color}; font-weight: bold; text-transform: uppercase;">
                                    {result}
                                </span>
                                <span style="margin-left: 0.5rem; color: var(--muted);">
                                    {confidence:.1f}% conf | {latency_ms}ms
                                </span>
                            </div>
                        </div>
                        <div style="margin-top: 0.25rem; color: var(--text-secondary); font-style: italic;">
                            {reason}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("📋 Nenhuma decisão disponível com os filtros selecionados")
            
    except Exception as e:
        st.error(f"❌ Erro ao carregar feed de decisões: {e}")