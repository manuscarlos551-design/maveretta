#!/usr/bin/env python3
"""
Maveretta - Observability Validation Script
Validates all observability components are working correctly
"""

import requests
import json
import sys
from typing import Dict, List, Tuple
from datetime import datetime


class ObservabilityValidator:
    def __init__(self):
        self.prometheus_url = "http://localhost:9090"
        self.grafana_url = "http://localhost:3000"
        self.alertmanager_url = "http://localhost:9093"
        self.results = []
        
    def log(self, check: str, status: str, message: str):
        """Log validation result"""
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{emoji} {check}: {message}")
        self.results.append({
            "check": check,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def check_prometheus(self) -> bool:
        """Check if Prometheus is accessible"""
        try:
            response = requests.get(f"{self.prometheus_url}/-/healthy", timeout=5)
            if response.status_code == 200:
                self.log("Prometheus Health", "PASS", "Prometheus is healthy")
                return True
            else:
                self.log("Prometheus Health", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("Prometheus Health", "FAIL", str(e))
            return False
    
    def check_prometheus_targets(self) -> Tuple[int, int]:
        """Check Prometheus targets status"""
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/targets", timeout=5)
            data = response.json()
            
            if data['status'] != 'success':
                self.log("Prometheus Targets", "FAIL", "Failed to get targets")
                return 0, 0
            
            targets = data['data']['activeTargets']
            total = len(targets)
            up = sum(1 for t in targets if t['health'] == 'up')
            down = total - up
            
            if down == 0:
                self.log("Prometheus Targets", "PASS", f"All {total} targets are UP")
            else:
                self.log("Prometheus Targets", "WARN", f"{up}/{total} targets UP, {down} DOWN")
                
                # List down targets
                for t in targets:
                    if t['health'] != 'up':
                        job = t['labels'].get('job', 'unknown')
                        instance = t['labels'].get('instance', 'unknown')
                        self.log(f"  Target Down", "FAIL", f"{job} ({instance})")
            
            return up, total
        except Exception as e:
            self.log("Prometheus Targets", "FAIL", str(e))
            return 0, 0
    
    def check_recording_rules(self) -> int:
        """Check if recording rules are working"""
        rules_to_check = [
            "maveretta:core_latency_p95",
            "maveretta:total_pnl_usd",
            "maveretta:trades_per_minute",
            "maveretta:active_slots_total"
        ]
        
        working = 0
        for rule in rules_to_check:
            try:
                response = requests.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": rule},
                    timeout=5
                )
                data = response.json()
                
                if data['status'] == 'success' and len(data['data']['result']) > 0:
                    self.log(f"Recording Rule: {rule}", "PASS", "Active")
                    working += 1
                else:
                    self.log(f"Recording Rule: {rule}", "WARN", "No data yet")
            except Exception as e:
                self.log(f"Recording Rule: {rule}", "FAIL", str(e))
        
        return working
    
    def check_alert_rules(self) -> int:
        """Check if alert rules are loaded"""
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/rules", timeout=5)
            data = response.json()
            
            if data['status'] != 'success':
                self.log("Alert Rules", "FAIL", "Failed to get rules")
                return 0
            
            total_rules = 0
            for group in data['data']['groups']:
                total_rules += len(group['rules'])
            
            self.log("Alert Rules", "PASS", f"{total_rules} rules loaded")
            return total_rules
        except Exception as e:
            self.log("Alert Rules", "FAIL", str(e))
            return 0
    
    def check_grafana(self) -> bool:
        """Check if Grafana is accessible"""
        try:
            response = requests.get(f"{self.grafana_url}/api/health", timeout=5)
            data = response.json()
            
            if data.get('database') == 'ok':
                self.log("Grafana Health", "PASS", "Grafana is healthy")
                return True
            else:
                self.log("Grafana Health", "FAIL", "Database not OK")
                return False
        except Exception as e:
            self.log("Grafana Health", "FAIL", str(e))
            return False
    
    def check_grafana_datasource(self) -> bool:
        """Check if Grafana datasource is configured"""
        try:
            response = requests.get(
                f"{self.grafana_url}/api/datasources",
                auth=('admin', 'admin123'),
                timeout=5
            )
            datasources = response.json()
            
            prometheus_ds = [ds for ds in datasources if ds['type'] == 'prometheus']
            
            if prometheus_ds:
                self.log("Grafana Datasource", "PASS", f"{len(prometheus_ds)} Prometheus datasource(s)")
                return True
            else:
                self.log("Grafana Datasource", "FAIL", "No Prometheus datasource found")
                return False
        except Exception as e:
            self.log("Grafana Datasource", "FAIL", str(e))
            return False
    
    def check_grafana_dashboards(self) -> int:
        """Check Grafana dashboards"""
        try:
            response = requests.get(
                f"{self.grafana_url}/api/search?type=dash-db",
                auth=('admin', 'admin123'),
                timeout=5
            )
            dashboards = response.json()
            
            maveretta_dashboards = [d for d in dashboards if 'maveretta' in d.get('title', '').lower()]
            
            self.log("Grafana Dashboards", "PASS", f"{len(maveretta_dashboards)} Maveretta dashboards found")
            return len(maveretta_dashboards)
        except Exception as e:
            self.log("Grafana Dashboards", "FAIL", str(e))
            return 0
    
    def check_alertmanager(self) -> bool:
        """Check if Alertmanager is accessible"""
        try:
            response = requests.get(f"{self.alertmanager_url}/api/v2/status", timeout=5)
            data = response.json()
            
            if data.get('cluster', {}).get('status') == 'ready':
                self.log("Alertmanager Health", "PASS", "Alertmanager is ready")
                return True
            else:
                self.log("Alertmanager Health", "WARN", "Cluster not ready")
                return False
        except Exception as e:
            self.log("Alertmanager Health", "FAIL", str(e))
            return False
    
    def check_exporters(self) -> Dict[str, bool]:
        """Check individual exporters"""
        exporters = {
            "Node Exporter": "http://localhost:9100/metrics",
            "cAdvisor": "http://localhost:8181/metrics",
            "Binance Exporter": "http://localhost:8000/metrics",
            "AI Gateway": "http://localhost:8080/metrics"
        }
        
        results = {}
        for name, url in exporters.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.log(f"Exporter: {name}", "PASS", "Responding")
                    results[name] = True
                else:
                    self.log(f"Exporter: {name}", "FAIL", f"HTTP {response.status_code}")
                    results[name] = False
            except Exception as e:
                self.log(f"Exporter: {name}", "WARN", "Not accessible (may not be running)")
                results[name] = False
        
        return results
    
    def generate_report(self):
        """Generate validation report"""
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')
        total = len(self.results)
        
        print("\n" + "="*60)
        print("📊 OBSERVABILITY VALIDATION REPORT")
        print("="*60)
        print(f"Total Checks: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print("="*60)
        
        # Save report to file
        report_file = f"/app/observability/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "warnings": warnings,
                    "success_rate": (passed/total)*100
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return failed == 0
    
    def run_all_checks(self):
        """Run all validation checks"""
        print("🚀 Starting Observability Validation\n")
        
        # Core services
        print("📡 Checking Core Services...")
        self.check_prometheus()
        self.check_grafana()
        self.check_alertmanager()
        
        print("\n🎯 Checking Prometheus Configuration...")
        self.check_prometheus_targets()
        self.check_recording_rules()
        self.check_alert_rules()
        
        print("\n📊 Checking Grafana Configuration...")
        self.check_grafana_datasource()
        self.check_grafana_dashboards()
        
        print("\n🔌 Checking Exporters...")
        self.check_exporters()
        
        # Generate report
        success = self.generate_report()
        
        return 0 if success else 1


if __name__ == "__main__":
    validator = ObservabilityValidator()
    exit_code = validator.run_all_checks()
    sys.exit(exit_code)
