# ai/agents/prometheus_metrics.py
"""
Sistema de métricas Prometheus para agentes de IA
Instrumentação completa para monitoramento e observabilidade
"""

from prometheus_client import Counter, Gauge, Histogram, Info
from typing import Optional
import time
from functools import wraps

# ===== MÉTRICAS DOS AGENTES DE IA =====

# Status do agente (1=online, 0=offline)
ia_agent_status = Gauge(
    'ia_agent_status',
    'IA agent status (1=online, 0=offline)',
    ['agent_id', 'agent_name', 'model', 'strategy']
)

# Total de decisões tomadas
ia_agent_decisions_total = Counter(
    'ia_agent_decisions_total',
    'Total number of decisions made by IA agent',
    ['agent_id', 'agent_name', 'result', 'strategy']
)

# Confiança média das decisões
ia_agent_confidence = Gauge(
    'ia_agent_confidence',
    'Current confidence level of IA agent (0-1)',
    ['agent_id', 'agent_name', 'strategy']
)

# Latência das decisões
ia_agent_decision_latency = Histogram(
    'ia_agent_decision_latency_seconds',
    'Time taken to make a decision',
    ['agent_id', 'agent_name', 'strategy'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# P&L do agente
ia_agent_pnl = Gauge(
    'ia_agent_pnl_usd',
    'Profit and Loss of IA agent in USD',
    ['agent_id', 'agent_name', 'strategy']
)

# Accuracy do agente
ia_agent_accuracy = Gauge(
    'ia_agent_accuracy',
    'Accuracy of IA agent decisions (0-1)',
    ['agent_id', 'agent_name', 'strategy']
)

# Uptime em horas
ia_agent_uptime_hours = Gauge(
    'ia_agent_uptime_hours',
    'Agent uptime in hours',
    ['agent_id', 'agent_name']
)

# Erros do agente
ia_agent_errors_total = Counter(
    'ia_agent_errors_total',
    'Total number of errors encountered by agent',
    ['agent_id', 'agent_name', 'error_type']
)

# API calls do agente (OpenAI, Claude, etc)
ia_agent_api_calls_total = Counter(
    'ia_agent_api_calls_total',
    'Total API calls made by agent',
    ['agent_id', 'agent_name', 'provider', 'status']
)

# Tokens consumidos
ia_agent_tokens_consumed = Counter(
    'ia_agent_tokens_consumed_total',
    'Total tokens consumed by agent',
    ['agent_id', 'agent_name', 'provider']
)

# Info sobre o agente
ia_agent_info = Info(
    'ia_agent',
    'Static information about IA agent'
)


class AgentMetrics:
    """
    Wrapper de métricas para um agente específico
    Facilita o uso das métricas sem repetir labels
    """
    
    def __init__(self, agent_id: str, agent_name: str, model: str, strategy: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.model = model
        self.strategy = strategy
        self.start_time = time.time()
        
        # Registra info estática
        ia_agent_info.info({
            'agent_id': agent_id,
            'agent_name': agent_name,
            'model': model,
            'strategy': strategy,
            'version': '1.0.0'
        })
        
        # Define status inicial como online
        self.set_online()
    
    def set_online(self):
        """Marca agente como online"""
        ia_agent_status.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            model=self.model,
            strategy=self.strategy
        ).set(1)
    
    def set_offline(self):
        """Marca agente como offline"""
        ia_agent_status.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            model=self.model,
            strategy=self.strategy
        ).set(0)
    
    def record_decision(self, result: str, confidence: float, duration: float):
        """
        Registra uma decisão tomada pelo agente
        
        Args:
            result: 'approve', 'reject', 'defer', 'buy', 'sell', 'hold'
            confidence: nível de confiança (0-1)
            duration: tempo de processamento em segundos
        """
        # Contador de decisões
        ia_agent_decisions_total.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            result=result,
            strategy=self.strategy
        ).inc()
        
        # Atualiza confiança
        ia_agent_confidence.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            strategy=self.strategy
        ).set(confidence)
        
        # Registra latência
        ia_agent_decision_latency.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            strategy=self.strategy
        ).observe(duration)
    
    def update_pnl(self, pnl_usd: float):
        """Atualiza P&L do agente"""
        ia_agent_pnl.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            strategy=self.strategy
        ).set(pnl_usd)
    
    def update_accuracy(self, accuracy: float):
        """Atualiza accuracy do agente (0-1)"""
        ia_agent_accuracy.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            strategy=self.strategy
        ).set(accuracy)
    
    def update_uptime(self):
        """Atualiza uptime em horas"""
        uptime_hours = (time.time() - self.start_time) / 3600
        ia_agent_uptime_hours.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name
        ).set(uptime_hours)
    
    def record_error(self, error_type: str):
        """Registra um erro"""
        ia_agent_errors_total.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            error_type=error_type
        ).inc()
    
    def record_api_call(self, provider: str, status: str, tokens: int = 0):
        """
        Registra uma chamada de API
        
        Args:
            provider: 'openai', 'claude', 'together', etc.
            status: 'success', 'error', 'timeout'
            tokens: número de tokens consumidos
        """
        ia_agent_api_calls_total.labels(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            provider=provider,
            status=status
        ).inc()
        
        if tokens > 0:
            ia_agent_tokens_consumed.labels(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                provider=provider
            ).inc(tokens)


def track_decision(agent_metrics: AgentMetrics):
    """
    Decorator para rastrear decisões automaticamente
    
    Uso:
        @track_decision(agent_metrics)
        def make_decision(self, market_data):
            # ... lógica da decisão
            return {'result': 'buy', 'confidence': 0.85}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Registra decisão
                if isinstance(result, dict):
                    agent_metrics.record_decision(
                        result=result.get('result', 'unknown'),
                        confidence=result.get('confidence', 0.0),
                        duration=duration
                    )
                
                return result
                
            except Exception as e:
                agent_metrics.record_error(type(e).__name__)
                raise
        
        return wrapper
    return decorator


# ===== EXEMPLO DE USO =====
"""
# No arquivo do agente (ex: intelligent_agent.py):

from ai.agents.prometheus_metrics import AgentMetrics, track_decision

class IntelligentAgent:
    def __init__(self, agent_id, name, model, strategy):
        # Inicializar métricas
        self.metrics = AgentMetrics(
            agent_id=agent_id,
            agent_name=name,
            model=model,
            strategy=strategy
        )
    
    @track_decision(self.metrics)
    def make_decision(self, market_data):
        # Lógica da decisão
        decision = self._analyze(market_data)
        
        # Atualizar métricas adicionais
        self.metrics.update_pnl(self.get_current_pnl())
        self.metrics.update_accuracy(self.calculate_accuracy())
        self.metrics.update_uptime()
        
        return {
            'result': 'buy',
            'confidence': 0.85,
            'price': 45000.0
        }
    
    def call_openai_api(self, prompt):
        try:
            response = openai.chat.completions.create(...)
            tokens = response.usage.total_tokens
            
            self.metrics.record_api_call(
                provider='openai',
                status='success',
                tokens=tokens
            )
            
            return response
        except Exception as e:
            self.metrics.record_api_call(
                provider='openai',
                status='error'
            )
            raise
"""
