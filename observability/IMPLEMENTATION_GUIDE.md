# 📘 Guia de Implementação - Observabilidade Maveretta

## 🎯 Objetivo

Este guia detalha como integrar os novos componentes de observabilidade na infraestrutura Maveretta existente, reaprovetando 100% do que já existe e expandindo apenas onde necessário.

---

## 🗂 Estrutura de Arquivos

### Arquivos Criados/Modificados

```
/app/
├── prometheus/
│   ├── prometheus.yml                    [EXISTENTE - Manter]
│   ├── prometheus_enhanced.yml           [NOVO - Usar este]
│   ├── alert_rules.yml                   [EXISTENTE - Manter]
│   ├── rules/
│   │   ├── maveretta_recording_rules.yml              [EXISTENTE]
│   │   └── maveretta_advanced_recording_rules.yml     [NOVO]
│   └── alerts/
│       ├── maveretta_critical_alerts.yml              [EXISTENTE]
│       ├── maveretta_trading_alerts.yml               [NOVO]
│       └── maveretta_infrastructure_alerts.yml        [NOVO]
│
├── config/grafana/
│   ├── dashboards/
│   │   ├── [18 dashboards existentes]                [MANTER TODOS]
│   │   └── maveretta-infrastructure.json              [NOVO]
│   └── provisioning/
│       ├── datasources/datasource.yml                 [EXISTENTE - OK]
│       └── dashboards.yml                             [EXISTENTE - OK]
│
├── docker-compose.yml                                 [EXISTENTE - Não modificar]
├── docker-compose-observability.yml                   [NOVO - Usar junto]
│
├── observability/
│   ├── README.md                                      [NOVO - Documentação]
│   └── IMPLEMENTATION_GUIDE.md                        [ESTE ARQUIVO]
│
└── observability_audit_report.json                   [NOVO - Relatório de auditoria]
```

---

## 🚀 Passo a Passo de Implementação

### FASE 1: Preparação (5 minutos)

#### 1.1 Backup das Configurações Atuais

```bash
cd /app

# Backup de segurança
tar -czf backup-observability-$(date +%Y%m%d-%H%M%S).tar.gz \
  prometheus/ \
  config/grafana/ \
  alertmanager/ \
  docker-compose.yml

echo "✅ Backup criado"
```

#### 1.2 Validar Arquivos Existentes

```bash
# Verificar estrutura atual
ls -la prometheus/
ls -la config/grafana/dashboards/
ls -la config/grafana/provisioning/

# Verificar se Prometheus está rodando
docker ps | grep prometheus

# Verificar se Grafana está rodando
docker ps | grep grafana

echo "✅ Validação concluída"
```

---

### FASE 2: Atualização do Prometheus (10 minutos)

#### 2.1 Ativar Configuração Avançada

O arquivo `prometheus_enhanced.yml` já foi criado. Vamos ativá-lo:

```bash
cd /app

# Validar novo arquivo
docker run --rm -v $(pwd)/prometheus:/prometheus \
  prom/prometheus:v2.54.1 \
  promtool check config /prometheus/prometheus_enhanced.yml

# Se validação OK, prosseguir
echo "✅ Configuração válida"
```

#### 2.2 Subir Stack com Observabilidade Expandida

```bash
# Parar stack atual (se necessário)
docker-compose down

# Subir com configuração expandida
docker-compose -f docker-compose.yml -f docker-compose-observability.yml up -d

# Aguardar inicialização
sleep 30

# Verificar serviços
docker-compose ps

echo "✅ Stack subiu com sucesso"
```

#### 2.3 Verificar Novos Exporters

```bash
# Node Exporter
curl -s http://localhost:9100/metrics | head -n 20

# cAdvisor
curl -s http://localhost:8181/metrics | head -n 20

# Verificar targets no Prometheus
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

echo "✅ Exporters ativos"
```

---

### FASE 3: Configuração do Grafana (5 minutos)

#### 3.1 Verificar Datasource

```bash
# Testar conexão Grafana -> Prometheus
curl -s http://localhost:3000/api/datasources \
  -u admin:admin123 | jq

# Se datasource OK, prosseguir
echo "✅ Datasource configurado"
```

#### 3.2 Carregar Novos Dashboards

Os dashboards são carregados automaticamente via provisioning. Verificar:

```bash
# Listar dashboards
curl -s http://localhost:3000/api/search \
  -u admin:admin123 | jq '.[] | {title: .title, uid: .uid}'

# Procurar por "maveretta-infrastructure"
echo "✅ Dashboards carregados"
```

#### 3.3 Acessar e Validar

1. Abrir navegador: http://localhost:3000 (ou seu domínio/grafana)
2. Login: admin / admin123
3. Procurar "Maveretta - Infrastructure"
4. Verificar se painéis estão exibindo dados

---

### FASE 4: Validação de Alertas (5 minutos)

#### 4.1 Verificar Regras de Alerta

```bash
# Listar todas as regras
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | {name: .name, rules: .rules | length}'

# Verificar regras ativas
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {alert: .labels.alertname, state: .state}'

echo "✅ Alertas configurados"
```

#### 4.2 Testar Alertmanager

```bash
# Verificar status
curl -s http://localhost:9093/api/v2/status | jq

# Listar alertas ativos
curl -s http://localhost:9093/api/v2/alerts | jq

echo "✅ Alertmanager operacional"
```

---

### FASE 5: Instrumentação do Código (Opcional)

Se você quiser adicionar instrumentação em novos módulos:

#### 5.1 Exemplo: Adicionar Métricas em um Arquivo Python

```python
# No topo do arquivo
from prometheus_client import Counter, Histogram, Gauge
import time

# Definir métricas
trades_executed = Counter(
    'my_module_trades_executed_total',
    'Total trades executed',
    ['exchange', 'symbol', 'side']
)

execution_latency = Histogram(
    'my_module_execution_latency_seconds',
    'Trade execution latency',
    ['exchange'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

open_positions = Gauge(
    'my_module_open_positions',
    'Number of open positions',
    ['exchange']
)

# Usar nas funções
def execute_trade(exchange, symbol, side):
    start = time.time()
    
    # Lógica de execução
    result = do_trade(exchange, symbol, side)
    
    # Registrar métricas
    trades_executed.labels(exchange=exchange, symbol=symbol, side=side).inc()
    execution_latency.labels(exchange=exchange).observe(time.time() - start)
    
    return result
```

#### 5.2 Expor Endpoint /metrics (se ainda não exposto)

```python
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask import Flask

app = Flask(__name__)

# Adicionar endpoint /metrics
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})
```

---

## 🧪 Testes e Validação

### Teste 1: Métricas de Sistema

```bash
# CPU
curl -s 'http://localhost:9090/api/v1/query?query=100%20-%20(avg(rate(node_cpu_seconds_total%7Bmode%3D%22idle%22%7D%5B5m%5D))%20*%20100)' | jq '.data.result[0].value[1]'

# Memória
curl -s 'http://localhost:9090/api/v1/query?query=(1%20-%20(node_memory_MemAvailable_bytes%20%2F%20node_memory_MemTotal_bytes))%20*%20100' | jq '.data.result[0].value[1]'

echo "✅ Métricas de sistema OK"
```

### Teste 2: Métricas de Trading

```bash
# Total PnL
curl -s 'http://localhost:9090/api/v1/query?query=sum(bot_slot_pnl_usd)' | jq '.data.result[0].value[1]'

# Slots ativos
curl -s 'http://localhost:9090/api/v1/query?query=count(bot_slot_status%20%3D%3D%201)' | jq '.data.result[0].value[1]'

echo "✅ Métricas de trading OK"
```

### Teste 3: Métricas de Exchanges

```bash
# Binance connection
curl -s 'http://localhost:9090/api/v1/query?query=binance_connection_status' | jq '.data.result[0].value[1]'

# WebSocket messages/min
curl -s 'http://localhost:9090/api/v1/query?query=rate(binance_websocket_messages_total%5B1m%5D)%20*%2060' | jq '.data.result[0].value[1]'

echo "✅ Métricas de exchanges OK"
```

### Teste 4: Dashboard Rendering

```bash
# Testar se dashboard responde
curl -s 'http://localhost:3000/api/dashboards/uid/maveretta-infrastructure' \
  -u admin:admin123 | jq '.dashboard.title'

# Deve retornar: "Maveretta - Infrastructure & System"
echo "✅ Dashboard acessível"
```

---

## 🔧 Troubleshooting

### Problema 1: Prometheus não coleta métricas de node-exporter

**Sintomas**: Target "node-exporter" em estado "Down"

**Solução**:
```bash
# Verificar se container está rodando
docker ps | grep node-exporter

# Testar endpoint diretamente
curl http://localhost:9100/metrics

# Se não responder, reiniciar
docker-compose -f docker-compose-observability.yml restart node-exporter
```

### Problema 2: cAdvisor não inicia

**Sintomas**: Container cAdvisor em loop de restart

**Solução**:
```bash
# Verificar logs
docker logs maveretta-cadvisor

# Problema comum: permissões
sudo chmod 755 /sys/fs/cgroup/

# Reiniciar
docker-compose -f docker-compose-observability.yml restart cadvisor
```

### Problema 3: Dashboard vazio no Grafana

**Sintomas**: Painéis sem dados ou "No data"

**Solução**:
```bash
# 1. Verificar datasource
curl http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=up \
  -u admin:admin123

# 2. Verificar se Prometheus tem dados
curl 'http://localhost:9090/api/v1/query?query=up'

# 3. Se Prometheus OK mas Grafana não:
# - Recarregar datasource na UI
# - Ajustar time range (ex: "Last 5 minutes")
```

### Problema 4: Alertas não disparam

**Sintomas**: Condições de alerta satisfeitas mas sem notificação

**Solução**:
```bash
# Verificar se regras estão carregadas
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[].name'

# Verificar se alertas estão ativos
curl http://localhost:9090/api/v1/alerts

# Verificar Alertmanager
curl http://localhost:9093/api/v2/status

# Testar envio manual
curl -X POST http://localhost:9093/api/v2/alerts \
  -H 'Content-Type: application/json' \
  -d '[{"labels":{"alertname":"test"}}]'
```

---

## 📊 Queries Úteis para Validação

### Validar Coleta de Métricas

```promql
# Targets ativos
count(up == 1)

# Targets por job
count by (job) (up == 1)

# Taxa de coleta (samples/sec)
rate(prometheus_tsdb_head_samples_appended_total[1m])
```

### Validar Recording Rules

```promql
# Verificar se recording rules estão funcionando
maveretta:core_latency_p95
maveretta:total_pnl_usd
maveretta:trades_per_minute
```

### Validar Alertas

```promql
# Contar alertas firing
count(ALERTS{alertstate="firing"})

# Listar alertas por severidade
count by (severity) (ALERTS{alertstate="firing"})
```

---

## ✅ Checklist de Validação Final

### Infraestrutura

- [ ] Prometheus rodando e coletando dados
- [ ] Node Exporter expondo métricas em :9100
- [ ] cAdvisor expondo métricas em :8181
- [ ] Todos os targets em estado "UP" no Prometheus
- [ ] Recording rules calculando corretamente
- [ ] Alertas carregados e funcionando

### Grafana

- [ ] Datasource Prometheus configurado
- [ ] Dashboard "maveretta-infrastructure" acessível
- [ ] Dashboards existentes não foram afetados
- [ ] Painéis exibindo dados corretamente
- [ ] Refresh automático funcionando (5s)

### Alertmanager

- [ ] Alertmanager rodando e acessível em :9093
- [ ] Configuração de notificações válida
- [ ] Alertas de teste disparando corretamente

### Aplicação

- [ ] Exporters de exchange ativos
- [ ] Core expondo /metrics
- [ ] IAs instrumentadas
- [ ] Slots reportando métricas
- [ ] Cascata monitorada

---

## 🎓 Próximos Passos

### Melhorias Futuras

1. **Distributed Tracing**
   - Adicionar Jaeger ou Tempo
   - Instrumentar requests com trace IDs

2. **Log Aggregation**
   - Adicionar Loki para logs centralizados
   - Correlacionar logs com métricas

3. **Anomaly Detection**
   - Implementar ML para detecção de anomalias
   - Alertas preditivos

4. **SLO/SLI Monitoring**
   - Definir SLOs para serviços críticos
   - Dashboards de error budget

5. **Cost Monitoring**
   - Métricas de custo de API
   - Trading fees tracking

---

## 📞 Suporte

Se encontrar problemas durante a implementação:

1. Consultar logs: `docker-compose logs -f [service]`
2. Verificar documentação: `/app/observability/README.md`
3. Testar queries manualmente no Prometheus
4. Validar configurações com promtool

---

**Implementação concluída!** 🎉

Sua infraestrutura Maveretta agora possui observabilidade 360° completa.
