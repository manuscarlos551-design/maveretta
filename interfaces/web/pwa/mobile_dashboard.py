
"""
Mobile Dashboard - PWA optimized for mobile devices
"""

import streamlit as st
from typing import Dict, Any, List
import asyncio

# Configure page for mobile
st.set_page_config(
    page_title="Maveretta Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Mobile-optimized CSS
st.markdown("""
<style>
    /* Mobile-first responsive design */
    @media (max-width: 768px) {
        .main > div {
            padding: 1rem 0.5rem;
        }
        
        .stButton button {
            width: 100%;
            padding: 1rem;
            font-size: 1.1rem;
            margin: 0.5rem 0;
        }
        
        .metric-card {
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 8px;
            background: #1a1a2e;
            border: 1px solid #00d4ff;
        }
        
        .emergency-btn {
            background: #ff4444 !important;
            color: white !important;
            font-weight: bold;
        }
        
        .action-btn {
            background: #00d4ff;
            color: #1a1a2e;
            border: none;
            padding: 0.8rem;
            border-radius: 8px;
            font-size: 1rem;
            margin: 0.3rem 0;
            width: 100%;
        }
    }
    
    /* Touch-friendly */
    button, a {
        -webkit-tap-highlight-color: rgba(0, 212, 255, 0.3);
    }
    
    /* Hide desktop elements on mobile */
    @media (max-width: 768px) {
        .desktop-only {
            display: none !important;
        }
    }
</style>
""", unsafe_allow_html=True)


class MobileDashboard:
    """Mobile-optimized dashboard"""
    
    def __init__(self):
        self.api_url = "http://localhost:8000"
    
    async def get_status(self) -> Dict[str, Any]:
        """Get bot status"""
        # Placeholder - integrate with actual API
        return {
            'running': True,
            'total_pnl': 1250.50,
            'open_positions': 3,
            'win_rate': 0.65
        }
    
    async def emergency_stop(self):
        """Emergency stop all trading"""
        # Placeholder
        st.warning("🛑 EMERGENCY STOP ATIVADO")
        await asyncio.sleep(1)
        st.success("✅ Todas as operações pausadas")
    
    async def close_position(self, position_id: str):
        """Close specific position"""
        st.info(f"Fechando posição {position_id}...")
        await asyncio.sleep(0.5)
        st.success(f"✅ Posição {position_id} fechada")
    
    def render_quick_actions(self):
        """Render quick action buttons"""
        st.markdown("### ⚡ Ações Rápidas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🛑 PARAR TUDO", key="emergency", use_container_width=True):
                asyncio.run(self.emergency_stop())
        
        with col2:
            if st.button("📊 Ver Posições", key="positions", use_container_width=True):
                st.session_state['view'] = 'positions'
    
    def render_metrics(self, status: Dict[str, Any]):
        """Render key metrics"""
        st.markdown("### 📈 Resumo")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h4>💰 PnL</h4>
                <h2>${status['total_pnl']:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h4>📊 Posições</h4>
                <h2>{status['open_positions']}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h4>🎯 Win Rate</h4>
                <h2>{status['win_rate']:.1%}</h2>
            </div>
            """, unsafe_allow_html=True)
    
    def render_positions(self):
        """Render open positions"""
        st.markdown("### 📊 Posições Abertas")
        
        # Mock positions
        positions = [
            {'id': 'pos1', 'symbol': 'BTC/USDT', 'pnl': 150.25, 'side': 'long'},
            {'id': 'pos2', 'symbol': 'ETH/USDT', 'pnl': -50.10, 'side': 'short'},
            {'id': 'pos3', 'symbol': 'SOL/USDT', 'pnl': 75.00, 'side': 'long'}
        ]
        
        for pos in positions:
            pnl_color = "🟢" if pos['pnl'] > 0 else "🔴"
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                **{pos['symbol']}** ({pos['side'].upper()})  
                {pnl_color} ${pos['pnl']:,.2f}
                """)
            
            with col2:
                if st.button("❌", key=f"close_{pos['id']}", use_container_width=True):
                    asyncio.run(self.close_position(pos['id']))
            
            st.divider()
    
    def render(self):
        """Main render method"""
        # Header
        st.title("🤖 Maveretta Bot")
        
        # Get status
        status = asyncio.run(self.get_status())
        
        # Status indicator
        status_icon = "🟢" if status['running'] else "🔴"
        st.markdown(f"### Status: {status_icon} {'Ativo' if status['running'] else 'Parado'}")
        
        # Quick actions
        self.render_quick_actions()
        
        st.divider()
        
        # Metrics
        self.render_metrics(status)
        
        st.divider()
        
        # View switcher
        view = st.session_state.get('view', 'home')
        
        if view == 'positions':
            self.render_positions()
            if st.button("⬅️ Voltar", use_container_width=True):
                st.session_state['view'] = 'home'


# Run app
if __name__ == "__main__":
    dashboard = MobileDashboard()
    dashboard.render()
