#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreqAI Bridge - Integração com ecossistema FreqAI
Bot AI Multi-Agente - Etapa 5

Este módulo cria uma bridge compatível com FreqAI mantendo total
compatibilidade com o sistema IA existente.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import logging
import os
from datetime import datetime, timedelta

# Imports do sistema existente (PRESERVAR COMPATIBILIDADE)
try:
    from ai.orchestrator.ai_coordinator import AICoordinator
    from ai.agents.multi_agent_coordinator import MultiAgentCoordinator
    AI_SYSTEM_AVAILABLE = True
except ImportError:
    AI_SYSTEM_AVAILABLE = False
    logging.warning("Sistema IA original não disponível - FreqAI rodará em modo standalone")

# ML imports
try:
    import lightgbm as lgb
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    ML_LIBS_AVAILABLE = True
except ImportError:
    ML_LIBS_AVAILABLE = False
    logging.warning("Bibliotecas ML não disponíveis - instale: pip install lightgbm xgboost scikit-learn")


class FreqAIBridge:
    """
    Bridge para compatibilidade com FreqAI
    
    IMPORTANTE: Este componente INTEGRA com sistema IA existente,
    NÃO substitui. O sistema original continua funcionando normalmente.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializar FreqAI Bridge
        
        Args:
            config: Configuração do bridge (opcional)
        """
        self.config = config or self._get_default_config()
        
        # Sistema IA original (PRESERVAR)
        self.ai_coordinator = None
        self.multi_agent = None
        
        if AI_SYSTEM_AVAILABLE:
            try:
                self.ai_coordinator = AICoordinator()
                self.multi_agent = MultiAgentCoordinator()
                logging.info("✅ Sistema IA original integrado ao FreqAI Bridge")
            except Exception as e:
                logging.warning(f"Erro ao integrar sistema IA: {e}")
        
        # Componentes ML
        self.models = {}
        self.feature_cache = {}
        self.scaler = StandardScaler() if ML_LIBS_AVAILABLE else None
        
        # Métricas
        self.predictions_made = 0
        self.accuracy_history = []
        
        logging.info("🔗 FreqAI Bridge inicializado")
    
    def _get_default_config(self) -> Dict:
        """Configuração padrão do FreqAI Bridge"""
        return {
            'model_type': 'lgb',  # lgb, xgb, catboost
            'feature_engineering': 'basic',  # basic, advanced
            'lookback_periods': [5, 10, 20],
            'retrain_frequency': 'daily',
            'confidence_threshold': 0.7,
            'use_original_ai': True,  # SEMPRE usar sistema original
            'fallback_strategy': 'conservative'
        }
    
    def enhance_with_original_ai(self, symbol: str, ml_decision: Dict) -> Dict:
        """
        Aprimora decisão ML com sistema IA original
        
        Esta é a função CHAVE que mantém compatibilidade total
        
        Args:
            symbol: Símbolo para análise
            ml_decision: Decisão do modelo ML
            
        Returns:
            Decisão aprimorada combinando ML + IA original
        """
        
        if not AI_SYSTEM_AVAILABLE or not self.config['use_original_ai']:
            return ml_decision
        
        try:
            # 1. Verificar sistema IA original (NUNCA SUBSTITUIR)
            ai_allowed = self.ai_coordinator.allow(symbol)
            
            if not ai_allowed:
                return {
                    'action': 'hold',
                    'confidence': 0.0,
                    'reasoning': 'Sistema IA original bloqueou o símbolo',
                    'ml_prediction': ml_decision,
                    'ai_blocked': True
                }
            
            # 2. Se IA permite, usar predição ML aprimorada
            enhanced_confidence = ml_decision.get('confidence', 0.0)
            
            # 3. Aplicar boost de confiança se IA concorda
            if ml_decision.get('action') in ['buy', 'sell']:
                enhanced_confidence *= 1.1  # 10% boost por concordância IA
                enhanced_confidence = min(enhanced_confidence, 0.95)  # Cap em 95%
            
            return {
                'action': ml_decision.get('action', 'hold'),
                'confidence': enhanced_confidence,
                'reasoning': f"ML + IA original: {ml_decision.get('reasoning', 'ML prediction')}",
                'ml_prediction': ml_decision,
                'ai_enhanced': True,
                'original_ai_allowed': ai_allowed
            }
            
        except Exception as e:
            logging.error(f"Erro na integração IA original: {e}")
            
            # Fallback para decisão ML pura
            return {
                **ml_decision,
                'ai_integration_error': str(e),
                'fallback_mode': True
            }
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
        """
        FreqAI-style indicator population
        
        Args:
            dataframe: OHLCV DataFrame
            metadata: Metadata com informações do símbolo
            
        Returns:
            DataFrame com indicadores
        """
        
        if dataframe.empty:
            return dataframe
        
        try:
            # Indicadores técnicos básicos
            dataframe = self._add_technical_indicators(dataframe)
            
            # Features estatísticas
            dataframe = self._add_statistical_features(dataframe)
            
            # Features temporais  
            dataframe = self._add_temporal_features(dataframe)
            
            # Cache features para reutilização
            symbol = metadata.get('pair', 'UNKNOWN')
            self.feature_cache[symbol] = {
                'timestamp': datetime.now(),
                'features': list(dataframe.columns)
            }
            
            logging.debug(f"Generated {len(dataframe.columns)} features for {symbol}")
            
            return dataframe
            
        except Exception as e:
            logging.error(f"Erro na geração de indicadores: {e}")
            return dataframe
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona indicadores técnicos"""
        
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Moving Averages
            df['sma_10'] = df['close'].rolling(window=10).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['ema_10'] = df['close'].ewm(span=10).mean()
            df['ema_20'] = df['close'].ewm(span=20).mean()
            
            return df
            
        except Exception as e:
            logging.error(f"Erro em indicadores técnicos: {e}")
            return df
    
    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features estatísticas"""
        
        try:
            # Volatility features
            df['volatility_10'] = df['close'].rolling(window=10).std()
            df['volatility_20'] = df['close'].rolling(window=20).std()
            
            # Price ratios
            df['high_low_ratio'] = df['high'] / df['low']
            df['close_open_ratio'] = df['close'] / df['open']
            
            # Volume features
            df['volume_sma_10'] = df['volume'].rolling(window=10).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma_10']
            
            # Price changes
            for period in [1, 3, 5, 10]:
                df[f'price_change_{period}'] = df['close'].pct_change(period)
                df[f'volume_change_{period}'] = df['volume'].pct_change(period)
            
            return df
            
        except Exception as e:
            logging.error(f"Erro em features estatísticas: {e}")
            return df
    
    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features temporais"""
        
        try:
            # Assumindo que 'timestamp' está no index ou como coluna
            if 'timestamp' in df.columns:
                timestamps = pd.to_datetime(df['timestamp'])
            elif hasattr(df.index, 'to_pydatetime'):
                timestamps = pd.to_datetime(df.index)
            else:
                # Fallback - criar timestamps baseado em índice
                timestamps = pd.date_range(
                    start=datetime.now() - timedelta(hours=len(df)),
                    periods=len(df),
                    freq='H'
                )
            
            # Features de tempo
            df['hour'] = timestamps.hour
            df['day_of_week'] = timestamps.dayofweek
            df['month'] = timestamps.month
            
            # Features cíclicas
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
            
            return df
            
        except Exception as e:
            logging.error(f"Erro em features temporais: {e}")
            return df
    
    def train_model(self, symbol: str, config: Dict) -> bool:
        """
        Treina modelo ML para símbolo específico
        
        Args:
            symbol: Símbolo para treinar (ex: 'BTC/USDT')
            config: Configuração do modelo
            
        Returns:
            True se treinamento foi bem-sucedido
        """
        
        if not ML_LIBS_AVAILABLE:
            logging.error("Bibliotecas ML não disponíveis")
            return False
        
        try:
            logging.info(f"🏋️ Treinando modelo ML para {symbol}")
            
            # 1. Obter dados históricos (mock por enquanto)
            # Em implementação real, conectar com data manager
            training_data = self._get_training_data(symbol)
            
            if training_data.empty:
                logging.error(f"Nenhum dado de treinamento para {symbol}")
                return False
            
            # 2. Feature engineering
            features_df = self.populate_indicators(training_data, {'pair': symbol})
            
            # 3. Preparar targets (exemplo: predizer direção do preço)
            features_df = self._prepare_targets(features_df)
            
            # 4. Limpar dados
            features_df = features_df.dropna()
            
            if len(features_df) < 100:
                logging.error(f"Dados insuficientes para treinar {symbol}")
                return False
            
            # 5. Separar features e targets
            target_cols = [col for col in features_df.columns if col.startswith('target_')]
            feature_cols = [col for col in features_df.columns if not col.startswith('target_')]
            
            X = features_df[feature_cols]
            y = features_df[target_cols[0]] if target_cols else None
            
            if y is None:
                logging.error("Nenhum target encontrado")
                return False
            
            # 6. Split treino/teste
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # 7. Normalização
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # 8. Treinar modelo
            model_type = config.get('model', 'lgb')
            
            if model_type == 'lgb':
                model = lgb.LGBMClassifier(
                    objective='binary',
                    n_estimators=100,
                    random_state=42,
                    verbosity=-1
                )
            elif model_type == 'xgb':
                model = xgb.XGBClassifier(
                    objective='binary:logistic',
                    n_estimators=100,
                    random_state=42
                )
            else:
                logging.error(f"Tipo de modelo não suportado: {model_type}")
                return False
            
            # 9. Fit modelo
            model.fit(X_train_scaled, y_train)
            
            # 10. Avaliar
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            logging.info(f"✅ Modelo treinado para {symbol} - Accuracy: {accuracy:.3f}")
            
            # 11. Salvar modelo
            self.models[symbol] = {
                'model': model,
                'scaler': self.scaler,
                'features': feature_cols,
                'accuracy': accuracy,
                'trained_at': datetime.now(),
                'config': config
            }
            
            return True
            
        except Exception as e:
            logging.error(f"Erro no treinamento do modelo: {e}")
            return False
    
    def predict(self, symbol: str, current_data: pd.DataFrame) -> Dict:
        """
        Faz predição para símbolo específico
        
        Args:
            symbol: Símbolo para predição
            current_data: Dados atuais de mercado
            
        Returns:
            Predição com confiança e ação recomendada
        """
        
        try:
            # 1. Verificar se modelo existe
            if symbol not in self.models:
                return {
                    'action': 'hold',
                    'confidence': 0.0,
                    'reasoning': f'Modelo não treinado para {symbol}'
                }
            
            model_info = self.models[symbol]
            model = model_info['model']
            scaler = model_info['scaler']
            required_features = model_info['features']
            
            # 2. Processar dados atuais
            processed_data = self.populate_indicators(current_data.copy(), {'pair': symbol})
            
            # 3. Verificar features necessárias
            missing_features = set(required_features) - set(processed_data.columns)
            if missing_features:
                logging.warning(f"Features faltando: {missing_features}")
                return {
                    'action': 'hold',
                    'confidence': 0.0,
                    'reasoning': f'Features faltando: {list(missing_features)[:3]}...'
                }
            
            # 4. Preparar features
            X = processed_data[required_features].iloc[-1:].values  # Última linha
            
            # 5. Verificar NaN
            if np.isnan(X).any():
                return {
                    'action': 'hold',
                    'confidence': 0.0,
                    'reasoning': 'Dados contêm NaN - aguardando dados completos'
                }
            
            # 6. Normalizar
            X_scaled = scaler.transform(X)
            
            # 7. Predição
            prediction_proba = model.predict_proba(X_scaled)[0]
            prediction = model.predict(X_scaled)[0]
            
            # 8. Interpretar resultado
            confidence = max(prediction_proba)
            action = 'buy' if prediction == 1 else 'sell'
            
            ml_decision = {
                'action': action,
                'confidence': float(confidence),
                'reasoning': f'ML Model prediction (accuracy: {model_info["accuracy"]:.2f})',
                'model_type': model_info['config'].get('model', 'unknown'),
                'prediction_proba': prediction_proba.tolist()
            }
            
            # 9. INTEGRAR COM SISTEMA IA ORIGINAL
            final_decision = self.enhance_with_original_ai(symbol, ml_decision)
            
            # 10. Atualizar métricas
            self.predictions_made += 1
            
            return final_decision
            
        except Exception as e:
            logging.error(f"Erro na predição ML: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f'Erro na predição: {str(e)[:100]}...',
                'error': str(e)
            }
    
    def _get_training_data(self, symbol: str) -> pd.DataFrame:
        """
        Obter dados de treinamento (mock implementation)
        
        Em implementação real, conectar com data manager do sistema
        """
        
        # Mock data para exemplo
        np.random.seed(42)
        n_samples = 1000
        
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=n_samples//24),
            periods=n_samples,
            freq='H'
        )
        
        # Simular dados OHLCV
        base_price = 45000 if 'BTC' in symbol else 3000
        
        mock_data = pd.DataFrame({
            'timestamp': dates,
            'open': base_price + np.random.randn(n_samples) * 100,
            'high': base_price + np.random.randn(n_samples) * 100 + 50,
            'low': base_price + np.random.randn(n_samples) * 100 - 50,
            'close': base_price + np.random.randn(n_samples) * 100,
            'volume': np.random.randint(1000000, 10000000, n_samples)
        })
        
        # Ensure high >= low
        mock_data['high'] = np.maximum(mock_data['high'], mock_data[['open', 'close']].max(axis=1))
        mock_data['low'] = np.minimum(mock_data['low'], mock_data[['open', 'close']].min(axis=1))
        
        return mock_data
    
    def _prepare_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara targets para treinamento"""
        
        try:
            # Target: predizer se preço vai subir na próxima hora
            df['price_future'] = df['close'].shift(-1)
            df['target_direction'] = (df['price_future'] > df['close']).astype(int)
            
            # Remove última linha (sem target)
            df = df[:-1]
            
            return df
            
        except Exception as e:
            logging.error(f"Erro ao preparar targets: {e}")
            return df
    
    def get_model_info(self, symbol: str) -> Optional[Dict]:
        """Informações do modelo treinado"""
        
        if symbol not in self.models:
            return None
        
        model_info = self.models[symbol]
        
        return {
            'symbol': symbol,
            'model_type': model_info['config'].get('model', 'unknown'),
            'accuracy': model_info['accuracy'],
            'trained_at': model_info['trained_at'],
            'features_count': len(model_info['features']),
            'predictions_made': self.predictions_made
        }
    
    def health_check(self) -> Dict:
        """Health check do FreqAI Bridge"""
        
        return {
            'freqai_bridge_status': 'healthy',
            'ml_libs_available': ML_LIBS_AVAILABLE,
            'ai_system_available': AI_SYSTEM_AVAILABLE,
            'models_trained': len(self.models),
            'predictions_made': self.predictions_made,
            'original_ai_integration': self.config['use_original_ai'],
            'config': self.config
        }


def test_freqai_bridge():
    """Teste básico do FreqAI Bridge"""
    
    print("🧪 TESTE FREQAI BRIDGE")
    print("=" * 40)
    
    # 1. Inicializar
    bridge = FreqAIBridge()
    
    # 2. Health check
    health = bridge.health_check()
    print("🏥 Health Check:")
    for key, value in health.items():
        print(f"   {key}: {value}")
    
    # 3. Teste de features
    mock_data = pd.DataFrame({
        'open': [100, 101, 102, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'close': [100.5, 101.5, 102.5, 103.5, 104.5],
        'volume': [1000, 1100, 1200, 1300, 1400]
    })
    
    features = bridge.populate_indicators(mock_data, {'pair': 'BTC/USDT'})
    print(f"\n📊 Features geradas: {len(features.columns)}")
    
    # 4. Teste de treinamento
    if ML_LIBS_AVAILABLE:
        success = bridge.train_model('BTC/USDT', {'model': 'lgb'})
        print(f"🏋️ Treinamento: {'✅' if success else '❌'}")
        
        # 5. Teste de predição
        if success:
            prediction = bridge.predict('BTC/USDT', mock_data)
            print(f"🔮 Predição: {prediction}")
    else:
        print("⚠️ ML libs não disponíveis - instale dependências")
    
    print("\n✅ Teste concluído")


if __name__ == "__main__":
    test_freqai_bridge()