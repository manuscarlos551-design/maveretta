
# core/testing/ab_testing.py
"""
A/B Testing Framework - Testa múltiplas versões de estratégia em paralelo
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import uuid
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class StrategyVariant:
    """Variante de estratégia para teste"""
    variant_id: str
    name: str
    strategy_params: Dict[str, Any]
    allocation_pct: float  # % de tráfego
    is_control: bool = False


@dataclass
class ABTestResult:
    """Resultado de um trade em teste A/B"""
    test_id: str
    variant_id: str
    symbol: str
    pnl: float
    timestamp: datetime
    metadata: Dict[str, Any]


class ABTestingFramework:
    """
    Framework para testar múltiplas estratégias em paralelo
    """
    
    def __init__(self):
        self.active_tests: Dict[str, Dict[str, Any]] = {}
        self.test_results: Dict[str, List[ABTestResult]] = {}
        
        logger.info("✅ A/B Testing Framework initialized")
    
    def create_test(
        self,
        test_name: str,
        variants: List[StrategyVariant],
        duration_hours: int = 24,
        min_samples: int = 30
    ) -> str:
        """
        Cria um novo teste A/B
        
        Args:
            test_name: Nome do teste
            variants: Lista de variantes a testar
            duration_hours: Duração do teste em horas
            min_samples: Mínimo de samples por variante
        
        Returns:
            Test ID
        """
        try:
            test_id = str(uuid.uuid4())
            
            # Valida alocação
            total_allocation = sum(v.allocation_pct for v in variants)
            if abs(total_allocation - 100) > 0.01:
                raise ValueError(f"Total allocation must be 100%, got {total_allocation}%")
            
            # Verifica se há exatamente 1 controle
            control_count = sum(1 for v in variants if v.is_control)
            if control_count != 1:
                raise ValueError("Must have exactly 1 control variant")
            
            self.active_tests[test_id] = {
                'test_id': test_id,
                'name': test_name,
                'variants': {v.variant_id: v for v in variants},
                'start_time': datetime.now(timezone.utc),
                'duration_hours': duration_hours,
                'min_samples': min_samples,
                'status': 'running'
            }
            
            self.test_results[test_id] = []
            
            logger.info(
                f"Created A/B test '{test_name}' with {len(variants)} variants "
                f"(duration: {duration_hours}h)"
            )
            
            return test_id
            
        except Exception as e:
            logger.error(f"Error creating A/B test: {e}")
            raise
    
    def assign_variant(self, test_id: str, symbol: str) -> Optional[StrategyVariant]:
        """
        Atribui uma variante para um símbolo baseado em alocação
        
        Args:
            test_id: ID do teste
            symbol: Símbolo de trading
        
        Returns:
            Variante atribuída
        """
        try:
            if test_id not in self.active_tests:
                return None
            
            test = self.active_tests[test_id]
            variants = list(test['variants'].values())
            
            # Weighted random selection
            weights = [v.allocation_pct for v in variants]
            selected = np.random.choice(variants, p=np.array(weights) / 100)
            
            return selected
            
        except Exception as e:
            logger.error(f"Error assigning variant: {e}")
            return None
    
    def record_result(
        self,
        test_id: str,
        variant_id: str,
        symbol: str,
        pnl: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Registra resultado de um trade
        
        Args:
            test_id: ID do teste
            variant_id: ID da variante
            symbol: Símbolo
            pnl: P&L do trade
            metadata: Metadados adicionais
        """
        try:
            if test_id not in self.test_results:
                self.test_results[test_id] = []
            
            result = ABTestResult(
                test_id=test_id,
                variant_id=variant_id,
                symbol=symbol,
                pnl=pnl,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            
            self.test_results[test_id].append(result)
            
        except Exception as e:
            logger.error(f"Error recording test result: {e}")
    
    def analyze_test(self, test_id: str) -> Dict[str, Any]:
        """
        Analisa resultados do teste com significância estatística
        
        Args:
            test_id: ID do teste
        
        Returns:
            Análise detalhada
        """
        try:
            if test_id not in self.active_tests:
                return {}
            
            test = self.active_tests[test_id]
            results = self.test_results.get(test_id, [])
            
            if not results:
                return {'status': 'no_data'}
            
            # Agrupa por variante
            variants_data = {}
            for variant_id in test['variants'].keys():
                variant_results = [r for r in results if r.variant_id == variant_id]
                
                if variant_results:
                    pnls = [r.pnl for r in variant_results]
                    variants_data[variant_id] = {
                        'count': len(pnls),
                        'mean_pnl': np.mean(pnls),
                        'std_pnl': np.std(pnls),
                        'total_pnl': sum(pnls),
                        'win_rate': sum(1 for p in pnls if p > 0) / len(pnls),
                        'pnls': pnls
                    }
            
            # Identifica controle
            control_id = next(
                v.variant_id for v in test['variants'].values() if v.is_control
            )
            
            # Testes de significância vs controle
            statistical_tests = {}
            if control_id in variants_data:
                control_pnls = variants_data[control_id]['pnls']
                
                for variant_id, data in variants_data.items():
                    if variant_id == control_id:
                        continue
                    
                    # T-test
                    t_stat, p_value = stats.ttest_ind(
                        data['pnls'],
                        control_pnls
                    )
                    
                    # Lift vs controle
                    lift_pct = (
                        (data['mean_pnl'] - variants_data[control_id]['mean_pnl']) /
                        abs(variants_data[control_id]['mean_pnl'])
                    ) * 100 if variants_data[control_id]['mean_pnl'] != 0 else 0
                    
                    statistical_tests[variant_id] = {
                        't_statistic': t_stat,
                        'p_value': p_value,
                        'is_significant': p_value < 0.05,
                        'lift_pct': lift_pct,
                        'recommendation': self._get_recommendation(
                            p_value, lift_pct, data['count'], test['min_samples']
                        )
                    }
            
            # Determina vencedor
            winner = self._determine_winner(variants_data, statistical_tests, test)
            
            return {
                'test_id': test_id,
                'test_name': test['name'],
                'status': test['status'],
                'variants_data': variants_data,
                'statistical_tests': statistical_tests,
                'winner': winner,
                'total_samples': len(results)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing test: {e}")
            return {}
    
    def _get_recommendation(
        self,
        p_value: float,
        lift_pct: float,
        sample_count: int,
        min_samples: int
    ) -> str:
        """Gera recomendação baseada em estatísticas"""
        if sample_count < min_samples:
            return 'continue_testing'
        
        if p_value < 0.05:
            if lift_pct > 10:
                return 'promote_to_production'
            elif lift_pct < -10:
                return 'reject_variant'
            else:
                return 'marginal_improvement'
        else:
            return 'no_significant_difference'
    
    def _determine_winner(
        self,
        variants_data: Dict[str, Dict[str, Any]],
        statistical_tests: Dict[str, Dict[str, Any]],
        test: Dict[str, Any]
    ) -> Optional[str]:
        """Determina variante vencedora"""
        # Verifica se há amostras suficientes
        min_samples = test['min_samples']
        for data in variants_data.values():
            if data['count'] < min_samples:
                return None  # Ainda testando
        
        # Procura variante significativamente melhor
        best_variant = None
        best_lift = 0
        
        for variant_id, stats_test in statistical_tests.items():
            if stats_test['is_significant'] and stats_test['lift_pct'] > best_lift:
                best_lift = stats_test['lift_pct']
                best_variant = variant_id
        
        return best_variant
    
    def stop_test(self, test_id: str):
        """Para um teste A/B"""
        if test_id in self.active_tests:
            self.active_tests[test_id]['status'] = 'stopped'
            logger.info(f"Stopped A/B test {test_id}")


# Instância global
ab_testing_framework = ABTestingFramework()
