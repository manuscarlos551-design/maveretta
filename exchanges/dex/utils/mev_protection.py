"""
MEV Protection - Proteção contra Maximum Extractable Value (MEV)
"""
import logging
from typing import Dict, List
from decimal import Decimal

logger = logging.getLogger(__name__)


class MEVProtection:
    """
    Proteção contra Maximum Extractable Value (MEV).
    
    Estratégias:
    - Flashbots (Ethereum)
    - Slippage protection
    - Transaction splitting
    - Sandwich attack detection
    """

    # Flashbots relay URLs
    FLASHBOTS_RELAYS = {
        'ethereum': 'https://relay.flashbots.net',
        'goerli': 'https://relay-goerli.flashbots.net'
    }

    def __init__(self, config: Dict):
        """
        Inicializa MEV Protection.
        
        Args:
            config: Configuração
        """
        self.config = config
        self.mev_protection_enabled = config.get('MEV_PROTECTION_ENABLED', True)
        self.flashbots_enabled = config.get('FLASHBOTS_ENABLED', False)
        
        logger.info("MEVProtection initialized")
        if self.mev_protection_enabled:
            logger.info("MEV protection ATIVADO")
        else:
            logger.warning("MEV protection DESATIVADO")

    async def use_flashbots(
        self,
        transaction: Dict,
        chain: str = 'ethereum'
    ) -> Dict:
        """
        Envia transação via Flashbots para evitar MEV.
        
        Args:
            transaction: Dict com dados da transação
            chain: Chain (apenas ethereum suportado)
            
        Returns:
            Dict com resultado
        """
        if not self.flashbots_enabled:
            return {
                'success': False,
                'error': 'Flashbots não habilitado na configuração'
            }
        
        if chain not in self.FLASHBOTS_RELAYS:
            return {
                'success': False,
                'error': f'Flashbots não disponível em {chain}'
            }
        
        # TODO: Implementar integração com Flashbots
        # Requer biblioteca flashbots e assinatura especial
        
        logger.warning("Flashbots integration em desenvolvimento")
        
        return {
            'success': False,
            'error': 'Flashbots integration em desenvolvimento',
            'relay_url': self.FLASHBOTS_RELAYS.get(chain)
        }

    def add_slippage_protection(
        self,
        transaction: Dict,
        max_slippage_pct: float = 1.0
    ) -> Dict:
        """
        Adiciona proteção de slippage.
        
        Args:
            transaction: Dict com dados da transação
            max_slippage_pct: Máximo slippage permitido (%)
            
        Returns:
            Transaction modificada
        """
        if 'amountOutMinimum' in transaction or 'amountOutMin' in transaction:
            # Já tem proteção
            return transaction
        
        # Calcular amountOutMin baseado em expected output
        if 'expectedAmountOut' in transaction:
            expected = transaction['expectedAmountOut']
            slippage_multiplier = 1 - (max_slippage_pct / 100)
            amount_out_min = expected * slippage_multiplier
            
            transaction['amountOutMinimum'] = int(amount_out_min)
            transaction['slippage_protection'] = max_slippage_pct
            
            logger.info(f"Slippage protection adicionado: {max_slippage_pct}%")
        
        return transaction

    async def check_sandwich_attack_risk(
        self,
        transaction: Dict,
        pool: Dict
    ) -> Dict:
        """
        Verifica risco de sandwich attack.
        
        Args:
            transaction: Dict com dados da transação
            pool: Informações da pool
            
        Returns:
            Dict com risk_level, should_proceed, recommended_actions
        """
        try:
            # Calcular price impact
            amount_in = transaction.get('amountIn', 0)
            pool_liquidity = pool.get('liquidity', 0)
            
            if pool_liquidity == 0:
                return {
                    'risk_level': 'UNKNOWN',
                    'should_proceed': False,
                    'reason': 'Liquidity info não disponível'
                }
            
            # Price impact como % da liquidez
            price_impact_pct = (amount_in / pool_liquidity) * 100
            
            # Determinar risco
            if price_impact_pct < 0.1:
                risk_level = 'LOW'
                should_proceed = True
                recommended_actions = []
            elif price_impact_pct < 1.0:
                risk_level = 'MEDIUM'
                should_proceed = True
                recommended_actions = [
                    'Considerar usar Flashbots',
                    'Aumentar slippage tolerance'
                ]
            elif price_impact_pct < 5.0:
                risk_level = 'HIGH'
                should_proceed = False
                recommended_actions = [
                    'Usar Flashbots obrigatoriamente',
                    'Considerar dividir transação',
                    'Aguardar mais liquidez'
                ]
            else:
                risk_level = 'CRITICAL'
                should_proceed = False
                recommended_actions = [
                    'NãO executar',
                    'Dividir em múltiplas transações pequenas',
                    'Aguardar significativamente mais liquidez'
                ]
            
            return {
                'risk_level': risk_level,
                'should_proceed': should_proceed,
                'price_impact_pct': round(price_impact_pct, 4),
                'recommended_actions': recommended_actions
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar risco de sandwich: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'should_proceed': False,
                'error': str(e)
            }

    def split_transaction(
        self,
        transaction: Dict,
        num_parts: int = 3
    ) -> List[Dict]:
        """
        Divide transação grande em partes menores.
        
        Args:
            transaction: Transação original
            num_parts: Número de partes
            
        Returns:
            Lista de transações menores
        """
        if num_parts < 2:
            return [transaction]
        
        amount_in = transaction.get('amountIn', 0)
        amount_per_part = amount_in / num_parts
        
        split_transactions = []
        
        for i in range(num_parts):
            tx_part = transaction.copy()
            tx_part['amountIn'] = amount_per_part
            tx_part['part_number'] = i + 1
            tx_part['total_parts'] = num_parts
            
            split_transactions.append(tx_part)
        
        logger.info(f"Transação dividida em {num_parts} partes")
        
        return split_transactions

    def get_mev_protection_recommendations(
        self,
        transaction_value_usd: float,
        chain: str
    ) -> Dict:
        """
        Retorna recomendações de proteção MEV baseadas no valor.
        
        Args:
            transaction_value_usd: Valor da transação em USD
            chain: Chain
            
        Returns:
            Dict com recomendações
        """
        recommendations = {
            'use_flashbots': False,
            'max_slippage': 1.0,
            'split_transaction': False,
            'num_parts': 1,
            'wait_for_lower_gas': False
        }
        
        # Valores pequenos (<$100)
        if transaction_value_usd < 100:
            recommendations['max_slippage'] = 2.0
            recommendations['use_flashbots'] = False
        
        # Valores médios ($100-$1000)
        elif transaction_value_usd < 1000:
            recommendations['max_slippage'] = 1.0
            recommendations['use_flashbots'] = chain == 'ethereum'
        
        # Valores altos ($1000-$10000)
        elif transaction_value_usd < 10000:
            recommendations['max_slippage'] = 0.5
            recommendations['use_flashbots'] = True
            recommendations['wait_for_lower_gas'] = True
        
        # Valores muito altos (>$10000)
        else:
            recommendations['max_slippage'] = 0.3
            recommendations['use_flashbots'] = True
            recommendations['split_transaction'] = True
            recommendations['num_parts'] = 3
            recommendations['wait_for_lower_gas'] = True
        
        return recommendations
