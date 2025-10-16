"""
DEX Manager - Gerenciador principal de exchanges descentralizadas
"""
import logging
import asyncio
from typing import Dict, List, Optional
from decimal import Decimal
from .gateway.web3_gateway import Web3Gateway
from .connectors.uniswap_v3 import UniswapV3Connector
from .connectors.pancakeswap import PancakeSwapConnector
from .connectors.sushiswap import SushiSwapConnector
from .connectors.curve import CurveConnector

logger = logging.getLogger(__name__)


class DEXManager:
    """
    Gerenciador de exchanges descentralizadas (DEXs).
    
    Features:
    - Conexão com múltiplas DEXs (Uniswap V3, PancakeSwap, SushiSwap, Curve)
    - Suporte a múltiplas chains (Ethereum, BSC, Polygon, Arbitrum)
    - Agregação de liquidez cross-DEX
    - Otimização de rotas
    - Cálculo de price impact
    - Estimativa de gas
    """

    def __init__(self, config: Dict):
        """
        Inicializa DEXManager.
        
        Args:
            config: Configuração contendo wallet, RPCs, etc.
        """
        self.config = config
        self.gateway = Web3Gateway(config)
        
        # Inicializar conectores
        self.connectors = {}
        
        # Uniswap V3 (Ethereum, Polygon, Arbitrum)
        for chain in ['ethereum', 'polygon', 'arbitrum']:
            try:
                self.connectors[f'uniswap_v3_{chain}'] = UniswapV3Connector(
                    self.gateway,
                    chain
                )
            except Exception as e:
                logger.warning(f"Uniswap V3 não disponível em {chain}: {e}")
        
        # PancakeSwap (BSC)
        try:
            self.connectors['pancakeswap_bsc'] = PancakeSwapConnector(
                self.gateway,
                'bsc'
            )
        except Exception as e:
            logger.warning(f"PancakeSwap não disponível: {e}")
        
        # SushiSwap (múltiplas chains)
        for chain in ['ethereum', 'polygon', 'arbitrum']:
            try:
                self.connectors[f'sushiswap_{chain}'] = SushiSwapConnector(
                    self.gateway,
                    chain
                )
            except Exception as e:
                logger.warning(f"SushiSwap não disponível em {chain}: {e}")
        
        # Curve (Ethereum)
        try:
            self.connectors['curve_ethereum'] = CurveConnector(
                self.gateway,
                'ethereum'
            )
        except Exception as e:
            logger.warning(f"Curve não disponível: {e}")
        
        logger.info(f"DEXManager initialized with {len(self.connectors)} connectors")

    async def find_best_route(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        chain: str = 'ethereum',
        compare_dexs: bool = True
    ) -> Dict:
        """
        Encontra a melhor rota de swap considerando múltiplas DEXs.
        
        Args:
            token_in: Endereço do token de entrada (ou símbolo)
            token_out: Endereço do token de saída (ou símbolo)
            amount_in: Quantidade de entrada
            chain: Chain onde executar swap
            compare_dexs: Se deve comparar múltiplas DEXs
            
        Returns:
            Dict com melhor rota, cotação e detalhes
        """
        try:
            # Resolver símbolos para endereços se necessário
            token_in_address = await self._resolve_token_address(token_in, chain)
            token_out_address = await self._resolve_token_address(token_out, chain)
            
            # Obter quotes de todas as DEXs disponíveis para essa chain
            quotes = []
            
            for connector_name, connector in self.connectors.items():
                # Verificar se connector é para a chain correta
                if chain not in connector_name:
                    continue
                
                try:
                    quote = await connector.get_quote(
                        token_in_address,
                        token_out_address,
                        amount_in
                    )
                    
                    if quote.get('success'):
                        quote['connector_name'] = connector_name
                        quotes.append(quote)
                        
                except Exception as e:
                    logger.warning(f"Erro ao obter quote de {connector_name}: {e}")
                    continue
            
            if not quotes:
                return {
                    'success': False,
                    'error': 'Nenhuma DEX disponível para esse par/chain'
                }
            
            # Ordenar por amount_out (melhor cotação)
            quotes.sort(key=lambda x: x.get('amount_out', 0), reverse=True)
            
            best_quote = quotes[0]
            
            # Adicionar comparação
            best_quote['compared_dexs'] = [q['dex'] for q in quotes]
            best_quote['num_quotes'] = len(quotes)
            
            # Calcular savings vs segunda melhor opção
            if len(quotes) > 1:
                second_best = quotes[1]
                savings = best_quote['amount_out'] - second_best['amount_out']
                savings_pct = (savings / second_best['amount_out']) * 100
                
                best_quote['savings'] = {
                    'amount': savings,
                    'pct': savings_pct,
                    'vs_dex': second_best['dex']
                }
            
            return best_quote
            
        except Exception as e:
            logger.error(f"Erro ao encontrar melhor rota: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def execute_swap(
        self,
        route: Dict,
        slippage_tolerance: float = 0.01,
        deadline: int = 300
    ) -> Dict:
        """
        Executa swap na DEX.
        
        Args:
            route: Rota retornada por find_best_route
            slippage_tolerance: Tolerância de slippage (default 1%)
            deadline: Prazo em segundos
            
        Returns:
            Dict com resultado do swap
        """
        try:
            if not route.get('success'):
                return {
                    'success': False,
                    'error': 'Rota inválida'
                }
            
            # Calcular amount_out_min com slippage
            amount_out = route['amount_out']
            amount_out_min = amount_out * (1 - slippage_tolerance)
            
            # Obter connector
            connector_name = route.get('connector_name')
            if not connector_name or connector_name not in self.connectors:
                return {
                    'success': False,
                    'error': 'Connector não encontrado'
                }
            
            connector = self.connectors[connector_name]
            
            # Executar swap
            result = await connector.execute_swap(
                token_in=route['token_in'],
                token_out=route['token_out'],
                amount_in=route['amount_in'],
                amount_out_min=amount_out_min,
                deadline=deadline
            )
            
            # Adicionar informações da rota ao resultado
            if result.get('success'):
                result['dex'] = route['dex']
                result['chain'] = route['chain']
                result['expected_amount_out'] = amount_out
                result['min_amount_out'] = amount_out_min
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao executar swap: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_liquidity_info(
        self,
        token_pair: tuple,
        chain: str
    ) -> Dict:
        """
        Obtém informações de liquidez para um par.
        
        Args:
            token_pair: Tupla (token0, token1)
            chain: Chain
            
        Returns:
            Dict com informações de liquidez
        """
        # TODO: Implementar agregação de liquidez de múltiplas DEXs
        return {
            'success': False,
            'error': 'Implementação pendente'
        }

    async def find_arbitrage_opportunities(
        self,
        tokens: List[str],
        chains: List[str] = None,
        min_profit_pct: float = 0.5
    ) -> List[Dict]:
        """
        Encontra oportunidades de arbitragem cross-DEX ou cross-chain.
        
        Args:
            tokens: Lista de tokens para verificar
            chains: Lista de chains (None = todas)
            min_profit_pct: Lucro mínimo em % para considerar
            
        Returns:
            Lista de oportunidades ordenadas por lucro
        """
        opportunities = []
        
        if chains is None:
            chains = ['ethereum', 'bsc', 'polygon', 'arbitrum']
        
        try:
            # Para cada par de tokens
            for i, token_in in enumerate(tokens):
                for token_out in tokens[i+1:]:
                    
                    # Verificar preços em diferentes DEXs/chains
                    prices = {}
                    
                    for chain in chains:
                        try:
                            # Obter melhor preço nessa chain
                            route = await self.find_best_route(
                                token_in=token_in,
                                token_out=token_out,
                                amount_in=1.0,  # Normalizado
                                chain=chain,
                                compare_dexs=True
                            )
                            
                            if route.get('success'):
                                prices[chain] = {
                                    'price': route['price'],
                                    'dex': route['dex'],
                                    'route': route
                                }
                        except Exception as e:
                            continue
                    
                    # Encontrar diferenças de preço
                    if len(prices) < 2:
                        continue
                    
                    # Comparar todos os pares
                    chain_list = list(prices.keys())
                    for i, buy_chain in enumerate(chain_list):
                        for sell_chain in chain_list[i+1:]:
                            
                            buy_price = prices[buy_chain]['price']
                            sell_price = prices[sell_chain]['price']
                            
                            # Calcular lucro potencial
                            profit_pct = ((sell_price - buy_price) / buy_price) * 100
                            
                            if profit_pct >= min_profit_pct:
                                opportunities.append({
                                    'token_in': token_in,
                                    'token_out': token_out,
                                    'buy_chain': buy_chain,
                                    'sell_chain': sell_chain,
                                    'buy_dex': prices[buy_chain]['dex'],
                                    'sell_dex': prices[sell_chain]['dex'],
                                    'buy_price': buy_price,
                                    'sell_price': sell_price,
                                    'profit_pct': profit_pct,
                                    'type': 'cross_chain' if buy_chain != sell_chain else 'cross_dex'
                                })\n            
            # Ordenar por lucro
            opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
            
            logger.info(f"Found {len(opportunities)} arbitrage opportunities")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Erro ao encontrar oportunidades: {e}")
            return []

    async def _resolve_token_address(
        self,
        token: str,
        chain: str
    ) -> str:
        """
        Resolve símbolo de token para endereço.
        
        Args:
            token: Símbolo ou endereço
            chain: Chain
            
        Returns:
            Endereço do token
        """
        # Se já é endereço (começa com 0x), retornar
        if token.startswith('0x'):
            return token
        
        # Mapa de símbolos comuns para endereços
        token_addresses = {
            'ethereum': {
                'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'
            },
            'bsc': {
                'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
                'USDC': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
                'USDT': '0x55d398326f99059fF775485246999027B3197955',
                'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
                'BTCB': '0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c'
            },
            'polygon': {
                'WMATIC': '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
                'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
                'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
                'DAI': '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
                'WETH': '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619'
            },
            'arbitrum': {
                'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
                'USDC': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
                'USDT': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
                'DAI': '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
                'WBTC': '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'
            }
        }
        
        chain_tokens = token_addresses.get(chain, {})
        address = chain_tokens.get(token.upper())
        
        if not address:
            raise ValueError(f"Token {token} não encontrado em {chain}")
        
        return address

    def get_supported_chains(self) -> List[str]:
        """Retorna lista de chains suportadas"""
        chains = set()
        for connector_name in self.connectors.keys():
            # Extrair chain do nome (formato: dex_chain)
            parts = connector_name.split('_')
            if len(parts) >= 2:
                chains.add(parts[-1])
        
        return list(chains)

    def get_supported_dexs(self, chain: str = None) -> List[str]:
        """Retorna lista de DEXs suportadas"""
        dexs = set()
        
        for connector_name in self.connectors.keys():
            if chain is None or chain in connector_name:
                # Extrair DEX do nome
                dex = connector_name.split('_')[0]
                dexs.add(dex)
        
        return list(dexs)

    async def get_wallet_balances(
        self,
        tokens: List[str],
        chain: str
    ) -> Dict:
        """
        Obtém balances de múltiplos tokens.
        
        Args:
            tokens: Lista de endereços de tokens
            chain: Chain
            
        Returns:
            Dict com balances
        """
        balances = {}
        
        for token in tokens:
            try:
                token_address = await self._resolve_token_address(token, chain)
                
                balance = await self.gateway.get_balance(
                    address=self.gateway.wallet_address,
                    token=token_address,
                    chain=chain
                )
                
                balances[token] = balance
                
            except Exception as e:
                logger.error(f"Erro ao obter balance de {token}: {e}")
                balances[token] = 0.0
        
        # Native token balance
        try:
            native_balance = await self.gateway.get_balance(
                address=self.gateway.wallet_address,
                token=None,
                chain=chain
            )
            
            chain_config = self.gateway.get_chain_config(chain)
            native_token = chain_config.get('native_token', 'ETH')
            
            balances[native_token] = native_balance
            
        except Exception as e:
            logger.error(f"Erro ao obter balance nativo: {e}")
        
        return balances
