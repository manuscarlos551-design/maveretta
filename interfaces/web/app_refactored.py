# interfaces/web/app.py
"""
Maveretta Bot - Dashboard Principal com 13 Abas Integradas
Interface Streamlit unificada com painéis Grafana embedados NATIVOS
Todas as 13 abas conforme mapeamento AUDITORIA_MAPEAMENTO_STREAMLIT_GRAFANA
LEGACY: Removido todos os st.metric, consultas Prometheus diretas, gráficos locais
"""
importar sistema operacional
importar sistema
importar urllib.parse
registro de importação
de pathlib importar Caminho

# Configurar registro
logging.basicConfig(nível=logging.INFO)
registrador = logging.getLogger(__nome__)

# -------------------------
# IMPORTAÇÕES DE TERCEIROS
# -------------------------
importar streamlit como st
importar streamlit.components.v1 como componentes

# -------------------------
# CONFIGURAÇÃO DA PÁGINA
# -------------------------
st.set_page_config(
    page_title="Maveretta Bot - Orquestração de Negociação de IA",
    ícone_de_página="🤖",
    layout="amplo",
    initial_sidebar_state="expandido"
)

# -------------------------
# CONSTANTES
# -------------------------
GRAFANA_BASE_URL = os.getenv("GRAFANA_BASE_URL", "http://localhost/grafana").rstrip("/")
APP_DIR = Caminho(__arquivo__).pai

# -------------------------
# AUXILIAR: INCORPORANDO PAINEL GRAFANA
# -------------------------
def grafana_panel(uid: str, slug: str, panel_id: int, altura: int = 300,
                  time_from: str = "agora-6h", time_to: str = "agora"):
    """
    Renderiza painel nativo do Grafana via iframe /d-solo
    
    Argumentos:
        uid: UID do dashboard (extraído do JSON real)
        slug: Slug do título do dashboard (kebab-case)
        panel_id: ID do painel dentro do dashboard
        altura: Altura em pixels (KPI: 260, série temporal: 400, tabela: 500)
        time_from: Intervalo temporal inicial (padrão: agora-6h)
        time_to: Intervalo temporal final (padrão: agora)
    """
    parâmetros = {
        "orgId": "1",
        "panelId": str(id_do_painel),
        "tema": "escuro",
        "quiosque": "",
        "de": tempo_de,
        "para": tempo_para,
    }
    url = f"{GRAFANA_BASE_URL}/d-solo/{uid}/{urllib.parse.quote(slug)}?{urllib.parse.urlencode(params)}"
    st.components.v1.iframe(url, altura=altura, rolagem=Falso)

# -------------------------
# CSS TEMA ESCURO PREMIUM
# -------------------------
TEMA_CSS = """
<estilo>
:raiz {
  --bg: #0a0d14;
  --painel: #141922;
  --painel2: #1c2531;
  --painel3: #252d3d;
  --texto: #e8eaef;
  --texto-secundário: #b8c2d3;
  --silenciado: #8a95a6;
  --acento: #f5c451;
  --accent-hover: #f7d373;
  --verde: #22c55e;
  --vermelho: #ef4444;
  --azul: #3b82f6;
  --roxo: #8b5cf6;
  --borda: #2a3441;
  --luz de borda: #3d4654;
  --sombra: rgba(0,0,0,0.25);
}

html, corpo, .stApp {
  cor de fundo: var(--bg);
  cor: var(--texto);
  família de fontes: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
}

.cabeçalho-principal {
  alinhamento de texto: centro;
  margem: 0 0 1,5rem 0;
  preenchimento: 1rem 0;
  plano de fundo: gradiente linear (135 graus, var (--panel2) 0%, var (--panel) 100%);
  raio da borda: 12px;
  borda: 1px var sólido (--border);
  caixa-sombra: 0 4px 20px var(--sombra);
  posição: relativa;
  estouro: oculto;
}

.cabeçalho-principal::antes de {
  contente: '';
  posição: absoluta;
  topo: 0;
  esquerda: 0;
  direita: 0;
  altura: 3px;
  plano de fundo: gradiente linear(90deg, var(--accent), var(--green), var(--blue));
}

.título-principal {
  tamanho da fonte: 28px;
  espessura da fonte: 800;
  espaçamento entre letras: -0,025em;
  cor: var(--texto);
  margem: 0 0 0,25rem 0;
  sombra de texto: 0 2px 4px rgba(0,0,0,0.3);
  exibição: flexível;
  alinhar-itens: centro;
  justificar-conteúdo: centro;
}

.subtítulo principal {
  tamanho da fonte: 13px;
  cor: var(--muted);
  espessura da fonte: 500;
  opacidade: 0,8;
}

.stTabs [data-baseweb="lista-de-guias"] {
  lacuna: 2px;
  preenchimento: 6px;
  fundo: var(--painel);
  raio da borda: 12px;
  borda: 1px var sólido (--border);
  margem inferior: 2rem;
  estouro-x: automático;
  largura da barra de rolagem: fina;
  scrollbar-color: var(--accent) transparente;
}

.stTabs [data-baseweb="guia"] {
  altura: 48px;
  largura mínima: 85px;
  preenchimento: 10px 12px;
  raio da borda: 10px;
  fundo: transparente;
  cor: var(--muted);
  borda: 1px sólido transparente;
  espessura da fonte: 600;
  tamanho da fonte: 12px;
  transição: todos os 0,2s cúbicos-bezier(0,4, 0, 0,2, 1);
  cursor: ponteiro;
  espaço em branco: nowrap;
  posição: relativa;
  estouro: oculto;
}

.stTabs [data-baseweb="tab"]:passe o mouse {
  fundo: var(--panel2);
  cor: var(--text-secondary);
  cor da borda: var(--border-light);
  transformar: translateY(-1px);
}

.stTabs [aria-selected="true"] {
  plano de fundo: gradiente linear (135 graus, var (--panel3) 0%, var (--panel2) 100%);
  cor: var(--texto);
  cor da borda: var(--accent);
  caixa-sombra: 0 2px 8px rgba(245, 196, 81, 0,15);
  posição: relativa;
}

.stTabs [aria-selected="true"]::depois {
  contente: '';
  posição: absoluta;
  fundo: 0;
  esquerda: 50%;
  transformar: translateX(-50%);
  largura: 60%;
  altura: 2px;
  fundo: var(--accent);
  raio da borda: 1px;
}

.cabeçalho-da-seção {
  tamanho da fonte: 18px;
  espessura da fonte: 700;
  margem: 2rem 0 1rem;
  preenchimento: 0,75rem 1rem;
  fundo: gradiente linear (90 graus, var (--panel2) 0%, transparente 100%);
  borda esquerda: 4px sólido var(--accent);
  raio da borda: 0 8px 8px 0;
  cor: var(--texto);
}

.grafana-incorporar {
  borda: 1px var sólido (--border);
  raio da borda: 8px;
  estouro: oculto;
  cor de fundo: var(--panel2);
  margem inferior: 1rem;
  transição: todos os 0,3s de facilidade;
}

.grafana-embed:passe o mouse {
  cor da borda: var(--border-light);
  caixa-sombra: 0 4px 12px var(--sombra);
}

@media (largura máxima: 899px) {
  .stTabs [data-baseweb="lista-de-guias"] {
    estouro-x: rolagem;
    largura da barra de rolagem: fina;
  }
  
  .stTabs [data-baseweb="guia"] {
    largura mínima: 95px;
    tamanho da fonte: 12px;
    preenchimento: 10px 12px;
  }
  
  .título-principal {
    tamanho da fonte: 22px;
  }
  
  .cabeçalho-da-seção {
    tamanho da fonte: 16px;
  }
}
</estilo>
"""

st.markdown(THEME_CSS, unsafe_allow_html=True)

# -------------------------
# CABEÇALHO
# -------------------------
st.markdown('''
<div class="cabeçalho-principal">
    <h1 class="main-title">🤖 Maveretta Bot - Orquestração de Negociação de IA</h1>
    <p class="main-subtitle">Dashboard Integrado com Painéis Nativos do Grafana</p>
</div>
''', unsafe_allow_html=Verdadeiro)

# -------------------------
# 13 ABAS CONFORME MAPEAMENTO
# -------------------------
guias = st.tabs([
    "📊 Visão Geral",
    "📈 Operações",
    "🎰 Caça-níqueis",
    "🏦 Tesouro",
    "🎮 Controles",
    "🧠 Insights da IA",
    "📋 Auditório",
    "📝 Registros",
    "🚨 Alertas",
    "🔬 Testes Retrospectivos",
    "🎯 Estratégias",
    "🎼 Orquestração",
    "💰 Carteira"
])


# ========================================
# ABA: 📊 Visão geral
# ========================================
com abas[0]:
    st.markdown('<div class="section-header">📊 Visão geral</div>', unsafe_allow_html=True)

    # Taxa de aprovação de consenso (ID do painel: 3)
    grafana_panel(uid="agente-drilldown-fase3", slug="agente-drilldown-fase-3", panel_id=3, altura=200)

    # Motivos de bloqueio de risco (ID do painel: 5)
    grafana_panel(uid="agente-drilldown-fase3", slug="agente-drilldown-fase-3", panel_id=5, altura=300)

    # Consenso aprovado (por símbolo) (ID do painel: 3)
    grafana_panel(uid="agentes-visão-geral-fase-3", slug="agentes-visão-geral-fase-3", panel_id=3, altura=300)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Total de posições abertas (ID do painel: 6)
    grafana_panel(uid="agentes-visão-geral-fase-3", slug="agentes-visão-geral-fase-3", panel_id=6, altura=200)

    # Rodadas de consenso (1h) (ID do painel: 1)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=1, height=300)

    # Consenso aprovado (1h) (ID do painel: 2)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=2, height=300)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Taxa de aprovação (1h) (ID do painel: 3)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=3, height=200)

    # Risco bloqueado por motivo (ID do painel: 7)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=7, height=300)

    # Status da conexão Bybit (ID do painel: 2)
    grafana_panel(uid="maveretta-bybit-live", slug="maveretta-bybit-live", panel_id=2, altura=200)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Status de conexão da Coinbase (ID do painel: 2)
    grafana_panel(uid="maveretta-coinbase-live", slug="maveretta-coinbase-live", panel_id=2, altura=200)

    # Análise de preços em tempo real - $symbol (ID do painel: 1)
    grafana_panel(uid="maveretta-dynamic-live", slug="maveretta-dynamic-symbol-analysis", panel_id=1, altura=300)

    # Preço atual (ID do painel: 2)
    grafana_panel(uid="maveretta-dynamic-live", slug="maveretta-dynamic-symbol-analysis", panel_id=2, height=300)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Volume 24h (ID do painel: 3)
    grafana_panel(uid="maveretta-dynamic-live", slug="maveretta-dynamic-symbol-analysis", panel_id=3, altura=300)

    # Latência (ID do painel: 4)
    grafana_panel(uid="maveretta-dynamic-live", slug="maveretta-dynamic-symbol-analysis", panel_id=4, altura=300)

    # Status da conexão (ID do painel: 5)
    grafana_panel(uid="maveretta-dynamic-live", slug="maveretta-dynamic-symbol-analysis", panel_id=5, altura=200)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Status dos Serviços (ID do Painel: 4)
    grafana_panel(uid="maveretta-infraestrutura", slug="maveretta-infraestrutura-sistema", panel_id=4, altura=200)

    # Tráfego de rede (ID do painel: 7)
    grafana_panel(uid="maveretta-infraestrutura", slug="maveretta-infraestrutura-sistema", panel_id=7, altura=300)

    # E/S de disco (ID do painel: 8)
    grafana_panel(uid="maveretta-infraestrutura", slug="maveretta-infraestrutura-sistema", panel_id=8, altura=300)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Status de conexão do KuCoin (ID do painel: 2)
    grafana_panel(uid="maveretta-kucoin-live", slug="maveretta-kucoin-live", panel_id=2, height=260)

    # Visão Geral do Mercado - BTC/USDT (ID do painel: 1)
    grafana_panel(uid="maveretta-market-overview", slug="maveretta-market-overview", panel_id=1, height=400)

    # Volume 24h (ID do painel: 2)
    grafana_panel(uid="maveretta-market-overview", slug="maveretta-market-overview", panel_id=2, height=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Status da conexão OKX (ID do painel: 2)
    grafana_panel(uid="maveretta-okx-live", slug="maveretta-okx-live", panel_id=2, altura=260)

    # Gráfico de Preços em Tempo Real (ID do painel: 7)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=7, altura=400)

    # Preço Atual (Top 10) (ID do painel: 12)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=12, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Ciclos Completos (ID do painel: 16)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=16, altura=400)

    # Mensagens WebSocket (ID do painel: 17)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=17, altura=400)

    # ATR Médio (ID do painel: 19)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=19, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Status Conexão (ID do painel: 20)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=20, altura=260)

    # Saúde / Tempo de atividade - Todos os serviços (ID do painel: 21)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=21, altura=400)

    # Ciclos Completados (1h) (ID do Painel: 2)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=2, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Total de Capital (USDT) (ID do Painel: 3)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=3, altura=260)

    # Status de conexão (ID do painel: 4)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=4, altura=260)

    # Taxa de Execução (Ciclos/s) (ID do Painel: 6)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=6, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Top 10 de preços de criptomoedas (USDT) (ID do painel: 1)
    grafana_panel(uid="maveretta-top10-live", slug="maveretta-top-10-prices", panel_id=1, altura=400)

    # Tabela dos 10 principais preços (ID do painel: 2)
    grafana_panel(uid="maveretta-top10-live", slug="maveretta-top-10-prices", panel_id=2, altura=500)

    # Taxa de sucesso de arbitragem (ID do painel: 1)
    grafana_panel(uid="pernas-de-arbitragem-de-orquestração", slug="pernas-de-arbitragem-de-orquestração", panel_id=1, altura=260)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Pernas por status (ID do painel: 2)
    grafana_panel(uid="pernas-de-arbitragem-de-orquestração", slug="pernas-de-arbitragem-de-orquestração", panel_id=2, altura=260)

    # Eventos de Auto-Hedge (ID do Painel: 6)
    grafana_panel(uid="pernas-de-arbitragem-de-orquestração", slug="pernas-de-arbitragem-de-orquestração", panel_id=6, altura=400)

    # Visão geral do status do IA (ID do painel: 1)
    grafana_panel(uid="orquestração-ia-saúde", slug="orquestração-ia-saúde", panel_id=1, altura=260)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Status da troca (ID do painel: 3)
    grafana_panel(uid="saúde-local-de-orquestração", slug="saúde-local-de-orquestração", panel_id=3, altura=260)

    # Status do limite de taxa (ID do painel: 4)
    grafana_panel(uid="saúde-local-de-orquestração", slug="saúde-local-de-orquestração", panel_id=4, altura=260)

# ========================================
# ABA: 📈 Operações
# ========================================
com abas[1]:
    st.markdown('<div class="section-header">📈 Operações</div>', unsafe_allow_html=True)

    # Operações em papel com lucros e perdas não realizados (ID do painel: 5)
    grafana_panel(uid="agentes-visão-geral-fase-3", slug="agentes-visão-geral-fase-3", panel_id=5, altura=400)

    # Uso da CPU (ID do painel: 1)
    grafana_panel(uid="maveretta-infraestrutura", slug="maveretta-infraestrutura-sistema", panel_id=1, altura=400)

    # Uso de memória (ID do painel: 2)
    grafana_panel(uid="maveretta-infraestrutura", slug="maveretta-infraestrutura-sistema", panel_id=2, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Uso do disco (ID do painel: 3)
    grafana_panel(uid="maveretta-infraestrutura", slug="maveretta-infraestrutura-sistema", panel_id=3, altura=400)

    # Uso da CPU do contêiner (ID do painel: 5)
    grafana_panel(uid="maveretta-infraestrutura", slug="maveretta-infraestrutura-sistema", panel_id=5, altura=400)

    # Uso de memória do contêiner (ID do painel: 6)
    grafana_panel(uid="maveretta-infraestrutura", slug="maveretta-infraestrutura-sistema", panel_id=6, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Latência Média (ID do painel: 18)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=18, altura=400)

    # Tempo de execução entre locais (ID do painel: 4)
    grafana_panel(uid="pernas-de-arbitragem-de-orquestração", slug="pernas-de-arbitragem-de-orquestração", panel_id=4, altura=400)

    # Latência de troca (ID do painel: 1)
    grafana_panel(uid="saúde-local-de-orquestração", slug="saúde-local-de-orquestração", panel_id=1, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Desvio do relógio (ID do painel: 2)
    grafana_panel(uid="saúde-local-de-orquestração", slug="saúde-local-de-orquestração", panel_id=2, altura=400)

# ========================================
# ABA: 🎰 Caça-níqueis
# ========================================
com abas[2]:
    st.markdown('<div class="section-header">🎰 Slots</div>', unsafe_allow_html=True)

    # Slots Ativos (ID do Painel: 15)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=15, altura=400)

    # Slots Ativos (ID do Painel: 1)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=1, altura=400)

    # Histórico de Slots Ativos (ID do painel: 5)
    grafana_panel(uid="maveretta-slots-live", slug="maveretta-trading-slots", panel_id=5, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Linha do tempo dos estados dos slots (ID do painel: 1)
    grafana_panel(uid="linha do tempo dos slots de orquestração", slug="linha do tempo dos slots de orquestração", panel_id=1, altura=400)

    # Distribuição de estados de slot (ID do painel: 2)
    grafana_panel(uid="linha do tempo dos slots de orquestração", slug="linha do tempo dos slots de orquestração", panel_id=2, altura=400)

    # Contagem de slots ativos (ID do painel: 3)
    grafana_panel(uid="linha do tempo dos slots de orquestração", slug="linha do tempo dos slots de orquestração", panel_id=3, altura=260)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Alterações no estado do slot (ID do painel: 4)
    grafana_panel(uid="linha do tempo dos slots de orquestração", slug="linha do tempo dos slots de orquestração", panel_id=4, altura=400)

# ========================================
# ABA: 🏦 Tesouro
# ========================================
com abas[3]:
    st.markdown('<div class="section-header">🏦 Tesouro</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")

# ========================================
# ABA: 🎮 Controles
# ========================================
com abas[4]:
    st.markdown('<div class="section-header">🎮 Controles</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")

# ========================================
#ABA: 🧠 Insights de IA
# ========================================
com abas[5]:
    st.markdown('<div class="section-header">🧠 Insights de IA</div>', unsafe_allow_html=True)

    # Mapa de calor de confiança (ID do painel: 2)
    grafana_panel(uid="agente-drilldown-fase3", slug="agente-drilldown-fase-3", panel_id=2, altura=500)

    # Status do agente (Em execução=1, Parado=0) (ID do painel: 1)
    grafana_panel(uid="agentes-visão-geral-fase-3", slug="agentes-visão-geral-fase-3", panel_id=1, altura=260)

    # Decisões por hora (por agente) (ID do painel: 2)
    grafana_panel(uid="agentes-visão-geral-fase-3", slug="agentes-visão-geral-fase-3", panel_id=2, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Média de confiança de consenso (ID do painel: 4)
    grafana_panel(uid="agentes-visão-geral-fase-3", slug="agentes-visão-geral-fase-3", panel_id=4, altura=400)

    # Redução do Agente % (ID do Painel: 7)
    grafana_panel(uid="agentes-visão-geral-fase-3", slug="agentes-visão-geral-fase-3", panel_id=7, altura=400)

    # Confiança média (ID do painel: 4)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=4, height=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Cronograma da Fase de Consenso (propor/desafiar/decidir) (ID do Painel: 5)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=5, height=400)

    # Mapa de calor de confiança por agente (ID do painel: 6)
    grafana_panel(uid="maveretta-consensus-flow", slug="maveretta-consensus-flow", panel_id=6, height=500)

    # Pernas com falha por motivo (ID do painel: 5)
    grafana_panel(uid="pernas-de-arbitragem-de-orquestração", slug="pernas-de-arbitragem-de-orquestração", panel_id=5, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Confiança na decisão por estratégia (ID do painel: 1)
    grafana_panel(uid="orquestração-decisão-conf", slug="orquestração-decisão-conf", panel_id=1, altura=260)

    # Confiança na decisão por IA (ID do painel: 2)
    grafana_panel(uid="orquestração-decisão-conf", slug="orquestração-decisão-conf", panel_id=2, altura=400)

    # Distribuição de confiança (ID do painel: 3)
    grafana_panel(uid="orquestração-decisão-conf", slug="orquestração-decisão-conf", panel_id=3, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Decisões de alta confiança (>80%) (ID do painel: 4)
    grafana_panel(uid="orquestração-decisão-conf", slug="orquestração-decisão-conf", panel_id=4, altura=400)

    # Decisões de baixa confiança (<50%) (ID do painel: 5)
    grafana_panel(uid="orquestração-decisão-conf", slug="orquestração-decisão-conf", panel_id=5, altura=400)

    # Confiança média por slot (ID do painel: 6)
    grafana_panel(uid="orquestração-decisão-conf", slug="orquestração-decisão-conf", panel_id=6, altura=260)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Latência IA (ms) (ID do painel: 2)
    grafana_panel(uid="orquestração-ia-saúde", slug="orquestração-ia-saúde", panel_id=2, altura=400)

    # Tempo de atividade IA % (ID do painel: 3)
    grafana_panel(uid="orquestração-ia-saúde", slug="orquestração-ia-saúde", panel_id=3, altura=400)

    # Erros por IA (ID do painel: 4)
    grafana_panel(uid="orquestração-ia-saúde", slug="orquestração-ia-saúde", panel_id=4, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

# ========================================
# ABA: 📋 Auditório
# ========================================
com abas[6]:
    st.markdown('<div class="section-header">📋 Auditoria</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")

# ========================================
# ABA: 📝 Registros
# ========================================
com abas[7]:
    st.markdown('<div class="section-header">📝 Registros</div>', unsafe_allow_html=True)

    # Erros de conexão (ID do painel: 5)
    grafana_panel(uid="saúde-local-de-orquestração", slug="saúde-local-de-orquestração", panel_id=5, altura=400)

# ========================================
# ABA: 🚨 Alertas
# ========================================
com abas[8]:
    st.markdown('<div class="section-header">🚨 Alertas</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")

# ========================================
# ABA: 🔬 Backtests
# ========================================
com abas[9]:
    st.markdown('<div class="section-header">🔬 Backtests</div>', unsafe_allow_html=True)

    # Bybit Equity (USDT) (ID do painel: 1)
    grafana_panel(uid="maveretta-bybit-live", slug="maveretta-bybit-live", panel_id=1, altura=260)

    # Coinbase Equity (USDT) (ID do painel: 1)
    grafana_panel(uid="maveretta-coinbase-live", slug="maveretta-coinbase-live", panel_id=1, altura=260)

    # KuCoin Equity (USDT) (ID do painel: 1)
    grafana_panel(uid="maveretta-kucoin-live", slug="maveretta-kucoin-live", panel_id=1, height=260)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Patrimônio da KuCoin ao longo do tempo (ID do painel: 3)
    grafana_panel(uid="maveretta-kucoin-live", slug="maveretta-kucoin-live", panel_id=3, height=260)

    # OKX Equity (USDT) (ID do painel: 1)
    grafana_panel(uid="maveretta-okx-live", slug="maveretta-okx-live", panel_id=1, altura=260)

    # Carteira Real (USDT) (ID do painel: 13)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=13, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # Carteira Real (BRL) (ID do painel: 14)
    grafana_panel(uid="maveretta-overview-live", slug="maveretta-overview-live", panel_id=14, altura=400)

# ========================================
# ABA: 🎯 Estratégias
# ========================================
com abas[10]:
    st.markdown('<div class="section-header">🎯 Estratégias</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")

# ========================================
# ABA: 🎼 Orquestração
# ========================================
com abas[11]:
    st.markdown('<div class="section-header">🎼 Orquestração</div>', unsafe_allow_html=True)

    # Cronograma de decisão (Propor/Desafiar/Decidir) (ID do painel: 1)
    grafana_panel(uid="agente-drilldown-fase3", slug="agente-drilldown-fase-3", panel_id=1, altura=400)

    # Latência de decisão (p50, p95) (ID do painel: 4)
    grafana_panel(uid="agente-drilldown-fase3", slug="agente-drilldown-fase-3", panel_id=4, altura=400)

    # P&L de arbitragem (ID do painel: 3)
    grafana_panel(uid="orquestração-arbitragem-pernas", slug="orquestração-arbitragem-pernas", panel_id=3, altura=400)

    st.markdown('<div style="margem: 1.5rem 0;"></div>', unsafe_allow_html=True)

# ========================================
# ABA: 💰 Carteira
# ========================================
com abas[12]:
    st.markdown('<div class="section-header">💰 Cartão</div>', unsafe_allow_html=True)

    st.info("🚧 Seção em desenvolvimento. Painéis serão adicionados em breve.")