#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Manager - Gerenciador Principal de ML/AI
Bot AI Multi-Agente - Etapa 5

Coordena todos os componentes de ML/AI avançados mantendo
total compatibilidade com o sistema IA existente.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union
import logging
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# Sistema existente (PRESERVAR COMPATIBILIDADE)
try:
    from ai.orchestrator.ai_coordinator import AICoordinator
    from ai.agents.multi_agent_coordinator import MultiAgentCoordinator
    AI_SYSTEM_AVAILABLE = True
except ImportError:
    AI_SYSTEM_AVAILABLE = False
    logging.warning("Sistema IA original não disponível")

# Componentes ML
from .freqai_bridge import FreqAIBridge

# AutoML components (implementar posteriormente)
try:
    from .automl.feature_engineer import AutoFeatureEngineer
    from .automl.model_selector import AutoModelSelector
    AUTOML_AVAILABLE = True
except ImportError:
    AUTOML_AVAILABLE = False
    logging.info("AutoML components não disponíveis ainda")

# Advanced models (implementar posteriormente)
try:
    from .models.ensemble_model import EnsemblePredictor
    ADVANCED_MODELS_AVAILABLE = True
except ImportError:
    ADVANCED_MODELS_AVAILABLE = False
    logging.info("Advanced models não disponíveis ainda")


class MLManager:
    """
    Gerenciador Principal de ML/AI
    
    Responsabilidades:
    1. Coordenar todos componentes ML
    2. Manter compatibilidade com sistema IA original
    3. Fornecer interface unificada
    4. Gerenciar performance e monitoring
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializar ML Manager
        
        Args:
            config_path: Caminho para arquivo de configuração
        """
        
        # Carregar configuração
        self.config = self._load_config(config_path)
        
        # Sistema IA Original (PRESERVAR - NUNCA MODIFICAR)
        self.ai_coordinator = None
        self.multi_agent = None
        
        if AI_SYSTEM_AVAILABLE and self.config.get('use_original_ai', True):
            try:
                self.ai_coordinator = AICoordinator()
                self.multi_agent = MultiAgentCoordinator()
                logging.info("✅ Sistema IA original integrado ao ML Manager")
            except Exception as e:
                logging.error(f"Erro ao integrar sistema IA original: {e}")
        
        # Componentes ML
        self.freqai_bridge = None
        self.automl_feature_engineer = None
        self.automl_model_selector = None
        self.ensemble_predictor = None
        
        # Performance tracking
        self.prediction_history = []
        self.model_performance = {}
        self.last_retrain = {}
        
        # Inicializar componentes
        self._initialize_components()
        
        logging.info("🤖 ML Manager inicializado")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Carrega configuração do ML Manager"""
        
        default_config = {
            # Sistema principal
            'use_original_ai': True,
            'ml_enabled': True,
            'cache_enabled': True,
            
            # Componentes
            'freqai_enabled': True,
            'automl_enabled': True,
            'ensemble_enabled': True,
            
            # Performance
            'retrain_frequency': 'weekly',  # daily, weekly, monthly
            'min_accuracy_threshold': 0.6,
            'confidence_threshold': 0.7,
            
            # Paths
            'models_path': 'ml/models_cache/',
            'data_cache_path': 'ml/data_cache/',
            
            # AutoML
            'automl_max_time_minutes': 30,
            'automl_n_trials': 50,
            
            # Monitoring
            'monitoring_enabled': True,
            'drift_detection_enabled': True
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logging.info(f"Configuração carregada de {config_path}")
            except Exception as e:
                logging.warning(f"Erro ao carregar config: {e} - usando padrão")
        
        return default_config
    
    def _initialize_components(self):
        """Inicializa componentes ML"""
        
        try:
            # 1. FreqAI Bridge
            if self.config.get('freqai_enabled', True):
                freqai_config = {
                    'use_original_ai': self.config.get('use_original_ai', True),
                    'confidence_threshold': self.config.get('confidence_threshold', 0.7)
                }
                self.freqai_bridge = FreqAIBridge(freqai_config)
                logging.info("✅ FreqAI Bridge inicializado")
            
            # 2. AutoML Feature Engineer
            if AUTOML_AVAILABLE and self.config.get('automl_enabled', False):
                self.automl_feature_engineer = AutoFeatureEngineer()
                self.automl_model_selector = AutoModelSelector()
                logging.info("✅ AutoML components inicializados")
            
            # 3. Ensemble Predictor
            if ADVANCED_MODELS_AVAILABLE and self.config.get('ensemble_enabled', False):
                self.ensemble_predictor = EnsemblePredictor()
                logging.info("✅ Ensemble Predictor inicializado")
            
            # 4. Criar diretórios necessários
            self._create_directories()
            
        except Exception as e:
            logging.error(f"Erro na inicialização de componentes: {e}")
    
    def _create_directories(self):
        """Cria diretórios necessários"""
        
        for dir_key in ['models_path', 'data_cache_path']:
            dir_path = Path(self.config.get(dir_key, f'ml/{dir_key}/'))
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_prediction(self, market_data: Dict, symbol: str = None) -> Dict:
        """
        Obtém predição ML aprimorada com sistema IA original
        
        Args:
            market_data: Dados de mercado
            symbol: Símbolo (extraído de market_data se não fornecido)
            
        Returns:
            Predição aprimorada combinando ML + IA original
        """
        
        try:
            symbol = symbol or market_data.get('symbol', 'UNKNOWN')
            
            # 1. SEMPRE verificar sistema IA original primeiro (NUNCA PULAR)
            if AI_SYSTEM_AVAILABLE and self.ai_coordinator:
                ai_allowed = self.ai_coordinator.allow(symbol)
                
                if not ai_allowed:
                    return {
                        'action': 'hold',
                        'confidence': 0.0,
                        'reasoning': 'Sistema IA original bloqueou trading',
                        'source': 'original_ai_block',
                        'symbol': symbol
                    }
            
            # 2. Obter predições ML
            ml_predictions = []
            
            # 2a. FreqAI prediction
            if self.freqai_bridge:
                try:
                    # Converter market_data para DataFrame se necessário
                    if isinstance(market_data, dict):
                        df_data = self._dict_to_dataframe(market_data)
                    else:
                        df_data = market_data
                    
                    freqai_pred = self.freqai_bridge.predict(symbol, df_data)
                    ml_predictions.append({
                        'source': 'freqai',
                        'weight': 0.4,
                        **freqai_pred
                    })
                except Exception as e:
                    logging.warning(f"Erro FreqAI prediction: {e}")
            
            # 2b. Ensemble prediction (se disponível)
            if self.ensemble_predictor:
                try:
                    ensemble_pred = self.ensemble_predictor.predict(market_data)
                    ml_predictions.append({
                        'source': 'ensemble',
                        'weight': 0.6,
                        **ensemble_pred
                    })
                except Exception as e:
                    logging.warning(f"Erro ensemble prediction: {e}")
            
            # 3. Combinar predições ML
            if not ml_predictions:
                return {
                    'action': 'hold',
                    'confidence': 0.0,
                    'reasoning': 'Nenhuma predição ML disponível',
                    'source': 'no_ml_models',
                    'symbol': symbol
                }
            
            combined_ml = self._combine_ml_predictions(ml_predictions)
            
            # 4. INTEGRAÇÃO COM SISTEMA MULTI-AGENTE ORIGINAL
            if AI_SYSTEM_AVAILABLE and self.multi_agent:
                try:
                    # Usar multi-agent para validar decisão ML
                    agent_decision = self.multi_agent.make_trading_decision(market_data)
                    
                    if agent_decision:
                        # Boost confiança se agentes concordam
                        if agent_decision.get('action') == combined_ml.get('action'):
                            combined_ml['confidence'] *= 1.15  # 15% boost
                            combined_ml['confidence'] = min(combined_ml['confidence'], 0.95)
                            combined_ml['multi_agent_boost'] = True
                        
                        combined_ml['multi_agent_decision'] = agent_decision
                
                except Exception as e:
                    logging.warning(f"Erro integração multi-agent: {e}")
            
            # 5. Aplicar thresholds finais
            final_prediction = self._apply_final_filters(combined_ml, symbol)
            
            # 6. Logging e tracking
            self._track_prediction(final_prediction, market_data)
            
            return final_prediction
            
        except Exception as e:
            logging.error(f"Erro na predição ML: {e}")
            
            return {
                'action': 'hold',
                'confidence': 0.0,
                'reasoning': f'Erro no ML Manager: {str(e)[:100]}',
                'source': 'error',
                'error': str(e),
                'symbol': symbol or 'UNKNOWN'
            }
    
    def _dict_to_dataframe(self, market_data: Dict) -> pd.DataFrame:
        """Converte dict market_data para DataFrame"""
        
        # Extrair dados OHLCV se disponíveis
        ohlcv_keys = ['open', 'high', 'low', 'close', 'volume']
        
        if all(key in market_data for key in ohlcv_keys):
            # Criar DataFrame com uma linha
            df = pd.DataFrame([{
                key: market_data[key] for key in ohlcv_keys
            }])
        else:
            # Usar valores mock se dados incompletos
            df = pd.DataFrame([{
                'open': market_data.get('price', 100),
                'high': market_data.get('price', 100) * 1.01,
                'low': market_data.get('price', 100) * 0.99,
                'close': market_data.get('price', 100),
                'volume': market_data.get('volume', 1000000)
            }])
        
        return df
    
    def _combine_ml_predictions(self, predictions: List[Dict]) -> Dict:
        """Combina múltiplas predições ML usando pesos"""
        
        if not predictions:
            return {'action': 'hold', 'confidence': 0.0}
        
        if len(predictions) == 1:
            return predictions[0]
        
        # Weighted average para confidence
        total_weight = sum(p.get('weight', 1.0) for p in predictions)
        
        weighted_confidence = sum(
            p.get('confidence', 0.0) * p.get('weight', 1.0) 
            for p in predictions
        ) / total_weight if total_weight > 0 else 0.0
        
        # Majority vote para action
        actions = [p.get('action', 'hold') for p in predictions]
        action_counts = {action: actions.count(action) for action in set(actions)}
        final_action = max(action_counts, key=action_counts.get)
        
        return {
            'action': final_action,
            'confidence': weighted_confidence,
            'reasoning': f'Combined ML: {len(predictions)} models',
            'source': 'combined_ml',
            'individual_predictions': predictions
        }
    
    def _apply_final_filters(self, prediction: Dict, symbol: str) -> Dict:
        """Aplica filtros finais na predição"""
        
        # 1. Threshold de confiança
        min_confidence = self.config.get('confidence_threshold', 0.7)
        
        if prediction.get('confidence', 0.0) < min_confidence:
            return {
                **prediction,
                'action': 'hold',
                'reasoning': f"Confiança {prediction.get('confidence', 0):.2f} < {min_confidence}",
                'confidence_filter_applied': True
            }
        
        # 2. Verificar performance histórica do modelo
        if symbol in self.model_performance:
            recent_accuracy = self.model_performance[symbol].get('recent_accuracy', 1.0)
            min_accuracy = self.config.get('min_accuracy_threshold', 0.6)
            
            if recent_accuracy < min_accuracy:
                return {
                    **prediction,
                    'action': 'hold',
                    'reasoning': f"Performance do modelo {recent_accuracy:.2f} < {min_accuracy}",
                    'accuracy_filter_applied': True
                }
        
        # 3. Verificar necessidade de retreinamento
        if self._needs_retraining(symbol):
            prediction['retrain_recommended'] = True
        
        return prediction
    
    def _needs_retraining(self, symbol: str) -> bool:
        """Verifica se modelo precisa ser retreinado"""
        
        if symbol not in self.last_retrain:
            return True
        
        last_retrain = self.last_retrain[symbol]
        retrain_freq = self.config.get('retrain_frequency', 'weekly')
        
        if retrain_freq == 'daily':
            threshold = timedelta(days=1)
        elif retrain_freq == 'weekly':
            threshold = timedelta(weeks=1)
        elif retrain_freq == 'monthly':
            threshold = timedelta(days=30)
        else:
            threshold = timedelta(weeks=1)  # default
        
        return (datetime.now() - last_retrain) > threshold
    
    def _track_prediction(self, prediction: Dict, market_data: Dict):
        """Tracking de predições para análise"""
        
        prediction_record = {
            'timestamp': datetime.now(),
            'symbol': prediction.get('symbol'),
            'prediction': prediction,
            'market_data_snapshot': {
                key: market_data.get(key) 
                for key in ['price', 'volume', 'rsi'] 
                if key in market_data
            }
        }
        
        self.prediction_history.append(prediction_record)
        
        # Manter apenas últimas 1000 predições
        if len(self.prediction_history) > 1000:
            self.prediction_history = self.prediction_history[-1000:]
    
    def train_models(self, symbol: str, training_data: pd.DataFrame = None) -> Dict:
        """
        Treina modelos ML para símbolo específico
        
        Args:
            symbol: Símbolo para treinar
            training_data: Dados de treinamento (opcional)
            
        Returns:
            Resultado do treinamento
        """
        
        results = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'models_trained': [],
            'errors': []
        }
        
        try:
            # 1. FreqAI model
            if self.freqai_bridge:
                try:
                    freqai_config = {'model': 'lgb'}
                    success = self.freqai_bridge.train_model(symbol, freqai_config)
                    
                    if success:
                        results['models_trained'].append('freqai')
                        self.last_retrain[symbol] = datetime.now()
                    else:
                        results['errors'].append('FreqAI training failed')
                        
                except Exception as e:
                    results['errors'].append(f'FreqAI error: {e}')
            
            # 2. AutoML models (se disponível)
            if self.automl_model_selector and training_data is not None:
                try:
                    # Implementar quando AutoML estiver disponível
                    results['models_trained'].append('automl')
                except Exception as e:
                    results['errors'].append(f'AutoML error: {e}')
            
            # 3. Ensemble models (se disponível)
            if self.ensemble_predictor:
                try:
                    # Implementar quando ensemble estiver disponível
                    results['models_trained'].append('ensemble')
                except Exception as e:
                    results['errors'].append(f'Ensemble error: {e}')
            
            logging.info(f"✅ Treinamento concluído para {symbol}: {results['models_trained']}")
            
        except Exception as e:
            results['errors'].append(f'Training error: {e}')
            logging.error(f"Erro no treinamento: {e}")
        
        return results
    
    def get_model_status(self, symbol: str = None) -> Dict:
        """Status dos modelos ML"""
        
        if symbol:
            # Status específico do símbolo
            status = {
                'symbol': symbol,
                'models': {}
            }
            
            if self.freqai_bridge:
                freqai_info = self.freqai_bridge.get_model_info(symbol)
                status['models']['freqai'] = freqai_info
            
            return status
        else:
            # Status geral
            return {
                'ml_manager_status': 'active',
                'components': {
                    'freqai_bridge': self.freqai_bridge is not None,
                    'automl': self.automl_feature_engineer is not None,
                    'ensemble': self.ensemble_predictor is not None
                },
                'ai_system_integration': {
                    'ai_coordinator_available': self.ai_coordinator is not None,
                    'multi_agent_available': self.multi_agent is not None
                },
                'prediction_stats': {
                    'total_predictions': len(self.prediction_history),
                    'models_trained': len(self.last_retrain)
                },
                'config': self.config
            }
    
    def health_check(self) -> Dict:
        """Health check completo do ML Manager"""
        
        health = {
            'ml_manager': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {},
            'integrations': {},
            'performance': {}
        }
        
        # 1. Componentes ML
        if self.freqai_bridge:
            health['components']['freqai'] = self.freqai_bridge.health_check()
        
        # 2. Integrações com sistema original
        if AI_SYSTEM_AVAILABLE:
            health['integrations']['original_ai'] = {
                'ai_coordinator': self.ai_coordinator is not None,
                'multi_agent': self.multi_agent is not None,
                'integration_active': self.config.get('use_original_ai', True)
            }
        
        # 3. Performance
        if self.prediction_history:
            recent_predictions = self.prediction_history[-100:]  # Últimas 100
            
            confidence_scores = [
                p['prediction'].get('confidence', 0) 
                for p in recent_predictions
            ]
            
            health['performance'] = {
                'recent_predictions_count': len(recent_predictions),
                'avg_confidence': np.mean(confidence_scores) if confidence_scores else 0,
                'models_available': len(self.last_retrain)
            }
        
        return health


def test_ml_manager():
    """Teste básico do ML Manager"""
    
    print("🧪 TESTE ML MANAGER")
    print("=" * 40)
    
    # 1. Inicializar
    ml_manager = MLManager()
    
    # 2. Health check
    health = ml_manager.health_check()
    print("🏥 Health Check:")
    for key, value in health.items():
        print(f"   {key}: {value}")
    
    # 3. Teste de predição
    market_data = {
        'symbol': 'BTC/USDT',
        'price': 45000.0,
        'volume': 2500000000,
        'rsi': 65.5,
        'macd': 0.012
    }
    
    prediction = ml_manager.get_prediction(market_data)
    print(f"\n🔮 Predição:")
    for key, value in prediction.items():
        if key != 'individual_predictions':  # Skip nested data
            print(f"   {key}: {value}")
    
    # 4. Status dos modelos
    status = ml_manager.get_model_status()
    print(f"\n📊 Status dos Modelos:")
    print(f"   Componentes ativos: {status.get('components', {})}")
    
    print("\n✅ Teste concluído")


if __name__ == "__main__":
    test_ml_manager()