"""
Registry of all AIs in the trading orchestration system.
NO automatic generation - only real data sources.
"""
import logging
from typing import List, Dict, Optional
from interfaces.web.core import IA, State, AVATAR_BINDING, TEAM_ROSTER

logger = logging.getLogger(__name__)

class IARegistry:
    """Central registry for all AI agents - only real data sources."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # NO automatic initialization - only load from real sources
    
    def get_all_ias(self) -> List[IA]:
        """Get all registered AIs from real data sources."""
        try:
            # TODO: Load from real database/service
            # This should connect to MongoDB IA collection or IA management service
            
            ias = []
            
            # Example: Load from MongoDB
            # ias = self._load_ias_from_mongodb()
            
            # Example: Load from IA management service
            # ias = self._load_ias_from_service()
            
            # Example: Check IA health from monitoring system
            # ias = self._load_ias_with_health_check()
            
            self.logger.debug(f"Loaded {len(ias)} IAs from real sources")
            return ias
            
        except Exception as e:
            self.logger.error(f"Failed to load IAs from real sources: {e}")
            return []
    
    def get_ia_by_id(self, ia_id: str) -> Optional[IA]:
        """Get specific IA by ID from real sources."""
        try:
            # TODO: Load specific IA from database
            # Should query real data source by ID
            
            # Example: Load from MongoDB by ID
            # ia = self._load_ia_from_mongodb(ia_id)
            
            self.logger.debug(f"Loaded IA {ia_id} from real sources")
            return None  # No real source available yet
            
        except Exception as e:
            self.logger.error(f"Failed to load IA {ia_id}: {e}")
            return None
    
    def get_ias_by_role(self, role: str) -> List[IA]:
        """Get AIs by role from real sources."""
        try:
            all_ias = self.get_all_ias()
            return [ia for ia in all_ias if ia.role == role]
        except Exception as e:
            self.logger.error(f"Failed to filter IAs by role {role}: {e}")
            return []
    
    def get_ias_by_provider(self, provider: str) -> List[IA]:
        """Get AIs by provider from real sources."""
        try:
            all_ias = self.get_all_ias()
            return [ia for ia in all_ias if ia.provider == provider]
        except Exception as e:
            self.logger.error(f"Failed to filter IAs by provider {provider}: {e}")
            return []
    
    def get_ias_by_group(self, group: str) -> List[IA]:
        """Get AIs by group from real sources."""
        try:
            # Only return IAs that actually exist in real sources
            all_ias = self.get_all_ias()
            group_ias = []
            
            if group == "L" and TEAM_ROSTER.get("LEADER"):
                leader_id = TEAM_ROSTER["LEADER"]["id"]
                group_ias.extend([ia for ia in all_ias if ia.id == leader_id])
            elif group == "G1" and TEAM_ROSTER.get("G1"):
                g1_ids = [config["id"] for config in TEAM_ROSTER["G1"]]
                group_ias.extend([ia for ia in all_ias if ia.id in g1_ids])
            elif group == "G2" and TEAM_ROSTER.get("G2"):
                g2_ids = [config["id"] for config in TEAM_ROSTER["G2"]]
                group_ias.extend([ia for ia in all_ias if ia.id in g2_ids])
            elif group == "DATA" and TEAM_ROSTER.get("DATA"):
                data_ids = [config["id"] for config in TEAM_ROSTER["DATA"]]
                group_ias.extend([ia for ia in all_ias if ia.id in data_ids])
            
            return group_ias
            
        except Exception as e:
            self.logger.error(f"Failed to get IAs by group {group}: {e}")
            return []
    
    def update_ia_state(self, ia_id: str, state: State, latency_ms: Optional[float] = None, uptime_pct: Optional[float] = None):
        """Update IA state and metrics in real data source."""
        try:
            # TODO: Update real database/service
            # Should persist changes to MongoDB or IA management service
            
            self.logger.info(f"Should update IA {ia_id}: state={state}, latency={latency_ms}ms, uptime={uptime_pct}% in real data source")
            
        except Exception as e:
            self.logger.error(f"Failed to update IA {ia_id}: {e}")
    
    def get_leader_ia(self) -> Optional[IA]:
        """Get the leader IA from real sources."""
        try:
            if TEAM_ROSTER.get("LEADER"):
                leader_id = TEAM_ROSTER["LEADER"]["id"]
                return self.get_ia_by_id(leader_id)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get leader IA: {e}")
            return None
    
    def get_group_stats(self) -> Dict[str, Dict]:
        """Get statistics by group from real data."""
        try:
            stats = {}
            
            for group in ["L", "G1", "G2", "DATA"]:
                group_ias = self.get_ias_by_group(group)
                total = len(group_ias)
                green = len([ia for ia in group_ias if ia.state == State.GREEN])
                amber = len([ia for ia in group_ias if ia.state == State.AMBER]) 
                red = len([ia for ia in group_ias if ia.state == State.RED])
                
                avg_latency = None
                latencies = [ia.latency_ms for ia in group_ias if ia.latency_ms is not None]
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                
                stats[group] = {
                    'total': total,
                    'green': green,
                    'amber': amber, 
                    'red': red,
                    'avg_latency_ms': avg_latency
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to calculate group stats: {e}")
            return {}
    
    # Private methods for real data source integration (TODO: implement)
    
    def _load_ias_from_mongodb(self) -> List[IA]:
        """Load IAs from MongoDB collection."""
        # TODO: Implement MongoDB integration
        # Should connect to ias collection and return real IA objects
        return []
    
    def _load_ia_from_mongodb(self, ia_id: str) -> Optional[IA]:
        """Load specific IA from MongoDB."""
        # TODO: Implement MongoDB integration
        return None
    
    def _load_ias_from_service(self) -> List[IA]:
        """Load IAs from IA management service."""
        # TODO: Implement service integration
        return []
    
    def _load_ias_with_health_check(self) -> List[IA]:
        """Load IAs with real-time health check."""
        # TODO: Implement health monitoring integration
        return []

# Global instance
ia_registry = IARegistry()
