"""
Funding Rate Analyzer - Análise de Funding Rate

Features:
- Obtenção de funding rate atual
- Histórico de funding rate
- Cálculo de custo de funding
- Recomendação de posições baseada em funding
- Identificação de oportunidades de arbitragem
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio


class FundingRateAnalyzer:
    """
    Análise de funding rate para futures perpetuos.
    """

    def __init__(self, exchanges: Dict):
        """
        Inicializa analyzer de funding rate.

        Args:
            exchanges: Dicionário com conexões CCXT das exchanges
        """
        self.exchanges = exchanges

    async def get_current_funding_rate(
        self,
        exchange_name: str,
        symbol: str
    ) -> Dict:
        """
        Obtém funding rate atual.

        Args:
            exchange_name: Nome da exchange
            symbol: Símbolo (ex: 'BTC/USDT:USDT')

        Returns:
            Dict com funding rate e informações
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            # Obter funding rate
            funding_rate_info = await exchange.fetch_funding_rate(symbol)
            
            result = {
                'symbol': symbol,
                'exchange': exchange_name,
                'funding_rate': funding_rate_info.get('fundingRate', 0),
                'funding_rate_pct': funding_rate_info.get('fundingRate', 0) * 100,
                'next_funding_time': funding_rate_info.get('fundingTimestamp', 0),
                'mark_price': funding_rate_info.get('markPrice', 0),
                'index_price': funding_rate_info.get('indexPrice', 0),
                'timestamp': datetime.utcnow().isoformat(),
                'success': True
            }

            # Classificar funding rate
            funding_pct = result['funding_rate_pct']
            if abs(funding_pct) < 0.01:
                result['classification'] = 'NEUTRAL'
            elif funding_pct > 0.05:
                result['classification'] = 'HIGH_POSITIVE'
            elif funding_pct > 0.01:
                result['classification'] = 'POSITIVE'
            elif funding_pct < -0.05:
                result['classification'] = 'HIGH_NEGATIVE'
            elif funding_pct < -0.01:
                result['classification'] = 'NEGATIVE'
            else:
                result['classification'] = 'NEUTRAL'

            return result

        except Exception as e:
            print(f"❌ Erro ao obter funding rate: {e}")
            return {
                'symbol': symbol,
                'exchange': exchange_name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def get_funding_rate_history(
        self,
        exchange_name: str,
        symbol: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Obtém histórico de funding rate.

        Args:
            exchange_name: Nome da exchange
            symbol: Símbolo
            limit: Número de registros (default: 100)

        Returns:
            Lista com histórico de funding rates
        """
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} não disponível")

        exchange = self.exchanges[exchange_name]

        try:
            # Obter histórico
            funding_history = await exchange.fetch_funding_rate_history(
                symbol=symbol,
                limit=limit
            )
            
            history = []
            for record in funding_history:
                history.append({
                    'timestamp': record.get('timestamp', 0),
                    'datetime': record.get('datetime', ''),
                    'funding_rate': record.get('fundingRate', 0),
                    'funding_rate_pct': record.get('fundingRate', 0) * 100,
                    'symbol': symbol,
                    'exchange': exchange_name
                })

            return history

        except Exception as e:
            print(f"❌ Erro ao obter histórico de funding rate: {e}")
            return []

    def calculate_funding_cost(
        self,
        position_size: float,
        funding_rate: float,
        hours: int = 8,
        periods: int = 1
    ) -> Dict:
        """
        Calcula custo de funding.

        Args:
            position_size: Tamanho da posição (notional value)
            funding_rate: Taxa de funding (ex: 0.0001 = 0.01%)
            hours: Horas por período de funding (default: 8)
            periods: Número de períodos (default: 1)

        Returns:
            Dict com custo de funding
        """
        # Custo por período
        cost_per_period = position_size * funding_rate
        
        # Custo total
        total_cost = cost_per_period * periods
        
        # Custo anualizado (aproximado)
        periods_per_day = 24 / hours
        periods_per_year = periods_per_day * 365
        annual_cost = cost_per_period * periods_per_year
        annual_cost_pct = (annual_cost / position_size) * 100 if position_size > 0 else 0

        return {
            'cost_per_period': cost_per_period,
            'total_cost': total_cost,
            'annual_cost': annual_cost,
            'annual_cost_pct': annual_cost_pct,
            'position_size': position_size,
            'funding_rate': funding_rate,
            'funding_rate_pct': funding_rate * 100,
            'hours_per_period': hours,
            'periods': periods,
            'periods_per_year': periods_per_year
        }

    def should_avoid_position(
        self,
        funding_rate: float,
        threshold: float = 0.01,
        side: str = 'long'
    ) -> Dict:
        """
        Determina se deve evitar posição devido a funding alto.

        Args:
            funding_rate: Taxa de funding
            threshold: Threshold de decisão (default: 0.01 = 1%)
            side: 'long' ou 'short'

        Returns:
            Dict com recomendação
        """
        funding_pct = abs(funding_rate) * 100
        
        # Funding positivo penaliza longs
        # Funding negativo penaliza shorts
        should_avoid = False
        reason = ""

        if side.lower() in ['long', 'buy']:
            if funding_rate > threshold:
                should_avoid = True
                reason = f"Funding rate muito alto ({funding_pct:.4f}%) penaliza posições long"
        else:  # short
            if funding_rate < -threshold:
                should_avoid = True
                reason = f"Funding rate muito negativo ({funding_pct:.4f}%) penaliza posições short"

        if not should_avoid:
            reason = "Funding rate aceitável"

        return {
            'should_avoid': should_avoid,
            'reason': reason,
            'funding_rate': funding_rate,
            'funding_rate_pct': funding_pct,
            'threshold': threshold,
            'side': side
        }

    async def analyze_funding_opportunities(
        self,
        symbols: List[str],
        exchanges: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Analisa oportunidades baseadas em funding rate.

        Args:
            symbols: Lista de símbolos para analisar
            exchanges: Lista de exchanges (None = todas)

        Returns:
            Lista de oportunidades ordenadas por atratividade
        """
        if exchanges is None:
            exchanges = list(self.exchanges.keys())

        opportunities = []

        for symbol in symbols:
            for exchange_name in exchanges:
                funding_info = await self.get_current_funding_rate(exchange_name, symbol)
                
                if not funding_info.get('success'):
                    continue

                funding_rate = funding_info['funding_rate']
                funding_pct = funding_info['funding_rate_pct']

                # Identificar oportunidades
                opportunity = None
                
                if funding_pct > 0.1:  # > 0.1%
                    opportunity = {
                        'type': 'SHORT_OPPORTUNITY',
                        'reason': 'Funding rate alto favorece shorts',
                        'recommended_side': 'short',
                        'attractiveness': funding_pct
                    }
                elif funding_pct < -0.1:  # < -0.1%
                    opportunity = {
                        'type': 'LONG_OPPORTUNITY',
                        'reason': 'Funding rate negativo favorece longs',
                        'recommended_side': 'long',
                        'attractiveness': abs(funding_pct)
                    }

                if opportunity:
                    opportunities.append({
                        'symbol': symbol,
                        'exchange': exchange_name,
                        'funding_rate': funding_rate,
                        'funding_rate_pct': funding_pct,
                        **opportunity,
                        'timestamp': datetime.utcnow().isoformat()
                    })

        # Ordenar por atratividade
        opportunities.sort(key=lambda x: x['attractiveness'], reverse=True)

        return opportunities

    def calculate_average_funding(
        self,
        funding_history: List[Dict]
    ) -> Dict:
        """
        Calcula médias de funding rate.

        Args:
            funding_history: Lista com histórico de funding

        Returns:
            Dict com estatísticas
        """
        if not funding_history:
            return {
                'avg_funding_rate': 0,
                'min_funding_rate': 0,
                'max_funding_rate': 0,
                'count': 0
            }

        rates = [record['funding_rate'] for record in funding_history]
        
        avg_rate = sum(rates) / len(rates)
        min_rate = min(rates)
        max_rate = max(rates)

        return {
            'avg_funding_rate': avg_rate,
            'avg_funding_rate_pct': avg_rate * 100,
            'min_funding_rate': min_rate,
            'min_funding_rate_pct': min_rate * 100,
            'max_funding_rate': max_rate,
            'max_funding_rate_pct': max_rate * 100,
            'count': len(rates),
            'period_start': funding_history[0]['datetime'] if funding_history else None,
            'period_end': funding_history[-1]['datetime'] if funding_history else None
        }

    async def compare_funding_across_exchanges(
        self,
        symbol: str,
        exchanges: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Compara funding rate entre exchanges.

        Args:
            symbol: Símbolo
            exchanges: Lista de exchanges (None = todas)

        Returns:
            Lista com comparação
        """
        if exchanges is None:
            exchanges = list(self.exchanges.keys())

        comparison = []

        for exchange_name in exchanges:
            funding_info = await self.get_current_funding_rate(exchange_name, symbol)
            
            if funding_info.get('success'):
                comparison.append({
                    'exchange': exchange_name,
                    'symbol': symbol,
                    'funding_rate': funding_info['funding_rate'],
                    'funding_rate_pct': funding_info['funding_rate_pct'],
                    'classification': funding_info['classification'],
                    'next_funding_time': funding_info['next_funding_time']
                })

        # Ordenar por funding rate
        comparison.sort(key=lambda x: x['funding_rate'])

        return comparison

    def identify_arbitrage_opportunity(
        self,
        funding_comparison: List[Dict],
        threshold_diff: float = 0.05
    ) -> Optional[Dict]:
        """
        Identifica oportunidades de arbitragem de funding.

        Args:
            funding_comparison: Lista de comparação entre exchanges
            threshold_diff: Diferença mínima para considerar arbitragem (%)

        Returns:
            Oportunidade de arbitragem ou None
        """
        if len(funding_comparison) < 2:
            return None

        # Exchange com menor funding (melhor para long)
        best_for_long = funding_comparison[0]
        
        # Exchange com maior funding (melhor para short)
        best_for_short = funding_comparison[-1]

        # Diferença de funding
        funding_diff = best_for_short['funding_rate_pct'] - best_for_long['funding_rate_pct']

        if abs(funding_diff) >= threshold_diff:
            return {
                'type': 'FUNDING_ARBITRAGE',
                'long_exchange': best_for_long['exchange'],
                'short_exchange': best_for_short['exchange'],
                'symbol': best_for_long['symbol'],
                'funding_diff_pct': funding_diff,
                'long_funding_rate': best_for_long['funding_rate_pct'],
                'short_funding_rate': best_for_short['funding_rate_pct'],
                'estimated_profit_per_period_pct': funding_diff,
                'recommendation': f"Long em {best_for_long['exchange']} e Short em {best_for_short['exchange']}",
                'timestamp': datetime.utcnow().isoformat()
            }

        return None
