# core/engine/cascade_orchestrator.py
"""
Cascade Orchestrator - Sistema Automático de Transferência de Lucros entre Slots
Monitora slots e executa cascade quando meta de 10% é atingida
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class CascadeOrchestrator:
    """
    Orquestrador automático do sistema de cascade entre slots
    
    Responsabilidades:
    - Monitorar todos os slots periodicamente
    - Detectar quando slot atinge meta de lucro (padrão 10%)
    - Executar transferência automática de lucro para próximo slot
    - Ativar próximo slot quando receber capital
    - Manter logs de todas as transferências
    """
    
    def __init__(
        self,
        slot_manager=None,
        check_interval_seconds: int = 300,  # 5 minutos
        config_file: str = "./data/cascade_config.json"
    ):
        """
        Inicializa o orquestrador de cascade
        
        Args:
            slot_manager: Gerenciador de slots (será integrado futuramente)
            check_interval_seconds: Intervalo entre verificações (padrão: 5 min)
            config_file: Arquivo de configuração da cadeia de slots
        """
        self.slot_manager = slot_manager
        self.check_interval = check_interval_seconds
        self.config_file = Path(config_file)
        
        # Estado do orquestrador
        self.running = False
        self.thread = None
        self.slots_config = {}
        self.cascade_history = []
        
        # Carregar configuração
        self._load_config()
        
        logger.info(f"[CASCADE_ORCHESTRATOR] Initialized with {len(self.slots_config)} slots")
        logger.info(f"[CASCADE_ORCHESTRATOR] Check interval: {check_interval_seconds}s")
    
    def _load_config(self) -> None:
        """Carrega configuração da cadeia de slots"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.slots_config = {
                        slot['slot_id']: slot 
                        for slot in data.get('cascade_chain', [])
                    }
                logger.info(f"[CASCADE_ORCHESTRATOR] Loaded config for {len(self.slots_config)} slots")
            else:
                logger.warning(f"[CASCADE_ORCHESTRATOR] Config file not found: {self.config_file}")
                self._create_default_config()
        except Exception as e:
            logger.error(f"[CASCADE_ORCHESTRATOR] Error loading config: {e}")
            self._create_default_config()
    
    def _create_default_config(self) -> None:
        """Cria configuração padrão com 10 slots"""
        default_chain = []
        
        # Agentes IA disponíveis: A1, A2, A3, A4, A5, A6
        # Distribuição: G1 (slots ímpares), G2 (slots pares)
        agents_g1 = ["A1", "A2", "A3"]  # Agentes principais do G1
        agents_g2 = ["A4", "A5", "A6"]  # Agentes principais do G2
        
        for i in range(1, 11):  # 10 slots
            slot_id = f"slot_{i}"
            next_slot = f"slot_{i+1}" if i < 10 else None
            
            # Determinar grupo e agente IA
            is_g1 = (i % 2 == 1)  # Ímpares são G1
            ia_group = "G1" if is_g1 else "G2"
            
            # Atribuir agente IA ciclicamente
            if is_g1:
                assigned_ia = agents_g1[(i // 2) % len(agents_g1)]
            else:
                assigned_ia = agents_g2[(i // 2) % len(agents_g2)]
            
            default_chain.append({
                "slot_id": slot_id,
                "capital_base": 1000.0,  # Ajustável pelo usuário
                "cascade_target_pct": 10.0,
                "next_slot_id": next_slot,
                "cascade_enabled": True,
                "active": i == 1,  # Apenas slot_1 inicia ativo
                "assigned_ia": assigned_ia,
                "ia_group": ia_group,
                "ia_status": "ACTIVE" if i == 1 else "INACTIVE"
            })
        
        self.slots_config = {slot['slot_id']: slot for slot in default_chain}
        
        # Salvar configuração
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump({"cascade_chain": default_chain}, f, indent=2)
            logger.info(f"[CASCADE_ORCHESTRATOR] Created default config with 10 slots")
        except Exception as e:
            logger.error(f"[CASCADE_ORCHESTRATOR] Error saving default config: {e}")
    
    def start(self) -> None:
        """Inicia o orquestrador em thread separada"""
        if self.running:
            logger.warning("[CASCADE_ORCHESTRATOR] Already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        
        logger.info("[CASCADE_ORCHESTRATOR] Started monitoring loop")
    
    def stop(self) -> None:
        """Para o orquestrador"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        
        logger.info("[CASCADE_ORCHESTRATOR] Stopped")
    
    def _monitoring_loop(self) -> None:
        """Loop principal de monitoramento"""
        logger.info("[CASCADE_ORCHESTRATOR] Monitoring loop started")
        
        while self.running:
            try:
                # Verificar todos os slots
                self._check_all_slots()
                
                # Aguardar próximo ciclo
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"[CASCADE_ORCHESTRATOR] Error in monitoring loop: {e}")
                time.sleep(60)  # Aguarda 1 min em caso de erro
    
    def _check_all_slots(self) -> None:
        """Verifica todos os slots para possível cascade"""
        
        # Se temos slot_manager integrado, usar ele
        if self.slot_manager:
            slots = self._get_slots_from_manager()
        else:
            # Caso contrário, usar dados da configuração (modo standalone)
            slots = self._get_slots_from_config()
        
        for slot in slots:
            try:
                self._check_slot_cascade(slot)
            except Exception as e:
                logger.error(f"[CASCADE_ORCHESTRATOR] Error checking slot {slot.get('id', 'unknown')}: {e}")
    
    def _get_slots_from_manager(self) -> List[Dict[str, Any]]:
        """Obtém slots do gerenciador (integração futura)"""
        try:
            # TODO: Integrar com slot_manager real
            # return self.slot_manager.get_all_slots()
            return []
        except Exception as e:
            logger.error(f"[CASCADE_ORCHESTRATOR] Error getting slots from manager: {e}")
            return []
    
    def _get_slots_from_config(self) -> List[Dict[str, Any]]:
        """Obtém slots da configuração (modo standalone)"""
        # Retorna lista de slots da configuração
        # Em produção, isso virá do MongoDB ou Redis
        return list(self.slots_config.values())
    
    def _check_slot_cascade(self, slot: Dict[str, Any]) -> None:
        """
        Verifica se slot deve executar cascade
        
        Args:
            slot: Dados do slot
        """
        slot_id = slot.get('slot_id') or slot.get('id')
        
        # Verificar se slot está ativo
        if not slot.get('active', False):
            return
        
        # Verificar se cascade está habilitado
        if not slot.get('cascade_enabled', True):
            return
        
        # Verificar se tem próximo slot configurado
        next_slot_id = slot.get('next_slot_id')
        if not next_slot_id:
            return
        
        # Calcular P&L atual
        capital_base = slot.get('capital_base', 1000.0)
        capital_current = slot.get('capital_current', capital_base)
        pnl = capital_current - capital_base
        pnl_percentage = (pnl / capital_base * 100) if capital_base > 0 else 0
        
        # Verificar se atingiu meta
        cascade_target = slot.get('cascade_target_pct', 10.0)
        
        if pnl_percentage >= cascade_target:
            logger.info(f"[CASCADE_ORCHESTRATOR] Slot {slot_id} reached target: {pnl_percentage:.2f}% >= {cascade_target}%")
            self._execute_cascade(slot, pnl)
    
    def _execute_cascade(self, slot: Dict[str, Any], profit_amount: float) -> None:
        """
        Executa transferência de cascade
        
        Args:
            slot: Slot origem
            profit_amount: Lucro a transferir
        """
        slot_id = slot.get('slot_id') or slot.get('id')
        next_slot_id = slot.get('next_slot_id')
        
        try:
            logger.info(f"[CASCADE_ORCHESTRATOR] Executing cascade: {slot_id} -> {next_slot_id}")
            logger.info(f"[CASCADE_ORCHESTRATOR] Transferring profit: ${profit_amount:.2f}")
            
            # 1. Resetar capital do slot atual
            slot['capital_current'] = slot['capital_base']
            slot['pnl'] = 0.0
            slot['pnl_percentage'] = 0.0
            
            # 2. Transferir lucro para próximo slot
            if next_slot_id in self.slots_config:
                next_slot = self.slots_config[next_slot_id]
                
                # Adicionar lucro ao capital do próximo slot
                next_slot['capital_current'] = next_slot.get('capital_current', next_slot['capital_base']) + profit_amount
                
                # ATIVAR próximo slot (recebeu capital!)
                next_slot['active'] = True
                
                # ATIVAR agente IA do próximo slot
                if 'assigned_ia' in next_slot:
                    next_slot['ia_status'] = 'ACTIVE'
                    self._activate_ia_agent(next_slot['assigned_ia'], next_slot_id)
                
                logger.info(f"[CASCADE_ORCHESTRATOR] Slot {next_slot_id} activated with ${next_slot['capital_current']:.2f}")
                logger.info(f"[CASCADE_ORCHESTRATOR] Agent {next_slot.get('assigned_ia', 'N/A')} activated for {next_slot_id}")
            
            # 3. Registrar no histórico
            cascade_record = {
                'timestamp': datetime.now().isoformat(),
                'from_slot': slot_id,
                'to_slot': next_slot_id,
                'profit_transferred': profit_amount,
                'success': True
            }
            self.cascade_history.append(cascade_record)
            self._save_cascade_log(cascade_record)
            
            # 4. Persistir mudanças
            self._save_config()
            
            logger.info(f"[CASCADE_ORCHESTRATOR] Cascade completed successfully")
            
        except Exception as e:
            logger.error(f"[CASCADE_ORCHESTRATOR] Error executing cascade: {e}")
            
            # Registrar falha
            cascade_record = {
                'timestamp': datetime.now().isoformat(),
                'from_slot': slot_id,
                'to_slot': next_slot_id,
                'profit_transferred': profit_amount,
                'success': False,
                'error': str(e)
            }
            self.cascade_history.append(cascade_record)
            self._save_cascade_log(cascade_record)
    
    def _save_config(self) -> None:
        """Salva configuração atualizada"""
        try:
            cascade_chain = list(self.slots_config.values())
            with open(self.config_file, 'w') as f:
                json.dump({"cascade_chain": cascade_chain}, f, indent=2)
        except Exception as e:
            logger.error(f"[CASCADE_ORCHESTRATOR] Error saving config: {e}")
    
    def _save_cascade_log(self, record: Dict[str, Any]) -> None:
        """Salva log de cascade executado"""
        try:
            log_file = Path("./data/cascade_history.jsonl")
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(record) + '\n')
                
        except Exception as e:
            logger.error(f"[CASCADE_ORCHESTRATOR] Error saving cascade log: {e}")
    
    def _activate_ia_agent(self, agent_id: str, slot_id: str) -> None:
        """
        Ativa agente IA para um slot específico
        
        Args:
            agent_id: ID do agente (A1, A2, A3, A4, A5, A6)
            slot_id: ID do slot que será operado pelo agente
        """
        try:
            # Registrar ativação do agente IA no Redis
            import redis
            import os
            
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Chave para status do agente
            agent_key = f"ia:agent_{agent_id}:status"
            slot_assignment_key = f"ia:agent_{agent_id}:slot_assignment"
            
            # Atualizar status do agente
            agent_status = {
                'status': 'ACTIVE',
                'assigned_slot': slot_id,
                'activated_at': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat()
            }
            
            redis_client.set(agent_key, json.dumps(agent_status), ex=86400)  # 24h expiry
            redis_client.set(slot_assignment_key, slot_id, ex=86400)
            
            logger.info(f"[CASCADE_ORCHESTRATOR] Agent {agent_id} activated for slot {slot_id}")
            
        except Exception as e:
            logger.warning(f"[CASCADE_ORCHESTRATOR] Error activating agent {agent_id}: {e}")
    
    def _deactivate_ia_agent(self, agent_id: str, slot_id: str) -> None:
        """
        Desativa agente IA de um slot
        
        Args:
            agent_id: ID do agente
            slot_id: ID do slot
        """
        try:
            import redis
            import os
            
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            redis_client = redis.from_url(redis_url, decode_responses=True)
            
            agent_key = f"ia:agent_{agent_id}:status"
            
            agent_status = {
                'status': 'INACTIVE',
                'assigned_slot': slot_id,
                'deactivated_at': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat()
            }
            
            redis_client.set(agent_key, json.dumps(agent_status), ex=86400)
            
            logger.info(f"[CASCADE_ORCHESTRATOR] Agent {agent_id} deactivated from slot {slot_id}")
            
        except Exception as e:
            logger.warning(f"[CASCADE_ORCHESTRATOR] Error deactivating agent {agent_id}: {e}")
    
    def get_cascade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retorna histórico de cascades executados
        
        Args:
            limit: Número máximo de registros
            
        Returns:
            Lista com histórico de cascades
        """
        try:
            log_file = Path("./data/cascade_history.jsonl")
            
            if not log_file.exists():
                return []
            
            history = []
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        history.append(record)
                    except:
                        continue
            
            # Retornar últimos N registros
            return history[-limit:] if len(history) > limit else history
            
        except Exception as e:
            logger.error(f"[CASCADE_ORCHESTRATOR] Error reading cascade history: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do orquestrador"""
        return {
            'running': self.running,
            'check_interval_seconds': self.check_interval,
            'total_slots': len(self.slots_config),
            'active_slots': sum(1 for s in self.slots_config.values() if s.get('active', False)),
            'total_cascades': len(self.cascade_history),
            'last_cascade': self.cascade_history[-1] if self.cascade_history else None
        }
    
    def update_slot_config(self, slot_id: str, updates: Dict[str, Any]) -> bool:
        """
        Atualiza configuração de um slot
        
        Args:
            slot_id: ID do slot
            updates: Dicionário com campos a atualizar
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            if slot_id not in self.slots_config:
                logger.error(f"[CASCADE_ORCHESTRATOR] Slot {slot_id} not found")
                return False
            
            # Atualizar campos permitidos
            allowed_fields = ['capital_base', 'cascade_target_pct', 'cascade_enabled', 'active']
            for field, value in updates.items():
                if field in allowed_fields:
                    self.slots_config[slot_id][field] = value
            
            # Salvar configuração
            self._save_config()
            
            logger.info(f"[CASCADE_ORCHESTRATOR] Updated config for slot {slot_id}")
            return True
            
        except Exception as e:
            logger.error(f"[CASCADE_ORCHESTRATOR] Error updating slot config: {e}")
            return False


# Instância global (singleton)
_cascade_orchestrator_instance = None


def get_cascade_orchestrator(**kwargs) -> CascadeOrchestrator:
    """Retorna instância singleton do orquestrador"""
    global _cascade_orchestrator_instance
    
    if _cascade_orchestrator_instance is None:
        _cascade_orchestrator_instance = CascadeOrchestrator(**kwargs)
    
    return _cascade_orchestrator_instance


def start_cascade_orchestrator(**kwargs) -> CascadeOrchestrator:
    """Inicia o orquestrador de cascade"""
    orchestrator = get_cascade_orchestrator(**kwargs)
    orchestrator.start()
    return orchestrator
