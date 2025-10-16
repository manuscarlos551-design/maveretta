"""
Web3 Gateway - Interface para interação com blockchains
"""
import os
import asyncio
from typing import Dict, Optional, Any
from decimal import Decimal
from web3 import Web3, AsyncWeb3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_utils import to_checksum_address
import logging

logger = logging.getLogger(__name__)


class Web3Gateway:
    """
    Gateway para interação com blockchains via Web3.
    Suporta múltiplas chains e gerencia conexões.
    """

    # Configuração de chains suportadas
    SUPPORTED_CHAINS = {
        'ethereum': {
            'chain_id': 1,
            'rpc_url': 'https://eth.llamarpc.com',
            'explorer': 'https://etherscan.io',
            'native_token': 'ETH',
            'wrapped_token': 'WETH',
            'wrapped_address': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'gas_multiplier': 1.2
        },
        'bsc': {
            'chain_id': 56,
            'rpc_url': 'https://bsc-dataseed.binance.org',
            'explorer': 'https://bscscan.com',
            'native_token': 'BNB',
            'wrapped_token': 'WBNB',
            'wrapped_address': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
            'gas_multiplier': 1.1
        },
        'polygon': {
            'chain_id': 137,
            'rpc_url': 'https://polygon-rpc.com',
            'explorer': 'https://polygonscan.com',
            'native_token': 'MATIC',
            'wrapped_token': 'WMATIC',
            'wrapped_address': '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
            'gas_multiplier': 1.15
        },
        'arbitrum': {
            'chain_id': 42161,
            'rpc_url': 'https://arb1.arbitrum.io/rpc',
            'explorer': 'https://arbiscan.io',
            'native_token': 'ETH',
            'wrapped_token': 'WETH',
            'wrapped_address': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
            'gas_multiplier': 1.1
        }
    }

    # ERC20 ABI (simplified)
    ERC20_ABI = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": False,
            "inputs": [
                {"name": "_spender", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "approve",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [
                {"name": "_owner", "type": "address"},
                {"name": "_spender", "type": "address"}
            ],
            "name": "allowance",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        }
    ]

    def __init__(self, config: Dict):
        """
        Inicializa Web3Gateway.
        
        Args:
            config: Configuração contendo wallet_address, private_key, etc.
        """
        self.config = config
        self.connections: Dict[str, Web3] = {}
        self.wallet_address = config.get('WALLET_ADDRESS', '')
        self.private_key = config.get('WALLET_PRIVATE_KEY', '')
        
        # Override RPC URLs se fornecidas no config
        for chain in self.SUPPORTED_CHAINS:
            env_key = f"{chain.upper()}_RPC_URL"
            if env_key in config:
                self.SUPPORTED_CHAINS[chain]['rpc_url'] = config[env_key]
        
        logger.info("Web3Gateway initialized")

    async def connect_to_chain(self, chain_name: str) -> Web3:
        """
        Conecta a uma blockchain específica.
        
        Args:
            chain_name: Nome da chain (ethereum, bsc, polygon, arbitrum)
            
        Returns:
            Web3 instance conectada
        """
        if chain_name in self.connections:
            return self.connections[chain_name]
        
        if chain_name not in self.SUPPORTED_CHAINS:
            raise ValueError(f"Chain não suportada: {chain_name}")
        
        chain_config = self.SUPPORTED_CHAINS[chain_name]
        rpc_url = chain_config['rpc_url']
        
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # Adicionar middleware para chains POA (BSC, Polygon)
            if chain_name in ['bsc', 'polygon']:
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Verificar conexão
            if not w3.is_connected():
                raise ConnectionError(f"Falha ao conectar com {chain_name}")
            
            self.connections[chain_name] = w3
            logger.info(f"Conectado com {chain_name} (chain_id: {chain_config['chain_id']})")
            
            return w3
            
        except Exception as e:
            logger.error(f"Erro ao conectar com {chain_name}: {e}")
            raise

    async def get_balance(
        self,
        address: str,
        token: Optional[str] = None,
        chain: str = 'ethereum'
    ) -> float:
        """
        Obtém balance de native token ou ERC20.
        
        Args:
            address: Endereço da wallet
            token: Endereço do token ERC20 (None para native token)
            chain: Nome da chain
            
        Returns:
            Balance em float
        """
        w3 = await self.connect_to_chain(chain)
        address = to_checksum_address(address)
        
        try:
            if token is None:
                # Native token (ETH, BNB, MATIC)
                balance_wei = w3.eth.get_balance(address)
                balance = w3.from_wei(balance_wei, 'ether')
                return float(balance)
            else:
                # ERC20 token
                token = to_checksum_address(token)
                contract = w3.eth.contract(address=token, abi=self.ERC20_ABI)
                
                balance = contract.functions.balanceOf(address).call()
                decimals = contract.functions.decimals().call()
                
                return float(balance) / (10 ** decimals)
                
        except Exception as e:
            logger.error(f"Erro ao obter balance em {chain}: {e}")
            return 0.0

    async def send_transaction(
        self,
        transaction: Dict,
        chain: str
    ) -> Dict:
        """
        Envia transação para blockchain.
        
        Args:
            transaction: Dicionário com dados da transação
            chain: Nome da chain
            
        Returns:
            Dict com tx_hash e receipt
        """
        if not self.private_key:
            raise ValueError("Private key não configurada!")
        
        w3 = await self.connect_to_chain(chain)
        
        try:
            # Adicionar campos obrigatórios
            if 'from' not in transaction:
                transaction['from'] = to_checksum_address(self.wallet_address)
            
            if 'nonce' not in transaction:
                transaction['nonce'] = w3.eth.get_transaction_count(
                    to_checksum_address(self.wallet_address)
                )
            
            if 'chainId' not in transaction:
                transaction['chainId'] = self.SUPPORTED_CHAINS[chain]['chain_id']
            
            # Estimar gas se não fornecido
            if 'gas' not in transaction:
                gas_estimate = w3.eth.estimate_gas(transaction)
                multiplier = self.SUPPORTED_CHAINS[chain]['gas_multiplier']
                transaction['gas'] = int(gas_estimate * multiplier)
            
            # Gas price (EIP-1559 ou legacy)
            if 'maxFeePerGas' not in transaction and 'gasPrice' not in transaction:
                gas_price = w3.eth.gas_price
                transaction['gasPrice'] = gas_price
            
            # Assinar transação
            signed_txn = w3.eth.account.sign_transaction(
                transaction,
                private_key=self.private_key
            )
            
            # Enviar transação
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"Transação enviada em {chain}: {tx_hash.hex()}")
            
            # Aguardar confirmação
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            return {
                'success': receipt['status'] == 1,
                'tx_hash': tx_hash.hex(),
                'block_number': receipt['blockNumber'],
                'gas_used': receipt['gasUsed'],
                'receipt': dict(receipt)
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar transação em {chain}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def estimate_gas(
        self,
        transaction: Dict,
        chain: str
    ) -> int:
        """
        Estima gas necessário para transação.
        
        Args:
            transaction: Dicionário com dados da transação
            chain: Nome da chain
            
        Returns:
            Gas estimado
        """
        w3 = await self.connect_to_chain(chain)
        
        try:
            if 'from' not in transaction:
                transaction['from'] = to_checksum_address(self.wallet_address)
            
            gas_estimate = w3.eth.estimate_gas(transaction)
            multiplier = self.SUPPORTED_CHAINS[chain]['gas_multiplier']
            
            return int(gas_estimate * multiplier)
            
        except Exception as e:
            logger.error(f"Erro ao estimar gas em {chain}: {e}")
            return 0

    def load_contract(
        self,
        address: str,
        abi: list,
        chain: str
    ):
        """
        Carrega contrato inteligente.
        
        Args:
            address: Endereço do contrato
            abi: ABI do contrato
            chain: Nome da chain
            
        Returns:
            Contract instance
        """
        if chain not in self.connections:
            raise ValueError(f"Chain {chain} não conectada")
        
        w3 = self.connections[chain]
        address = to_checksum_address(address)
        
        return w3.eth.contract(address=address, abi=abi)

    async def approve_token(
        self,
        token_address: str,
        spender_address: str,
        amount: float,
        chain: str
    ) -> Dict:
        """
        Aprova spender para gastar tokens.
        
        Args:
            token_address: Endereço do token
            spender_address: Endereço que vai gastar
            amount: Quantidade a aprovar
            chain: Nome da chain
            
        Returns:
            Dict com resultado da aprovação
        """
        w3 = await self.connect_to_chain(chain)
        
        try:
            token_address = to_checksum_address(token_address)
            spender_address = to_checksum_address(spender_address)
            
            contract = w3.eth.contract(address=token_address, abi=self.ERC20_ABI)
            decimals = contract.functions.decimals().call()
            
            # Converter amount para wei
            amount_wei = int(amount * (10 ** decimals))
            
            # Construir transação
            transaction = contract.functions.approve(
                spender_address,
                amount_wei
            ).build_transaction({
                'from': to_checksum_address(self.wallet_address),
                'nonce': w3.eth.get_transaction_count(
                    to_checksum_address(self.wallet_address)
                )
            })
            
            # Enviar transação
            result = await self.send_transaction(transaction, chain)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao aprovar token em {chain}: {e}")
            return {'success': False, 'error': str(e)}

    async def get_allowance(
        self,
        token_address: str,
        owner_address: str,
        spender_address: str,
        chain: str
    ) -> float:
        """
        Verifica allowance de token.
        
        Args:
            token_address: Endereço do token
            owner_address: Endereço do dono
            spender_address: Endereço do spender
            chain: Nome da chain
            
        Returns:
            Allowance em float
        """
        w3 = await self.connect_to_chain(chain)
        
        try:
            token_address = to_checksum_address(token_address)
            owner_address = to_checksum_address(owner_address)
            spender_address = to_checksum_address(spender_address)
            
            contract = w3.eth.contract(address=token_address, abi=self.ERC20_ABI)
            
            allowance = contract.functions.allowance(
                owner_address,
                spender_address
            ).call()
            
            decimals = contract.functions.decimals().call()
            
            return float(allowance) / (10 ** decimals)
            
        except Exception as e:
            logger.error(f"Erro ao obter allowance em {chain}: {e}")
            return 0.0

    def get_chain_config(self, chain: str) -> Dict:
        """Retorna configuração da chain"""
        return self.SUPPORTED_CHAINS.get(chain, {})

    def get_explorer_url(self, chain: str, tx_hash: str) -> str:
        """Retorna URL do explorer para transação"""
        config = self.get_chain_config(chain)
        return f"{config.get('explorer', '')}/tx/{tx_hash}"
