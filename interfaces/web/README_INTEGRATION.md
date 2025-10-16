# Integração Streamlit + Grafana - 13 Abas

## ✅ Implementação Completa

Este documento descreve a integração completa dos painéis Grafana no dashboard Streamlit, conforme o mapeamento `AUDITORIA_MAPEAMENTO_STREAMLIT_GRAFANA`.

---

## 📊 Estrutura das 13 Abas

### ✅ Abas Implementadas com Painéis Grafana

#### 1. 📊 Visão Geral (41 painéis mapeados)
**Dashboards Grafana Integrados:**
- `maveretta-market-overview` - Visão geral do mercado
- `maveretta-top10-live` - Top 10 criptomoedas
- `maveretta-dynamic-live` - Análise dinâmica por símbolo

**Métricas Prometheus:**
- Consensus Approved, Open Positions, BTC Price, Services Status
- Status de conexão das 5 exchanges (Binance, Bybit, Coinbase, KuCoin, OKX)
- Métricas de consenso, infraestrutura, arbitragem e risco

#### 2. 📈 Operações (10 painéis mapeados)
**Métricas Prometheus:**
- Paper Trades PnL, Execution Time
- CPU, Memory, Disk Usage
- Container metrics (CPU/Memory por serviço)
- Latência (Binance, Exchange, Clock Skew)

#### 3. 🎰 Caça-níqueis/Slots (7 painéis mapeados)
**Dashboards Grafana:**
- `maveretta-slots-live` - Dashboard completo de slots
- `orchestration-slots-timeline` - Timeline dos estados

**Métricas Prometheus:**
- Slots ativos, Ciclos completados, Capital total, Taxa de execução
- Active slots count, State changes
- Distribuição de estados dos slots

#### 4. 🏦 Tesouro (0 painéis - estrutura criada)
**Status:** 🚧 Em desenvolvimento
**Planejado:** Métricas financeiras consolidadas

#### 5. 🎮 Controles (0 painéis - estrutura criada)
**Status:** 🚧 Em desenvolvimento
**Planejado:** Controles operacionais (Start/Pause/Stop/Emergency)

#### 6. 🧠 Insights da IA (18 painéis mapeados)
**Dashboards Grafana:**
- `agents-overview-phase3` - Visão geral dos agentes
- `maveretta-consensus-flow` - Fluxo de consenso
- `orchestration-decision-conf` - Confiança nas decisões

**Métricas Prometheus:**
- Agent running, Decisions/hour, Consensus confidence, Drawdown
- IA Latency, IA Uptime, IA Errors

#### 7. 📋 Auditoria (0 painéis - estrutura criada)
**Status:** 🚧 Em desenvolvimento
**Planejado:** Trilha de eventos e auditoria completa

#### 8. 📝 Registros/Logs (1 painel mapeado)
**Métricas Prometheus:**
- Connection errors por exchange
- `exchange_errors_total` monitorado

#### 9. 🚨 Alertas (0 painéis - estrutura criada)
**Status:** 🚧 Em desenvolvimento
**Planejado:** Sistema de alertas e notificações

#### 10. 🔬 Testes Retrospectivos/Backtests (7 painéis mapeados)
**Métricas Prometheus:**
- Equity por exchange (Binance, KuCoin, Bybit, Coinbase, OKX)
- Histórico em USD e BRL

#### 11. 🎯 Estratégias (0 painéis - estrutura criada)
**Status:** 🚧 Em desenvolvimento
**Planejado:** Gestão de estratégias de trading

#### 12. 🎼 Orquestração (3 painéis mapeados)
**Dashboards Grafana:**
- `agent-drilldown-phase3` - Detalhes dos agentes
- `orchestration-venue-health` - Saúde das venues

**Métricas Prometheus:**
- Decision Latency (p95), Arbitrage P&L, Risk blocks

#### 13. 💰 Carteira (0 painéis - estrutura criada)
**Status:** 🚧 Em desenvolvimento
**Planejado:** Visão consolidada de carteira

---

## 🔧 Arquitetura Técnica

### Stack de Tecnologia
```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Streamlit  │─────▶│   Grafana   │─────▶│ Prometheus  │
│   (8501)    │      │   (3000)    │      │   (9090)    │
└─────────────┘      └─────────────┘      └─────────────┘
       │                     │                     │
       │                     │                     │
       ▼                     ▼                     ▼
  iframes embedados    Dashboards JSON      Métricas TSDB
```

### Fluxo de Dados

1. **Exporters → Prometheus**
   - `binance-exporter:8000`
   - `kucoin-exporter:8001`
   - `bybit-exporter:8002`
   - `coinbase-exporter:8003`
   - `okx-exporter:8004`
   - `mongodb-exporter:9216`
   - `redis-exporter:9121`
   - Scrape interval: 3-15s (dependendo da criticidade)

2. **Prometheus → Grafana**
   - Datasource: `prometheus-ds`
   - URL: `http://prometheus:9090`
   - Queries PromQL executadas pelos dashboards

3. **Streamlit → Grafana**
   - Embed via iframes
   - URL base: `http://grafana:3000`
   - Parâmetros: `orgId=1&theme=dark&refresh=10s`

4. **Streamlit → Prometheus (direto)**
   - Cliente Python: `prometheus_client_helper.py`
   - Queries PromQL para métricas específicas

---

## 📁 Arquivos Modificados/Criados

### Arquivos Principais
```
/app/interfaces/web/
├── app.py                      # ✅ REESCRITO - 13 abas completas
├── app.py.backup               # 📦 Backup do original
├── grafana_embed.py            # ✅ ATUALIZADO - UIDs corretos
├── prometheus_client_helper.py # ✅ Usado para queries diretas
└── README_INTEGRATION.md       # 📝 Esta documentação
```

### Configurações Existentes (não modificadas)
```
/app/config/grafana/
├── provisioning/
│   ├── datasources/datasource.yml  # Prometheus datasource
│   └── dashboards.yml              # Provisioning de dashboards
└── dashboards/
    ├── maveretta-overview-live.json
    ├── maveretta-slots-live.json
    ├── agents-overview-phase3.json
    ├── consensus-flow.json
    └── ... (18 dashboards JSON)

/app/prometheus/
└── prometheus.yml                  # Configuração de scrape
```

---

## 🎯 Dashboards Grafana Configurados

| Dashboard Key | UID Grafana | Status | Descrição |
|---------------|-------------|--------|-----------|
| `overview` | `maveretta-overview-live` | ✅ | Overview principal |
| `market` | `maveretta-market-overview` | ✅ | Visão de mercado |
| `dynamic` | `maveretta-dynamic-live` | ✅ | Análise dinâmica |
| `slots` | `maveretta-slots-live` | ✅ | Slots de trading |
| `top10` | `maveretta-top10-live` | ✅ | Top 10 preços |
| `agents` | `agents-overview-phase3` | ✅ | Visão dos agentes |
| `consensus` | `maveretta-consensus-flow` | ✅ | Fluxo de consenso |
| `agent_drilldown` | `agent-drilldown-phase3` | ✅ | Detalhes agentes |
| `venue_health` | `orchestration-venue-health` | ✅ | Saúde venues |
| `ia_health` | `orchestration-ia-health` | ✅ | Saúde IAs |
| `decision_conf` | `orchestration-decision-conf` | ✅ | Decisões |
| `slots_timeline` | `orchestration-slots-timeline` | ✅ | Timeline slots |
| `arbitrage_legs` | `orchestration-arbitrage-legs` | ✅ | Arbitragem |
| `infrastructure` | `maveretta-infrastructure` | ✅ | Infraestrutura |
| `binance` | `maveretta-overview-live` | ✅ | Binance |
| `kucoin` | `maveretta-kucoin-live` | ✅ | KuCoin |
| `bybit` | `maveretta-bybit-live` | ✅ | Bybit |
| `coinbase` | `maveretta-coinbase-live` | ✅ | Coinbase |
| `okx` | `maveretta-okx-live` | ✅ | OKX |

---

## 🚀 Como Usar

### 1. Iniciar os Serviços

```bash
# Iniciar todos os serviços via docker-compose
docker-compose up -d

# Verificar status
docker-compose ps
```

### 2. Acessar as Interfaces

- **Streamlit Dashboard**: http://localhost:8501
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090

### 3. Navegar pelas Abas

1. Acesse o Streamlit em http://localhost:8501
2. Use as 13 abas no topo da página
3. Os painéis Grafana são carregados automaticamente via iframes
4. Métricas Prometheus são consultadas em tempo real

### 4. Verificar Dados

```bash
# Verificar se Prometheus está coletando métricas
curl http://localhost:9090/api/v1/query?query=up

# Verificar se Grafana está acessível
curl http://localhost:3000/api/health

# Verificar logs do Streamlit
docker-compose logs -f dashboard
```

---

## 🔍 Troubleshooting

### Problema: Painéis Grafana não aparecem

**Solução:**
1. Verifique se Grafana está rodando: `docker-compose ps grafana`
2. Acesse Grafana diretamente em http://localhost:3000
3. Verifique se os dashboards estão provisionados em "Dashboards" → "Maveretta Core"
4. Verifique logs: `docker-compose logs grafana`

### Problema: Métricas Prometheus retornam zero

**Solução:**
1. Verifique se exporters estão rodando: `docker-compose ps | grep exporter`
2. Acesse Prometheus: http://localhost:9090/targets
3. Verifique se todos os targets estão "UP"
4. Verifique credenciais das exchanges no `.env`

### Problema: Streamlit não conecta ao Grafana

**Solução:**
1. Verifique GRAFANA_URL no `.env`
2. Deve ser `http://grafana:3000` (dentro do Docker network)
3. Reinicie Streamlit: `docker-compose restart dashboard`

### Problema: Dashboard não carrega (UID não encontrado)

**Solução:**
1. Verifique os UIDs em `/app/interfaces/web/grafana_embed.py`
2. Compare com UIDs reais em `/app/config/grafana/dashboards/*.json`
3. Atualize `DASHBOARD_UIDS` se necessário

---

## 📊 Métricas Disponíveis

### Exchanges
- `binance_equity_usdt`, `binance_equity_brl`
- `kucoin_equity_usdt`, `bybit_equity_usdt`
- `coinbase_equity_usdt`, `okx_equity_usdt`
- `up{job="*-exporter"}` - Status de conexão

### Trading
- `bot_slots_active` - Slots ativos
- `bot_cycles_completed_total` - Ciclos completados
- `binance_last_price` - Preços em tempo real
- `binance_volume_24h` - Volume 24h

### Agentes IA
- `agent_running` - Status do agente
- `agent_decisions_total` - Decisões tomadas
- `agent_consensus_approved_total` - Consenso aprovado
- `agent_consensus_confidence_avg` - Confiança média
- `agent_drawdown_pct` - Drawdown percentual

### Orquestração
- `slot_state` - Estado dos slots
- `slot_state_changes_total` - Mudanças de estado
- `arb_legs_success_total` - Arbitragem bem-sucedida
- `arb_pnl_realized` - P&L de arbitragem

### Infraestrutura
- `node_cpu_seconds_total` - Uso de CPU
- `node_memory_MemAvailable_bytes` - Memória disponível
- `node_filesystem_avail_bytes` - Disco disponível
- `container_cpu_usage_seconds_total` - CPU por container
- `container_memory_usage_bytes` - Memória por container

### Risco
- `agent_risk_blocked_total` - Bloqueios de risco
- `exchange_errors_total` - Erros de exchange
- `exchange_latency_ms` - Latência
- `exchange_rate_limit_remaining` - Rate limit

---

## 🎨 Personalização

### Adicionar Novo Dashboard

1. **Criar dashboard no Grafana**
   - Acesse http://localhost:3000
   - Crie o dashboard
   - Exporte como JSON

2. **Adicionar ao provisioning**
   ```bash
   cp dashboard.json /app/config/grafana/dashboards/
   ```

3. **Registrar UID no Streamlit**
   ```python
   # Em /app/interfaces/web/grafana_embed.py
   DASHBOARD_UIDS = {
       ...
       "novo_dashboard": "uid-do-dashboard",
   }
   ```

4. **Usar no Streamlit**
   ```python
   # Em app.py
   render_full_dashboard("novo_dashboard", height=600)
   ```

### Adicionar Nova Métrica

1. **Expor métrica no exporter**
2. **Verificar no Prometheus**: http://localhost:9090/graph
3. **Usar no Streamlit**:
   ```python
   value = prom_query_value("sua_metrica_aqui")
   st.metric("Sua Métrica", f"{value:.2f}")
   ```

---

## 📝 Mapeamento Completo

Conforme documento `AUDITORIA_MAPEAMENTO_STREAMLIT_GRAFANA`:

- **Total de dashboards Grafana**: 18
- **Total de painéis analisados**: 87
- **Painéis mapeados**: 87 (100%)
- **Abas implementadas**: 13/13 (100%)
- **Abas com painéis ativos**: 8/13 (61.5%)
- **Abas planejadas (estrutura criada)**: 5/13 (38.5%)

---

## ✅ Checklist de Implementação

- [x] Análise do mapeamento AUDITORIA_MAPEAMENTO_STREAMLIT_GRAFANA
- [x] Identificação dos 18 dashboards Grafana
- [x] Extração dos UIDs reais dos dashboards
- [x] Atualização do grafana_embed.py com UIDs corretos
- [x] Criação das 13 abas no Streamlit
- [x] Integração dos 87 painéis via iframes e queries Prometheus
- [x] Implementação de métricas em tempo real
- [x] Tema dark premium consistente
- [x] Documentação completa
- [ ] Testes de carga e performance
- [ ] Implementação das 5 abas planejadas

---

## 🎯 Próximos Passos

### Curto Prazo
1. ✅ Implementar 13 abas com painéis Grafana
2. ✅ Conectar Prometheus para métricas em tempo real
3. ⏳ Testar em ambiente de produção

### Médio Prazo
1. 📋 Implementar aba de Auditoria com trilha de eventos
2. 🎮 Implementar aba de Controles com ações operacionais
3. 🚨 Implementar aba de Alertas com notificações
4. 🎯 Implementar aba de Estratégias com gestão de trading
5. 💰 Implementar aba de Carteira consolidada

### Longo Prazo
1. 📊 Dashboard mobile-responsive
2. 🔐 Sistema de permissões por aba
3. 📈 Relatórios automatizados
4. 🤖 Chatbot integrado para navegação

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs: `docker-compose logs -f`
2. Consulte esta documentação
3. Verifique o status dos serviços: `docker-compose ps`

---

**Versão:** 1.0.0  
**Data:** 2025-10-13  
**Status:** ✅ Implementação Completa das 13 Abas
