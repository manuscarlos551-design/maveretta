
# core/market/whale_monitor.py
"""
Whale Monitor - Detecta atividade de grandes players (baleias)
Monitora grandes ordens, movimentações on-chain e padrões suspeitos
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import logging
from collections import deque

logger = logging.getLogger(__name__)


class WhaleActivityType:
    """Tipos de atividade de baleia"""
    LARGE_ORDER = "large_order"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    WASH_TRADING = "wash_trading"
    SPOOFING = "spoofing"


class WhaleMonitor:
    """
    Monitora atividade de baleias (grandes players)
    """
    
    def __init__(self):
        self.whale_alerts: deque = deque(maxlen=1000)
        self.whale_zones: Dict[str, List[float]] = {}  # symbol -> [prices]
        
        # Thresholds
        self.large_order_threshold_btc = 10.0  # 10 BTC
        self.large_order_threshold_usd = 500000  # $500k
        self.volume_spike_multiplier = 3.0  # 3x volume médio
        
        logger.info("✅ Whale Monitor initialized")
    
    def analyze_orderbook(
        self,
        symbol: str,
        orderbook: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analisa order book para detectar grandes ordens
        
        Args:
            symbol: Par de trading
            orderbook: Order book data (bids, asks)
        
        Returns:
            Lista de alertas de baleia
        """
        alerts = []
        
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Analisa bids (compras)
            for price, amount in bids:
                if self._is_whale_order(symbol, amount, price):
                    alerts.append({
                        'symbol': symbol,
                        'type': WhaleActivityType.LARGE_ORDER,
                        'side': 'buy',
                        'price': price,
                        'amount': amount,
                        'value_usd': price * amount,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            # Analisa asks (vendas)
            for price, amount in asks:
                if self._is_whale_order(symbol, amount, price):
                    alerts.append({
                        'symbol': symbol,
                        'type': WhaleActivityType.LARGE_ORDER,
                        'side': 'sell',
                        'price': price,
                        'amount': amount,
                        'value_usd': price * amount,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            # Detecta spoofing (grandes ordens que não são executadas)
            spoofing_alerts = self._detect_spoofing(symbol, bids, asks)
            alerts.extend(spoofing_alerts)
            
            # Salva alertas
            for alert in alerts:
                self.whale_alerts.append(alert)
                self._update_whale_zones(symbol, alert['price'])
            
            if alerts:
                logger.info(
                    f"🐋 Whale activity detected: {len(alerts)} alerts for {symbol}"
                )
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error analyzing orderbook: {e}")
            return []
    
    def analyze_trades(
        self,
        symbol: str,
        trades: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analisa trades recentes para detectar acumulação/distribuição
        
        Args:
            symbol: Par de trading
            trades: Lista de trades recentes
        
        Returns:
            Lista de alertas
        """
        alerts = []
        
        try:
            if not trades or len(trades) < 10:
                return []
            
            df = pd.DataFrame(trades)
            
            # Detecta volume spike
            avg_volume = df['amount'].mean()
            recent_volume = df.tail(5)['amount'].sum()
            
            if recent_volume > avg_volume * self.volume_spike_multiplier:
                # Verifica se é acumulação (mais compras) ou distribuição (mais vendas)
                recent_trades = df.tail(10)
                buy_volume = recent_trades[recent_trades['side'] == 'buy']['amount'].sum()
                sell_volume = recent_trades[recent_trades['side'] == 'sell']['amount'].sum()
                
                if buy_volume > sell_volume * 1.5:
                    activity_type = WhaleActivityType.ACCUMULATION
                    side = 'buy'
                elif sell_volume > buy_volume * 1.5:
                    activity_type = WhaleActivityType.DISTRIBUTION
                    side = 'sell'
                else:
                    return []
                
                alerts.append({
                    'symbol': symbol,
                    'type': activity_type,
                    'side': side,
                    'volume': recent_volume,
                    'avg_price': recent_trades['price'].mean(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            # Detecta wash trading (mesmo trader comprando e vendendo)
            wash_trading_alerts = self._detect_wash_trading(symbol, trades)
            alerts.extend(wash_trading_alerts)
            
            # Salva alertas
            for alert in alerts:
                self.whale_alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error analyzing trades: {e}")
            return []
    
    def _is_whale_order(self, symbol: str, amount: float, price: float) -> bool:
        """Verifica se é uma ordem de baleia"""
        value_usd = amount * price
        
        # BTC/USD
        if 'BTC' in symbol:
            return amount >= self.large_order_threshold_btc or \
                   value_usd >= self.large_order_threshold_usd
        
        # Outros pares
        return value_usd >= self.large_order_threshold_usd
    
    def _detect_spoofing(
        self,
        symbol: str,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]]
    ) -> List[Dict[str, Any]]:
        """
        Detecta spoofing (grandes ordens que não são executadas)
        
        Spoofing: Colocar grandes ordens para manipular preço, mas cancelar antes de execução
        """
        alerts = []
        
        # Verifica se há grandes ordens muito longe do preço atual
        if bids and asks:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid_price = (best_bid + best_ask) / 2
            
            # Procura grandes ordens > 2% longe do mid price
            for price, amount in bids:
                if price < mid_price * 0.98 and self._is_whale_order(symbol, amount, price):
                    alerts.append({
                        'symbol': symbol,
                        'type': WhaleActivityType.SPOOFING,
                        'side': 'buy',
                        'price': price,
                        'amount': amount,
                        'distance_from_mid': ((mid_price - price) / mid_price) * 100,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            for price, amount in asks:
                if price > mid_price * 1.02 and self._is_whale_order(symbol, amount, price):
                    alerts.append({
                        'symbol': symbol,
                        'type': WhaleActivityType.SPOOFING,
                        'side': 'sell',
                        'price': price,
                        'amount': amount,
                        'distance_from_mid': ((price - mid_price) / mid_price) * 100,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
        
        return alerts
    
    def _detect_wash_trading(
        self,
        symbol: str,
        trades: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detecta wash trading (mesmo trader comprando e vendendo)
        
        Padrão: Muitos trades no mesmo preço em curto período
        """
        alerts = []
        
        df = pd.DataFrame(trades)
        
        # Agrupa por preço
        price_groups = df.groupby('price').size()
        
        # Se há muitos trades no mesmo preço (>10)
        suspicious_prices = price_groups[price_groups > 10]
        
        for price in suspicious_prices.index:
            price_trades = df[df['price'] == price]
            
            # Verifica se há alternância rápida buy/sell
            if len(price_trades) > 10:
                alerts.append({
                    'symbol': symbol,
                    'type': WhaleActivityType.WASH_TRADING,
                    'price': price,
                    'trade_count': len(price_trades),
                    'volume': price_trades['amount'].sum(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        
        return alerts
    
    def _update_whale_zones(self, symbol: str, price: float):
        """Atualiza zonas onde baleias estão ativas"""
        if symbol not in self.whale_zones:
            self.whale_zones[symbol] = []
        
        self.whale_zones[symbol].append(price)
        
        # Mantém apenas últimos 100 preços
        if len(self.whale_zones[symbol]) > 100:
            self.whale_zones[symbol] = self.whale_zones[symbol][-100:]
    
    def get_whale_zones(self, symbol: str) -> List[float]:
        """
        Retorna zonas de preço onde baleias estão ativas
        
        Returns:
            Lista de preços onde há concentração de atividade
        """
        if symbol not in self.whale_zones:
            return []
        
        prices = self.whale_zones[symbol]
        
        # Agrupa preços similares (±0.5%)
        zones = []
        sorted_prices = sorted(prices)
        
        current_zone = [sorted_prices[0]]
        
        for price in sorted_prices[1:]:
            if price <= current_zone[-1] * 1.005:  # ±0.5%
                current_zone.append(price)
            else:
                if len(current_zone) >= 3:  # Mínimo 3 ocorrências
                    zones.append(np.mean(current_zone))
                current_zone = [price]
        
        # Último zona
        if len(current_zone) >= 3:
            zones.append(np.mean(current_zone))
        
        return zones
    
    def get_recent_alerts(
        self,
        symbol: Optional[str] = None,
        activity_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retorna alertas recentes
        
        Args:
            symbol: Filtrar por símbolo (opcional)
            activity_type: Filtrar por tipo de atividade (opcional)
            limit: Número máximo de resultados
        
        Returns:
            Lista de alertas
        """
        alerts = list(self.whale_alerts)
        
        # Filtra por símbolo
        if symbol:
            alerts = [a for a in alerts if a['symbol'] == symbol]
        
        # Filtra por tipo
        if activity_type:
            alerts = [a for a in alerts if a['type'] == activity_type]
        
        # Ordena por timestamp (mais recentes primeiro)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return alerts[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de atividade de baleias"""
        if not self.whale_alerts:
            return {}
        
        df = pd.DataFrame(list(self.whale_alerts))
        
        return {
            'total_alerts': len(df),
            'by_type': df['type'].value_counts().to_dict(),
            'by_symbol': df['symbol'].value_counts().to_dict(),
            'avg_value_usd': df[df['value_usd'].notna()]['value_usd'].mean(),
            'total_whale_zones': sum(len(zones) for zones in self.whale_zones.values())
        }


# Instância global
whale_monitor = WhaleMonitor()
