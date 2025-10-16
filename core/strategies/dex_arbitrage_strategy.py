"""
DEX Arbitrage Strategy - Estratégia de arbitragem entre DEXs
"""
import logging
import asyncio
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class DEXArbitrageStrategy:
    """
    Estratégia de arbitragem entre DEXs.
    
    Tipos de arbitragem:
    - Cross-DEX (mesma chain, DEXs diferentes)
    - Cross-Chain (chains diferentes)
    - Triangular (três tokens em ciclo)
    """

    def __init__(self, config: Dict):
        """
        Inicializa DEX Arbitrage Strategy.
        
        Args:
            config: Configuração da estratégia
        """
        self.config = config
        self.dex_manager = None  # Será injetado
        self.gas_optimizer = None  # Será injetado
        self.mev_protection = None  # Será injetado
        
        # Parâmetros
        self.min_profit_pct = config.get('MIN_PROFIT_PCT', 0.5)
        self.max_gas_cost_pct = config.get('MAX_GAS_COST_PCT', 30.0)
        self.slippage_tolerance = config.get('SLIPPAGE_TOLERANCE', 0.01)
        
        # Estatísticas
        self.stats = {
            'opportunities_found': 0,
            'opportunities_executed': 0,
            'total_profit_usd': 0.0,
            'failed_attempts': 0
        }
        
        logger.info(f"DEXArbitrageStrategy initialized (min_profit: {self.min_profit_pct}%)")

    def set_dependencies(self, dex_manager, gas_optimizer, mev_protection):
        """Injeta dependências"""
        self.dex_manager = dex_manager
        self.gas_optimizer = gas_optimizer
        self.mev_protection = mev_protection

    async def find_opportunities(
        self,
        tokens: List[str],
        chains: List[str] = None,
        amount_base: float = 1.0
    ) -> List[Dict]:
        """
        Encontra oportunidades de arbitragem.
        
        Args:
            tokens: Lista de tokens para verificar
            chains: Lista de chains (None = todas)
            amount_base: Quantidade base para teste
            
        Returns:
            Lista de oportunidades ordenadas por lucro esperado
        """
        if not self.dex_manager:
            raise ValueError("DEXManager não injetado")
        
        opportunities = []
        
        if chains is None:
            chains = self.dex_manager.get_supported_chains()
        
        logger.info(f"Buscando arbitragem em {len(tokens)} tokens e {len(chains)} chains")
        
        try:
            # 1. Cross-DEX arbitrage (mesma chain)
            for chain in chains:
                cross_dex_opps = await self._find_cross_dex_opportunities(
                    tokens, chain, amount_base
                )
                opportunities.extend(cross_dex_opps)
            
            # 2. Cross-Chain arbitrage
            if len(chains) > 1:
                cross_chain_opps = await self._find_cross_chain_opportunities(
                    tokens, chains, amount_base
                )
                opportunities.extend(cross_chain_opps)
            
            # 3. Triangular arbitrage
            for chain in chains:
                triangular_opps = await self._find_triangular_opportunities(
                    tokens, chain, amount_base
                )
                opportunities.extend(triangular_opps)
            
            # Filtrar por lucro mínimo
            opportunities = [
                opp for opp in opportunities
                if opp.get('net_profit_pct', 0) >= self.min_profit_pct
            ]
            
            # Ordenar por lucro
            opportunities.sort(key=lambda x: x.get('net_profit_pct', 0), reverse=True)
            
            self.stats['opportunities_found'] += len(opportunities)
            
            logger.info(f"Encontradas {len(opportunities)} oportunidades de arbitragem")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Erro ao buscar oportunidades: {e}")
            return []

    async def execute_arbitrage(
        self,
        opportunity: Dict
    ) -> Dict:
        """
        Executa arbitragem.
        
        Args:
            opportunity: Oportunidade identificada
            
        Returns:
            Dict com resultado da execução
        """
        if not all([self.dex_manager, self.gas_optimizer, self.mev_protection]):
            raise ValueError("Dependências não injetadas")
        
        try:
            arb_type = opportunity.get('type')
            
            if arb_type == 'cross_dex':
                result = await self._execute_cross_dex_arbitrage(opportunity)
            elif arb_type == 'cross_chain':
                result = await self._execute_cross_chain_arbitrage(opportunity)
            elif arb_type == 'triangular':
                result = await self._execute_triangular_arbitrage(opportunity)
            else:
                return {
                    'success': False,
                    'error': f'Tipo de arbitragem desconhecido: {arb_type}'
                }
            
            # Atualizar estatísticas
            if result.get('success'):
                self.stats['opportunities_executed'] += 1
                self.stats['total_profit_usd'] += result.get('actual_profit_usd', 0)
            else:
                self.stats['failed_attempts'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao executar arbitragem: {e}")
            self.stats['failed_attempts'] += 1
            return {
                'success': False,
                'error': str(e)
            }

    async def _find_cross_dex_opportunities(
        self,
        tokens: List[str],
        chain: str,
        amount: float
    ) -> List[Dict]:
        """Busca arbitragem cross-DEX na mesma chain"""
        opportunities = []
        
        # Para cada par de tokens
        for i, token_in in enumerate(tokens):
            for token_out in tokens[i+1:]:
                try:
                    # Obter melhores quotes de DEXs
                    route = await self.dex_manager.find_best_route(
                        token_in=token_in,
                        token_out=token_out,
                        amount_in=amount,
                        chain=chain,
                        compare_dexs=True
                    )
                    
                    if not route.get('success') or route.get('num_quotes', 0) < 2:
                        continue
                    
                    # Já tem comparação entre DEXs no route
                    savings = route.get('savings', {})
                    
                    if savings:
                        profit_pct = savings.get('pct', 0)
                        
                        # Estimar custos de gas
                        gas_cost_usd = await self._estimate_gas_cost(chain, 'swap')
                        
                        # Calcular lucro líquido
                        gross_profit_usd = savings.get('amount', 0) * amount  # Aproximado
                        net_profit_usd = gross_profit_usd - gas_cost_usd
                        net_profit_pct = (net_profit_usd / amount) * 100 if amount > 0 else 0
                        
                        if net_profit_pct > 0:
                            opportunities.append({
                                'type': 'cross_dex',
                                'chain': chain,
                                'token_in': token_in,
                                'token_out': token_out,
                                'amount': amount,
                                'buy_dex': savings.get('vs_dex'),
                                'sell_dex': route['dex'],
                                'gross_profit_pct': profit_pct,
                                'gas_cost_usd': gas_cost_usd,
                                'net_profit_usd': net_profit_usd,
                                'net_profit_pct': net_profit_pct,
                                'route': route
                            })
                
                except Exception as e:
                    logger.debug(f"Erro ao verificar {token_in}/{token_out}: {e}")
                    continue
        
        return opportunities

    async def _find_cross_chain_opportunities(
        self,
        tokens: List[str],
        chains: List[str],
        amount: float
    ) -> List[Dict]:
        """Busca arbitragem cross-chain"""
        # Usa find_arbitrage_opportunities do DEXManager
        return await self.dex_manager.find_arbitrage_opportunities(
            tokens=tokens,
            chains=chains,
            min_profit_pct=0  # Vamos filtrar depois
        )

    async def _find_triangular_opportunities(
        self,
        tokens: List[str],
        chain: str,
        amount: float
    ) -> List[Dict]:
        """Busca arbitragem triangular (3 tokens em ciclo)"""
        opportunities = []
        
        if len(tokens) < 3:
            return opportunities
        
        # Para cada combinação de 3 tokens
        for i in range(len(tokens)):
            for j in range(i+1, len(tokens)):
                for k in range(j+1, len(tokens)):
                    token_a = tokens[i]
                    token_b = tokens[j]
                    token_c = tokens[k]
                    
                    try:
                        # Simular ciclo: A -> B -> C -> A
                        result = await self._simulate_triangular_cycle(
                            token_a, token_b, token_c, chain, amount
                        )
                        
                        if result and result.get('net_profit_pct', 0) > 0:
                            opportunities.append(result)
                    
                    except Exception as e:
                        continue
        
        return opportunities

    async def _simulate_triangular_cycle(
        self,
        token_a: str,
        token_b: str,
        token_c: str,
        chain: str,
        amount: float
    ) -> Optional[Dict]:
        """Simula ciclo triangular"""
        try:
            # A -> B
            route1 = await self.dex_manager.find_best_route(
                token_a, token_b, amount, chain
            )
            if not route1.get('success'):
                return None
            
            amount_b = route1['amount_out']
            
            # B -> C
            route2 = await self.dex_manager.find_best_route(
                token_b, token_c, amount_b, chain
            )
            if not route2.get('success'):
                return None
            
            amount_c = route2['amount_out']
            
            # C -> A
            route3 = await self.dex_manager.find_best_route(
                token_c, token_a, amount_c, chain
            )
            if not route3.get('success'):
                return None
            
            final_amount_a = route3['amount_out']
            
            # Calcular lucro
            profit = final_amount_a - amount
            profit_pct = (profit / amount) * 100 if amount > 0 else 0
            
            # Estimar gas (3 swaps)
            gas_cost_usd = await self._estimate_gas_cost(chain, 'swap') * 3
            
            # Lucro líquido
            net_profit_usd = profit - gas_cost_usd
            net_profit_pct = (net_profit_usd / amount) * 100 if amount > 0 else 0
            
            if net_profit_pct > 0:
                return {
                    'type': 'triangular',
                    'chain': chain,
                    'cycle': f"{token_a} -> {token_b} -> {token_c} -> {token_a}",
                    'amount_start': amount,
                    'amount_end': final_amount_a,
                    'gross_profit': profit,
                    'gross_profit_pct': profit_pct,
                    'gas_cost_usd': gas_cost_usd,
                    'net_profit_usd': net_profit_usd,
                    'net_profit_pct': net_profit_pct,
                    'routes': [route1, route2, route3]
                }
            
            return None
            
        except Exception as e:
            return None

    async def _execute_cross_dex_arbitrage(self, opportunity: Dict) -> Dict:
        """Executa arbitragem cross-DEX"""
        # TODO: Implementar execução real
        return {
            'success': False,
            'error': 'Execução de arbitragem em desenvolvimento',
            'opportunity': opportunity
        }

    async def _execute_cross_chain_arbitrage(self, opportunity: Dict) -> Dict:
        """Executa arbitragem cross-chain"""
        # TODO: Implementar com bridge
        return {
            'success': False,
            'error': 'Arbitragem cross-chain em desenvolvimento',
            'opportunity': opportunity
        }

    async def _execute_triangular_arbitrage(self, opportunity: Dict) -> Dict:
        """Executa arbitragem triangular"""
        # TODO: Implementar sequência de swaps
        return {
            'success': False,
            'error': 'Arbitragem triangular em desenvolvimento',
            'opportunity': opportunity
        }

    async def _estimate_gas_cost(self, chain: str, operation: str) -> float:
        """Estima custo de gas em USD"""
        # Estimativas aproximadas
        gas_costs_usd = {
            'ethereum': {'swap': 50, 'approve': 20},
            'bsc': {'swap': 1, 'approve': 0.5},
            'polygon': {'swap': 0.5, 'approve': 0.2},
            'arbitrum': {'swap': 2, 'approve': 0.5}
        }
        
        chain_costs = gas_costs_usd.get(chain, {'swap': 10, 'approve': 5})
        return chain_costs.get(operation, 10)

    def get_statistics(self) -> Dict:
        """Retorna estatísticas da estratégia"""
        return {
            **self.stats,
            'success_rate': (
                self.stats['opportunities_executed'] / 
                max(self.stats['opportunities_found'], 1)
            ) * 100,
            'avg_profit_per_trade': (
                self.stats['total_profit_usd'] / 
                max(self.stats['opportunities_executed'], 1)
            )
        }

    def reset_statistics(self):
        """Reseta estatísticas"""
        self.stats = {
            'opportunities_found': 0,
            'opportunities_executed': 0,
            'total_profit_usd': 0.0,
            'failed_attempts': 0
        }
