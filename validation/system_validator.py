#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Validator - Etapa 7
Validador geral do sistema completo
"""

import os
import sys
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Adiciona path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class SystemValidator:
    """
    Validador completo do sistema
    Verifica integridade e funcionamento de todos os componentes
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Componentes para validar
        self.components_to_validate = [
            'core_engine',
            'ai_system', 
            'ml_system',
            'risk_management',
            'exchange_integration',
            'backtesting',
            'interfaces',
            'documentation',
            'configuration'
        ]
        
        # Resultados de validação
        self.validation_results = {}
        
    def setup_logging(self):
        """Configura logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    def validate_complete_system(self) -> Dict[str, Any]:
        """Valida sistema completo"""
        
        self.logger.info("🔍 Iniciando validação completa do sistema...")
        
        system_validation = {
            'timestamp': datetime.now().isoformat(),
            'validator_version': '1.0.0',
            'components_validated': {},
            'overall_health_score': 0,
            'critical_issues': [],
            'recommendations': [],
            'system_ready': False
        }
        
        # Valida cada componente
        for component in self.components_to_validate:
            self.logger.info(f"Validando {component}...")
            try:
                result = self._validate_component(component)
                system_validation['components_validated'][component] = result
            except Exception as e:
                self.logger.error(f"Erro validando {component}: {e}")
                system_validation['components_validated'][component] = {
                    'status': 'error',
                    'error': str(e),
                    'score': 0
                }
        
        # Calcula score geral e status
        self._calculate_overall_health(system_validation)
        
        # Gera recomendações
        self._generate_recommendations(system_validation)
        
        self.validation_results = system_validation
        
        health_score = system_validation['overall_health_score']
        status = "✅ SAUDÁVEL" if health_score >= 80 else "⚠️  REQUER ATENÇÃO" if health_score >= 60 else "❌ CRÍTICO"
        
        self.logger.info(f"Validação concluída - {status} ({health_score:.1f}/100)")
        
        return system_validation
    
    def _validate_component(self, component: str) -> Dict[str, Any]:
        """Valida um componente específico"""
        
        validation_methods = {
            'core_engine': self._validate_core_engine,
            'ai_system': self._validate_ai_system,
            'ml_system': self._validate_ml_system,
            'risk_management': self._validate_risk_management,
            'exchange_integration': self._validate_exchange_integration,
            'backtesting': self._validate_backtesting,
            'interfaces': self._validate_interfaces,
            'documentation': self._validate_documentation,
            'configuration': self._validate_configuration
        }
        
        if component in validation_methods:
            return validation_methods[component]()
        else:
            return {'status': 'unknown', 'score': 0, 'message': f'Componente {component} não reconhecido'}
    
    def _validate_core_engine(self) -> Dict[str, Any]:
        """Valida motor principal"""
        
        validation = {
            'component': 'core_engine',
            'status': 'checking',
            'checks': {},
            'score': 0
        }
        
        # Verifica arquivos principais
        core_files = [
            '/app/core/engine/bot_engine.py',
            '/app/bot_runner.py',
            '/app/bot_runner_modular.py'
        ]
        
        files_exist = 0
        for file_path in core_files:
            exists = Path(file_path).exists()
            validation['checks'][f'file_{Path(file_path).name}'] = exists
            if exists:
                files_exist += 1
        
        # Calcula score
        score = (files_exist / len(core_files)) * 100
        
        validation['status'] = 'healthy' if score >= 80 else 'warning' if score >= 60 else 'critical'
        validation['score'] = score
        validation['files_found'] = files_exist
        validation['files_expected'] = len(core_files)
        
        return validation
    
    def _validate_ai_system(self) -> Dict[str, Any]:
        """Valida sistema de IA"""
        
        validation = {
            'component': 'ai_system',
            'status': 'checking',
            'checks': {},
            'score': 0
        }
        
        # Verifica estrutura AI
        ai_paths = [
            '/app/ai',
            '/app/ai/orchestrator',
            '/app/ai/agents'
        ]
        
        paths_exist = 0
        for ai_path in ai_paths:
            exists = Path(ai_path).exists()
            validation['checks'][f'path_{Path(ai_path).name}'] = exists
            if exists:
                paths_exist += 1
        
        # Score baseado em estrutura
        score = (paths_exist / len(ai_paths)) * 100
        
        validation['status'] = 'healthy' if score >= 80 else 'warning' if score >= 60 else 'critical'
        validation['score'] = score
        
        return validation
    
    def _validate_ml_system(self) -> Dict[str, Any]:
        """Valida sistema de ML"""
        
        validation = {
            'component': 'ml_system',
            'status': 'checking',
            'checks': {},
            'score': 0
        }
        
        # Verifica estrutura ML
        ml_components = [
            '/app/ml/ml_manager.py',
            '/app/ml/freqai_bridge.py',
            '/app/ml/automl',
            '/app/ml/models'
        ]
        
        components_exist = 0
        for component in ml_components:
            exists = Path(component).exists()
            validation['checks'][f'component_{Path(component).name}'] = exists
            if exists:
                components_exist += 1
        
        # Calcula score
        score = (components_exist / len(ml_components)) * 100
        
        validation['status'] = 'healthy' if score >= 70 else 'warning' if score >= 50 else 'critical'
        validation['score'] = score
        
        return validation
    
    def _validate_risk_management(self) -> Dict[str, Any]:
        """Valida sistema de risk management"""
        
        validation = {
            'component': 'risk_management',
            'status': 'checking',
            'checks': {},
            'score': 0
        }
        
        # Verifica estrutura de risk
        risk_components = [
            '/app/risk/managers/risk_manager.py',
            '/app/risk/managers/advanced_protection_manager.py',
            '/app/risk/protections/protection_manager.py'
        ]
        
        components_exist = 0
        for component in risk_components:
            exists = Path(component).exists()
            validation['checks'][f'component_{Path(component).name}'] = exists
            if exists:
                components_exist += 1
        
        # Calcula score
        score = (components_exist / len(risk_components)) * 100
        
        validation['status'] = 'healthy' if score >= 80 else 'warning' if score >= 60 else 'critical'
        validation['score'] = score
        
        return validation
    
    def _validate_exchange_integration(self) -> Dict[str, Any]:
        """Valida integração com exchanges"""
        
        validation = {
            'component': 'exchange_integration',
            'status': 'checking',
            'checks': {},
            'score': 0
        }
        
        # Verifica estrutura de exchanges
        exchange_components = [
            '/app/core/exchanges/exchange_manager.py',
            '/app/exchanges'
        ]
        
        components_exist = 0
        for component in exchange_components:
            exists = Path(component).exists()
            validation['checks'][f'component_{Path(component).name}'] = exists
            if exists:
                components_exist += 1
        
        # Calcula score
        score = (components_exist / len(exchange_components)) * 100
        
        validation['status'] = 'healthy' if score >= 75 else 'warning' if score >= 50 else 'critical'
        validation['score'] = score
        
        return validation
    
    def _validate_backtesting(self) -> Dict[str, Any]:
        """Valida sistema de backtesting"""
        
        validation = {
            'component': 'backtesting',
            'status': 'checking',
            'checks': {},
            'score': 0
        }
        
        # Verifica estrutura de backtest
        backtest_path = Path('/app/backtest')
        validation['checks']['backtest_directory'] = backtest_path.exists()
        
        if backtest_path.exists():
            # Verifica arquivos de backtesting
            backtest_files = list(backtest_path.glob('*.py'))
            validation['checks']['backtest_files_count'] = len(backtest_files)
            validation['checks']['has_backtest_files'] = len(backtest_files) > 0
        else:
            validation['checks']['backtest_files_count'] = 0
            validation['checks']['has_backtest_files'] = False
        
        # Score baseado na presença de estrutura
        score = 80 if validation['checks'].get('backtest_directory', False) else 0
        if validation['checks'].get('has_backtest_files', False):
            score += 20
        
        validation['status'] = 'healthy' if score >= 80 else 'warning' if score >= 40 else 'critical'
        validation['score'] = score
        
        return validation
    
    def _validate_interfaces(self) -> Dict[str, Any]:
        """Valida interfaces (API, Web)"""
        
        validation = {
            'component': 'interfaces',
            'status': 'checking',
            'checks': {},
            'score': 0
        }
        
        # Verifica estrutura de interfaces
        interface_components = [
            '/app/interfaces/api/main.py',
            '/app/interfaces/web/app.py'
        ]
        
        components_exist = 0
        for component in interface_components:
            exists = Path(component).exists()
            validation['checks'][f'component_{Path(component).name}'] = exists
            if exists:
                components_exist += 1
        
        # Calcula score
        score = (components_exist / len(interface_components)) * 100
        
        validation['status'] = 'healthy' if score >= 80 else 'warning' if score >= 60 else 'critical'
        validation['score'] = score
        
        return validation
    
    def _validate_documentation(self) -> Dict[str, Any]:
        """Valida documentação"""
        
        validation = {
            'component': 'documentation',
            'status': 'checking',
            'checks': {},
            'score': 0
        }
        
        # Verifica estrutura de documentação
        docs_path = Path('/app/docs')
        validation['checks']['docs_directory'] = docs_path.exists()
        
        if docs_path.exists():
            # Verifica seções principais
            doc_sections = [
                'getting_started',
                'user_guide', 
                'developer_guide',
                'examples'
            ]
            
            sections_exist = 0
            for section in doc_sections:
                section_path = docs_path / section
                exists = section_path.exists()
                validation['checks'][f'docs_{section}'] = exists
                if exists:
                    sections_exist += 1
            
            # Verifica README principal
            readme_exists = (docs_path / 'README.md').exists()
            validation['checks']['docs_readme'] = readme_exists
            
            # Calcula score
            sections_score = (sections_exist / len(doc_sections)) * 80
            readme_score = 20 if readme_exists else 0
            score = sections_score + readme_score
            
        else:
            score = 0
        
        validation['status'] = 'healthy' if score >= 80 else 'warning' if score >= 60 else 'critical'
        validation['score'] = score
        
        return validation
    
    def _validate_configuration(self) -> Dict[str, Any]:
        """Valida sistema de configuração"""
        
        validation = {
            'component': 'configuration',
            'status': 'checking',
            'checks': {},
            'score': 0
        }
        
        # Verifica arquivos de configuração principais
        config_files = [
            '/app/.env',
            '/app/config/settings/config_manager.py',
            '/app/requirements.txt'
        ]
        
        files_exist = 0
        for config_file in config_files:
            exists = Path(config_file).exists()
            validation['checks'][f'config_{Path(config_file).name}'] = exists
            if exists:
                files_exist += 1
        
        # Calcula score
        score = (files_exist / len(config_files)) * 100
        
        validation['status'] = 'healthy' if score >= 80 else 'warning' if score >= 60 else 'critical'
        validation['score'] = score
        
        return validation
    
    def _calculate_overall_health(self, system_validation: Dict[str, Any]):
        """Calcula score geral de saúde do sistema"""
        
        component_scores = []
        critical_issues = []
        
        for component, result in system_validation['components_validated'].items():
            score = result.get('score', 0)
            status = result.get('status', 'unknown')
            
            component_scores.append(score)
            
            # Identifica problemas críticos
            if status == 'critical' or score < 50:
                critical_issues.append(f"{component}: {status} (score: {score:.1f})")
        
        # Calcula score médio
        overall_score = sum(component_scores) / len(component_scores) if component_scores else 0
        
        system_validation['overall_health_score'] = overall_score
        system_validation['critical_issues'] = critical_issues
        system_validation['system_ready'] = overall_score >= 80 and len(critical_issues) == 0
    
    def _generate_recommendations(self, system_validation: Dict[str, Any]):
        """Gera recomendações baseadas na validação"""
        
        recommendations = []
        
        # Recomendações baseadas no score geral
        overall_score = system_validation['overall_health_score']
        
        if overall_score < 60:
            recommendations.append("🚨 Sistema requer atenção imediata - múltiplos componentes críticos")
            recommendations.append("🔧 Verificar instalação e configuração dos componentes básicos")
        
        # Recomendações específicas por componente
        for component, result in system_validation['components_validated'].items():
            score = result.get('score', 0)
            status = result.get('status', 'unknown')
            
            if status == 'critical':
                recommendations.append(f"❌ {component}: Requer correção imediata")
            elif status == 'warning':
                recommendations.append(f"⚠️  {component}: Recomenda-se melhorias")
        
        # Recomendações gerais para melhoria
        if overall_score >= 80:
            recommendations.append("✅ Sistema em boa condição - manter monitoramento")
        elif overall_score >= 60:
            recommendations.append("📈 Sistema funcional - focar em melhorias dos componentes com menor score")
        
        system_validation['recommendations'] = recommendations

def main():
    """Função principal para demonstração"""
    print("🔍 System Validator - Etapa 7")
    print("=" * 60)
    
    validator = SystemValidator()
    
    # Executa validação completa
    results = validator.validate_complete_system()
    
    # Mostra resultados
    print(f"\n📊 RESULTADO DA VALIDAÇÃO COMPLETA:")
    print(f"   Score Geral: {results['overall_health_score']:.1f}/100")
    print(f"   Sistema Pronto: {'✅' if results['system_ready'] else '❌'}")
    print(f"   Problemas Críticos: {len(results['critical_issues'])}")
    
    print(f"\n📋 COMPONENTES VALIDADOS:")
    for component, result in results['components_validated'].items():
        status_icon = "✅" if result['status'] == 'healthy' else "⚠️" if result['status'] == 'warning' else "❌"
        print(f"   {status_icon} {component}: {result['score']:.1f}/100 ({result['status']})")
    
    if results['critical_issues']:
        print(f"\n🚨 PROBLEMAS CRÍTICOS:")
        for issue in results['critical_issues']:
            print(f"   • {issue}")
    
    print(f"\n💡 RECOMENDAÇÕES:")
    for rec in results['recommendations']:
        print(f"   {rec}")

if __name__ == "__main__":
    main()