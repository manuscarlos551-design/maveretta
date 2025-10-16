#!/bin/bash
# Quick Validation Script - Maveretta Bot Turbinada
# Versão: 2.5.0

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║           MAVERETTA BOT - VALIDAÇÃO RÁPIDA TURBINADA                    ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
    fi
}

echo "🔍 VALIDANDO CORREÇÕES..."
echo ""

# 1. Check requirements.txt
echo "1️⃣ Verificando requirements.txt..."
if ! grep -q "^-e $" requirements.txt; then
    echo -e "${GREEN}✅ requirements.txt: Erro -e corrigido${NC}"
else
    echo -e "${RED}❌ requirements.txt: Ainda contém erro -e${NC}"
fi

# 2. Check if anthropic is present
if grep -q "anthropic" requirements.txt; then
    echo -e "${GREEN}✅ requirements.txt: anthropic adicionado${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt: anthropic não encontrado${NC}"
fi

# 3. Check docker-compose.yml TTL
echo ""
echo "2️⃣ Verificando docker-compose.yml..."
if grep -q "storage.tsdb.retention.time" docker-compose.yml; then
    echo -e "${GREEN}✅ docker-compose.yml: TTL Prometheus configurado${NC}"
else
    echo -e "${YELLOW}⚠️  docker-compose.yml: TTL Prometheus não encontrado${NC}"
fi

# 4. Check MongoDB config
echo ""
echo "3️⃣ Verificando MongoDB config..."
if [ -f "config/settings/mongodb_config.py" ]; then
    echo -e "${GREEN}✅ mongodb_config.py: Arquivo criado${NC}"
else
    echo -e "${RED}❌ mongodb_config.py: Arquivo não encontrado${NC}"
fi

# 5. Check Prometheus recording rules
echo ""
echo "4️⃣ Verificando Prometheus recording rules..."
if [ -f "prometheus/rules/maveretta_turbinada_rules.yml" ]; then
    echo -e "${GREEN}✅ maveretta_turbinada_rules.yml: Arquivo criado${NC}"
else
    echo -e "${RED}❌ maveretta_turbinada_rules.yml: Arquivo não encontrado${NC}"
fi

# 6. Check Streamlit app
echo ""
echo "5️⃣ Verificando Streamlit app.py..."
if grep -q "lazy: bool = False" interfaces/web/app.py; then
    echo -e "${GREEN}✅ app.py: Lazy loading adicionado${NC}"
else
    echo -e "${YELLOW}⚠️  app.py: Lazy loading não encontrado${NC}"
fi

# 7. Check documentation
echo ""
echo "6️⃣ Verificando documentação..."
if [ -f "CHANGELOG_FINAL.md" ]; then
    echo -e "${GREEN}✅ CHANGELOG_FINAL.md: Criado${NC}"
else
    echo -e "${RED}❌ CHANGELOG_FINAL.md: Não encontrado${NC}"
fi

if [ -f "EMBEDS_FIX_REPORT.md" ]; then
    echo -e "${GREEN}✅ EMBEDS_FIX_REPORT.md: Criado${NC}"
else
    echo -e "${RED}❌ EMBEDS_FIX_REPORT.md: Não encontrado${NC}"
fi

if [ -f "BUILD_HEALTH_REPORT.md" ]; then
    echo -e "${GREEN}✅ BUILD_HEALTH_REPORT.md: Criado${NC}"
else
    echo -e "${RED}❌ BUILD_HEALTH_REPORT.md: Não encontrado${NC}"
fi

# 8. Check .env
echo ""
echo "7️⃣ Verificando .env..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env: Arquivo presente${NC}"
    
    # Check API keys (don't print values)
    if grep -q "OPENAI_API_KEY" .env; then
        echo -e "${GREEN}✅ OPENAI_API_KEY: Definida${NC}"
    else
        echo -e "${YELLOW}⚠️  OPENAI_API_KEY: Não encontrada${NC}"
    fi
    
    if grep -q "BINANCE_API_KEY" .env; then
        echo -e "${GREEN}✅ BINANCE_API_KEY: Definida${NC}"
    else
        echo -e "${YELLOW}⚠️  BINANCE_API_KEY: Não encontrada${NC}"
    fi
else
    echo -e "${RED}❌ .env: Arquivo não encontrado${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "✅ VALIDAÇÃO COMPLETA!"
echo ""
echo "📋 Próximos passos:"
echo "   1. docker compose build --no-cache"
echo "   2. docker compose up -d"
echo "   3. curl http://localhost/health"
echo "═══════════════════════════════════════════════════════════════════════════"
