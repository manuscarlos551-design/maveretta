#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production Monitor - Etapa 7
Sistema completo de monitoramento para produção
"""

import os
import sys
import time
import json
import psutil
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import threading
from dataclasses import dataclass
import sqlite3

# Adiciona path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class SystemMetrics:
    """Classe para métricas do sistema"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    
@dataclass
class TradingMetrics:
    """Classe para métricas de trading"""
    timestamp: datetime
    pnl_current: float
    pnl_daily: float
    pnl_total: float
    open_positions: int
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float

class ProductionMonitor:
    """
    Sistema completo de monitoramento para produção
    Monitora sistema, trading, performance e saúde geral
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Configuração do monitor
        self.monitoring_config = {
            'system_check_interval': 30,  # segundos
            'trading_check_interval': 60, # segundos
            'alert_thresholds': {
                'cpu_critical': 85.0,
                'memory_critical': 90.0,
                'disk_critical': 95.0,
                'drawdown_warning': 0.10,
                'drawdown_critical': 0.15,
                'api_response_timeout': 5.0
            },
            'retention_days': 30,
            'database_path': 'data/production_monitoring.db'
        }
        
        # Estado do monitor
        self.is_running = False
        self.monitoring_threads = []
        
        # Métricas atuais
        self.current_system_metrics = None
        self.current_trading_metrics = None
        
        # Histórico de alertas
        self.alert_history = []
        
        # Inicializa base de dados
        self._initialize_database()
        
    def setup_logging(self):
        """Configura logging para produção"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Log file específico para monitoramento
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / 'production_monitor.log')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
    
    def _initialize_database(self):
        """Inicializa base de dados SQLite para métricas"""
        
        db_path = Path(self.monitoring_config['database_path'])
        db_path.parent.mkdir(exist_ok=True)
        
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # Tabela de métricas do sistema
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        cpu_percent REAL,
                        memory_percent REAL,
                        disk_usage_percent REAL,
                        network_bytes_sent INTEGER,
                        network_bytes_recv INTEGER,
                        active_connections INTEGER
                    )
                ''')
                
                # Tabela de métricas de trading
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trading_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        pnl_current REAL,
                        pnl_daily REAL,
                        pnl_total REAL,
                        open_positions INTEGER,
                        total_trades INTEGER,
                        win_rate REAL,
                        profit_factor REAL,
                        max_drawdown REAL,
                        sharpe_ratio REAL
                    )
                ''')
                
                # Tabela de alertas
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        alert_type TEXT,
                        severity TEXT,
                        message TEXT,
                        metric_value REAL,
                        threshold_value REAL,
                        resolved BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                conn.commit()
                
            self.logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing database: {e}")
    
    def start_monitoring(self):
        """Inicia monitoramento em background"""
        
        if self.is_running:
            self.logger.warning("Monitoring already running")
            return
        
        self.logger.info("🚀 Starting production monitoring...")
        self.is_running = True
        
        # Thread para monitoramento do sistema
        system_thread = threading.Thread(target=self._system_monitoring_loop, daemon=True)
        system_thread.start()
        self.monitoring_threads.append(system_thread)
        
        # Thread para monitoramento de trading
        trading_thread = threading.Thread(target=self._trading_monitoring_loop, daemon=True)
        trading_thread.start()
        self.monitoring_threads.append(trading_thread)
        
        # Thread para limpeza de dados antigos
        cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()
        self.monitoring_threads.append(cleanup_thread)
        
        self.logger.info("✅ Production monitoring started")
    
    def stop_monitoring(self):
        """Para monitoramento"""
        
        self.logger.info("🛑 Stopping production monitoring...")
        self.is_running = False
        
        # Aguarda threads terminarem
        for thread in self.monitoring_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.monitoring_threads.clear()
        self.logger.info("✅ Production monitoring stopped")
    
    def _system_monitoring_loop(self):
        """Loop principal de monitoramento do sistema"""
        
        self.logger.info("📊 Starting system monitoring loop")
        
        while self.is_running:
            try:
                # Coleta métricas do sistema
                metrics = self._collect_system_metrics()
                self.current_system_metrics = metrics
                
                # Salva no banco de dados
                self._save_system_metrics(metrics)
                
                # Verifica alertas
                self._check_system_alerts(metrics)
                
                # Log periódico
                if int(time.time()) % 300 == 0:  # A cada 5 minutos
                    self.logger.info(f"System Health - CPU: {metrics.cpu_percent:.1f}%, Memory: {metrics.memory_percent:.1f}%, Disk: {metrics.disk_usage_percent:.1f}%")
                
            except Exception as e:
                self.logger.error(f"Error in system monitoring: {e}")
            
            time.sleep(self.monitoring_config['system_check_interval'])
    
    def _trading_monitoring_loop(self):
        """Loop principal de monitoramento de trading"""
        
        self.logger.info("📈 Starting trading monitoring loop")
        
        while self.is_running:
            try:
                # Coleta métricas de trading
                metrics = self._collect_trading_metrics()
                self.current_trading_metrics = metrics
                
                # Salva no banco de dados
                self._save_trading_metrics(metrics)
                
                # Verifica alertas de trading
                self._check_trading_alerts(metrics)
                
                # Log periódico
                if int(time.time()) % 300 == 0:  # A cada 5 minutos
                    self.logger.info(f"Trading Health - P&L: {metrics.pnl_daily:.2f}, Positions: {metrics.open_positions}, Drawdown: {metrics.max_drawdown:.2%}")
                
            except Exception as e:
                self.logger.error(f"Error in trading monitoring: {e}")
            
            time.sleep(self.monitoring_config['trading_check_interval'])
    
    def _cleanup_loop(self):
        """Loop de limpeza de dados antigos"""
        
        while self.is_running:
            try:
                # Executa limpeza uma vez por hora
                time.sleep(3600)
                
                if not self.is_running:
                    break
                
                self._cleanup_old_data()
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Coleta métricas atuais do sistema"""
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        
        # Network
        network = psutil.net_io_counters()
        network_bytes_sent = network.bytes_sent
        network_bytes_recv = network.bytes_recv
        
        # Connections
        try:
            connections = len(psutil.net_connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            connections = 0
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_usage_percent=disk_usage_percent,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            active_connections=connections
        )
    
    def _collect_trading_metrics(self) -> TradingMetrics:
        """Coleta métricas atuais de trading"""
        
        # Por enquanto, simula métricas
        # Em produção, isso seria conectado ao sistema de trading real
        
        import random
        import math
        
        # Simula métricas realistas
        base_pnl = 1000  # Base P&L
        daily_variation = random.uniform(-50, 100)  # Variação diária
        
        pnl_daily = daily_variation
        pnl_total = base_pnl + daily_variation
        pnl_current = pnl_total
        
        open_positions = random.randint(0, 3)
        total_trades = random.randint(50, 200)
        win_rate = random.uniform(0.55, 0.75)
        profit_factor = random.uniform(1.2, 1.8)
        max_drawdown = abs(random.uniform(0.02, 0.12))
        
        # Sharpe ratio baseado no P&L
        sharpe_ratio = max(0.5, min(3.0, pnl_total / 1000 * 2))
        
        return TradingMetrics(
            timestamp=datetime.now(),
            pnl_current=pnl_current,
            pnl_daily=pnl_daily,
            pnl_total=pnl_total,
            open_positions=open_positions,
            total_trades=total_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio
        )
    
    def _save_system_metrics(self, metrics: SystemMetrics):
        """Salva métricas do sistema no banco"""
        
        try:
            db_path = self.monitoring_config['database_path']
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_metrics 
                    (timestamp, cpu_percent, memory_percent, disk_usage_percent, 
                     network_bytes_sent, network_bytes_recv, active_connections)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics.timestamp,
                    metrics.cpu_percent,
                    metrics.memory_percent,
                    metrics.disk_usage_percent,
                    metrics.network_bytes_sent,
                    metrics.network_bytes_recv,
                    metrics.active_connections
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving system metrics: {e}")
    
    def _save_trading_metrics(self, metrics: TradingMetrics):
        """Salva métricas de trading no banco"""
        
        try:
            db_path = self.monitoring_config['database_path']
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trading_metrics 
                    (timestamp, pnl_current, pnl_daily, pnl_total, open_positions,
                     total_trades, win_rate, profit_factor, max_drawdown, sharpe_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics.timestamp,
                    metrics.pnl_current,
                    metrics.pnl_daily,
                    metrics.pnl_total,
                    metrics.open_positions,
                    metrics.total_trades,
                    metrics.win_rate,
                    metrics.profit_factor,
                    metrics.max_drawdown,
                    metrics.sharpe_ratio
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving trading metrics: {e}")
    
    def _check_system_alerts(self, metrics: SystemMetrics):
        """Verifica e dispara alertas do sistema"""
        
        thresholds = self.monitoring_config['alert_thresholds']
        
        # Alerta de CPU
        if metrics.cpu_percent > thresholds['cpu_critical']:
            self._trigger_alert(
                'system_cpu',
                'critical',
                f'CPU usage critical: {metrics.cpu_percent:.1f}%',
                metrics.cpu_percent,
                thresholds['cpu_critical']
            )
        
        # Alerta de memória
        if metrics.memory_percent > thresholds['memory_critical']:
            self._trigger_alert(
                'system_memory',
                'critical',
                f'Memory usage critical: {metrics.memory_percent:.1f}%',
                metrics.memory_percent,
                thresholds['memory_critical']
            )
        
        # Alerta de disco
        if metrics.disk_usage_percent > thresholds['disk_critical']:
            self._trigger_alert(
                'system_disk',
                'critical',
                f'Disk usage critical: {metrics.disk_usage_percent:.1f}%',
                metrics.disk_usage_percent,
                thresholds['disk_critical']
            )
    
    def _check_trading_alerts(self, metrics: TradingMetrics):
        """Verifica e dispara alertas de trading"""
        
        thresholds = self.monitoring_config['alert_thresholds']
        
        # Alerta de drawdown
        if metrics.max_drawdown > thresholds['drawdown_critical']:
            self._trigger_alert(
                'trading_drawdown',
                'critical',
                f'Maximum drawdown critical: {metrics.max_drawdown:.2%}',
                metrics.max_drawdown,
                thresholds['drawdown_critical']
            )
        elif metrics.max_drawdown > thresholds['drawdown_warning']:
            self._trigger_alert(
                'trading_drawdown',
                'warning',
                f'Maximum drawdown warning: {metrics.max_drawdown:.2%}',
                metrics.max_drawdown,
                thresholds['drawdown_warning']
            )
        
        # Alerta de P&L negativo significativo
        if metrics.pnl_daily < -500:  # Perda diária > $500
            self._trigger_alert(
                'trading_pnl',
                'warning',
                f'Daily P&L negative: ${metrics.pnl_daily:.2f}',
                metrics.pnl_daily,
                -500
            )
    
    def _trigger_alert(self, alert_type: str, severity: str, message: str, 
                      metric_value: float, threshold_value: float):
        """Dispara um alerta"""
        
        alert = {
            'timestamp': datetime.now(),
            'alert_type': alert_type,
            'severity': severity,
            'message': message,
            'metric_value': metric_value,
            'threshold_value': threshold_value
        }
        
        # Adiciona ao histórico
        self.alert_history.append(alert)
        
        # Salva no banco
        try:
            db_path = self.monitoring_config['database_path']
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alerts 
                    (timestamp, alert_type, severity, message, metric_value, threshold_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    alert['timestamp'],
                    alert_type,
                    severity,
                    message,
                    metric_value,
                    threshold_value
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving alert: {e}")
        
        # Log do alerta
        log_level = logging.CRITICAL if severity == 'critical' else logging.WARNING
        self.logger.log(log_level, f"🚨 ALERT [{severity.upper()}] {message}")
    
    def _cleanup_old_data(self):
        """Remove dados antigos do banco"""
        
        cutoff_date = datetime.now() - timedelta(days=self.monitoring_config['retention_days'])
        
        try:
            db_path = self.monitoring_config['database_path']
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Remove métricas antigas
                cursor.execute('DELETE FROM system_metrics WHERE timestamp < ?', (cutoff_date,))
                cursor.execute('DELETE FROM trading_metrics WHERE timestamp < ?', (cutoff_date,))
                cursor.execute('DELETE FROM alerts WHERE timestamp < ? AND resolved = TRUE', (cutoff_date,))
                
                conn.commit()
                
                self.logger.info(f"Cleaned up data older than {cutoff_date}")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Retorna status atual da saúde do sistema"""
        
        if not self.current_system_metrics:
            return {'status': 'unknown', 'message': 'No metrics available'}
        
        metrics = self.current_system_metrics
        thresholds = self.monitoring_config['alert_thresholds']
        
        # Calcula status geral
        issues = []
        
        if metrics.cpu_percent > thresholds['cpu_critical']:
            issues.append('CPU critical')
        if metrics.memory_percent > thresholds['memory_critical']:
            issues.append('Memory critical')
        if metrics.disk_usage_percent > thresholds['disk_critical']:
            issues.append('Disk critical')
        
        if issues:
            status = 'critical'
            message = f"Critical issues: {', '.join(issues)}"
        elif (metrics.cpu_percent > 70 or metrics.memory_percent > 80 or metrics.disk_usage_percent > 85):
            status = 'warning'
            message = "System resources under pressure"
        else:
            status = 'healthy'
            message = "All systems normal"
        
        return {
            'status': status,
            'message': message,
            'timestamp': metrics.timestamp.isoformat(),
            'metrics': {
                'cpu_percent': metrics.cpu_percent,
                'memory_percent': metrics.memory_percent,
                'disk_usage_percent': metrics.disk_usage_percent,
                'active_connections': metrics.active_connections
            }
        }
    
    def get_trading_performance(self) -> Dict[str, Any]:
        """Retorna métricas atuais de performance de trading"""
        
        if not self.current_trading_metrics:
            return {'status': 'unknown', 'message': 'No trading metrics available'}
        
        metrics = self.current_trading_metrics
        thresholds = self.monitoring_config['alert_thresholds']
        
        # Avalia performance
        if metrics.max_drawdown > thresholds['drawdown_critical']:
            status = 'critical'
            message = 'Drawdown critical level'
        elif metrics.max_drawdown > thresholds['drawdown_warning']:
            status = 'warning'
            message = 'Drawdown warning level'
        elif metrics.pnl_daily < -100:
            status = 'warning'
            message = 'Daily losses'
        else:
            status = 'healthy'
            message = 'Trading performance normal'
        
        return {
            'status': status,
            'message': message,
            'timestamp': metrics.timestamp.isoformat(),
            'metrics': {
                'pnl_daily': metrics.pnl_daily,
                'pnl_total': metrics.pnl_total,
                'open_positions': metrics.open_positions,
                'win_rate': metrics.win_rate,
                'profit_factor': metrics.profit_factor,
                'max_drawdown': metrics.max_drawdown,
                'sharpe_ratio': metrics.sharpe_ratio
            }
        }
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna alertas recentes"""
        
        try:
            db_path = self.monitoring_config['database_path']
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, alert_type, severity, message, metric_value, threshold_value
                    FROM alerts 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                alerts = []
                for row in cursor.fetchall():
                    alerts.append({
                        'timestamp': row[0],
                        'alert_type': row[1],
                        'severity': row[2],
                        'message': row[3],
                        'metric_value': row[4],
                        'threshold_value': row[5]
                    })
                
                return alerts
                
        except Exception as e:
            self.logger.error(f"Error getting recent alerts: {e}")
            return []
    
    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Gera relatório completo de monitoramento"""
        
        return {
            'generated_at': datetime.now().isoformat(),
            'monitoring_status': 'running' if self.is_running else 'stopped',
            'system_health': self.get_system_health(),
            'trading_performance': self.get_trading_performance(),
            'recent_alerts': self.get_recent_alerts(5),
            'alert_summary': {
                'total_alerts_today': len([a for a in self.alert_history 
                                         if a['timestamp'].date() == datetime.now().date()]),
                'critical_alerts_today': len([a for a in self.alert_history 
                                            if a['timestamp'].date() == datetime.now().date() 
                                            and a['severity'] == 'critical']),
            },
            'uptime': self._calculate_uptime()
        }
    
    def _calculate_uptime(self) -> Dict[str, Any]:
        """Calcula uptime do sistema"""
        
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            return {
                'boot_time': boot_time.isoformat(),
                'uptime_seconds': uptime.total_seconds(),
                'uptime_human': str(uptime).split('.')[0]  # Remove microseconds
            }
        except Exception as e:
            return {'error': str(e)}

def main():
    """Função principal para demonstração"""
    print("📊 Production Monitor - Etapa 7")
    print("=" * 60)
    
    # Inicializa monitor
    monitor = ProductionMonitor()
    
    print("🚀 Starting monitoring...")
    monitor.start_monitoring()
    
    # Monitora por 30 segundos para demonstração
    try:
        for i in range(6):
            time.sleep(5)
            
            # Mostra status a cada 5 segundos
            system_health = monitor.get_system_health()
            trading_performance = monitor.get_trading_performance()
            
            print(f"\n📊 Status ({i*5}s):")
            print(f"   System: {system_health['status']} - {system_health['message']}")
            print(f"   Trading: {trading_performance['status']} - {trading_performance['message']}")
            
            if system_health['status'] != 'unknown':
                metrics = system_health['metrics']
                print(f"   CPU: {metrics['cpu_percent']:.1f}% | Memory: {metrics['memory_percent']:.1f}% | Disk: {metrics['disk_usage_percent']:.1f}%")
            
            if trading_performance['status'] != 'unknown':
                metrics = trading_performance['metrics']
                print(f"   P&L Daily: ${metrics['pnl_daily']:.2f} | Drawdown: {metrics['max_drawdown']:.2%} | Positions: {metrics['open_positions']}")
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    
    finally:
        print("🛑 Stopping monitoring...")
        monitor.stop_monitoring()
        print("✅ Monitoring stopped")

if __name__ == "__main__":
    main()