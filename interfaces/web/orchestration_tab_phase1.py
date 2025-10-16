# interfaces/web/orchestration_tab_phase1.py
"""
Agent Orchestration Tab - Phase 1
Minimal UI for agent management: list, start/stop, set mode
"""

import streamlit as st
import requests
import time
from datetime import datetime
from typing import Dict, Any, List

# Backend URL
BACKEND_URL = "http://localhost:9200"


def format_timestamp(ts: float) -> str:
    """Format unix timestamp to readable string"""
    if not ts or ts == 0:
        return "Never"
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Invalid"


def get_status_emoji(status: str) -> str:
    """Get emoji for agent status"""
    if status == "running":
        return "🟢"
    return "🔴"


def get_mode_color(mode: str) -> str:
    """Get color for mode badge"""
    colors = {
        "shadow": "🔵",
        "paper": "🟡", 
        "live": "🔴"
    }
    return colors.get(mode, "⚪")


def fetch_agents() -> List[Dict[str, Any]]:
    """Fetch agents from orchestration API"""
    try:
        response = requests.get(f"{BACKEND_URL}/orchestration/agents", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("data"):
                return list(data["data"].values())
        return []
    except Exception as e:
        st.error(f"Error fetching agents: {e}")
        return []


def start_agent(agent_id: str) -> bool:
    """Start an agent"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/orchestration/agents/{agent_id}/start",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("ok", False)
        return False
    except Exception as e:
        st.error(f"Error starting agent: {e}")
        return False


def stop_agent(agent_id: str) -> bool:
    """Stop an agent"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/orchestration/agents/{agent_id}/stop",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("ok", False)
        return False
    except Exception as e:
        st.error(f"Error stopping agent: {e}")
        return False


def set_agent_mode(agent_id: str, mode: str) -> bool:
    """Set agent execution mode"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/orchestration/agents/{agent_id}/mode",
            json={"mode": mode},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("ok", False)
        return False
    except Exception as e:
        st.error(f"Error setting mode: {e}")
        return False


def render_orchestration_tab():
    """Render the orchestration tab (Phase 1)"""
    
    st.title("🎯 Agent Orchestration - Phase 1")
    st.markdown("**Shadow Mode Only** - State management without execution")
    
    # Add refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    with col2:
        auto_refresh = st.checkbox("Auto-refresh", value=False)
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(5)
        st.rerun()
    
    st.divider()
    
    # Fetch agents
    agents = fetch_agents()
    
    if not agents:
        st.warning("⚠️ No agents configured. Add YAML files to `/app/config/agents/`")
        st.info("**Phase 1**: Only agents with valid API keys will be loaded.")
        return
    
    # Show agent count
    st.metric("Total Agents", len(agents))
    
    st.divider()
    
    # Agent table
    st.subheader("📋 Agent List")
    
    for agent in agents:
        agent_id = agent.get("agent_id", "unknown")
        status = agent.get("status", "stopped")
        mode = agent.get("mode", "shadow")
        provider = agent.get("provider", "unknown")
        model = agent.get("model", "unknown")
        last_tick = agent.get("last_tick", 0)
        tick_count = agent.get("tick_count", 0)
        role = agent.get("role", "")
        
        # Create expander for each agent
        with st.expander(
            f"{get_status_emoji(status)} **{agent_id}** | "
            f"{get_mode_color(mode)} {mode.upper()} | "
            f"Provider: {provider}",
            expanded=False
        ):
            # Agent details
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Details**")
                st.text(f"Status: {status}")
                st.text(f"Mode: {mode}")
                st.text(f"Provider: {provider}")
                st.text(f"Model: {model}")
            
            with col2:
                st.markdown("**Activity**")
                st.text(f"Tick count: {tick_count}")
                st.text(f"Last tick: {format_timestamp(last_tick)}")
                st.text(f"Role: {role}")
            
            with col3:
                st.markdown("**Config**")
                exchanges = agent.get("exchanges", [])
                symbols = agent.get("symbols", [])
                st.text(f"Exchanges: {', '.join(exchanges) if exchanges else 'None'}")
                st.text(f"Symbols: {', '.join(symbols[:2]) if symbols else 'None'}")
            
            st.divider()
            
            # Controls
            st.markdown("**Controls**")
            ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns(4)
            
            with ctrl_col1:
                if status == "stopped":
                    if st.button("▶️ Start", key=f"start_{agent_id}", use_container_width=True):
                        if start_agent(agent_id):
                            st.success(f"Started {agent_id}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Failed to start {agent_id}")
                else:
                    if st.button("⏸️ Stop", key=f"stop_{agent_id}", use_container_width=True):
                        if stop_agent(agent_id):
                            st.success(f"Stopped {agent_id}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Failed to stop {agent_id}")
            
            with ctrl_col2:
                # Mode selector
                mode_options = ["shadow", "paper", "live"]
                current_mode_idx = mode_options.index(mode) if mode in mode_options else 0
                
                new_mode = st.selectbox(
                    "Mode",
                    mode_options,
                    index=current_mode_idx,
                    key=f"mode_{agent_id}"
                )
                
                if new_mode != mode:
                    if set_agent_mode(agent_id, new_mode):
                        st.success(f"Mode changed to {new_mode}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to change mode")
            
            with ctrl_col3:
                st.markdown("**Phase 1 Note**")
                st.caption("Paper/Live modes accepted but not executed yet")
    
    # Footer info
    st.divider()
    st.markdown("---")
    st.caption("**Phase 1**: Shadow-only orchestration. No actual trading execution.")
    st.caption("Agents load configs from `/app/config/agents/*.yaml` and validate API keys.")


# Main entry point for the tab
def show():
    """Entry point for the orchestration tab"""
    render_orchestration_tab()


if __name__ == "__main__":
    # For testing standalone
    render_orchestration_tab()
