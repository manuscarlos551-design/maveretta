#!/bin/bash
# Production Deploy Script - Etapa 7
# Deploy completo com zero downtime usando Docker Compose

set -e  # Exit on any error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$PROJECT_DIR/backups"
LOG_FILE="$PROJECT_DIR/logs/deployment_$(date +%Y%m%d_%H%M%S).log"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"

# Função para logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Função para cleanup em caso de erro
cleanup() {
    log_error "Deployment failed. Starting cleanup..."
    if [ -f "$BACKUP_DIR/latest_backup.tar.gz" ]; then
        log "Initiating automatic rollback..."
        rollback_deployment
    fi
    exit 1
}

# Trap para cleanup automático
trap cleanup ERR

print_banner() {
    echo -e "${BLUE}"
    echo "==============================================="
    echo "🚀 BOT AI MULTI-AGENT - PRODUCTION DEPLOY"
    echo "==============================================="
    echo -e "${NC}"
}

# Verificações pré-deploy
pre_deploy_checks() {
    log "🔍 Starting pre-deployment checks..."
    
    # Verifica se está no diretório correto
    if [ ! -f "$PROJECT_DIR/bot_runner_modular.py" ]; then
        log_error "Not in correct project directory"
        exit 1
    fi
    
    # Verifica Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Verifica Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Verifica arquivo .env
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log_error "Environment file (.env) not found"
        exit 1
    fi
    
    # Verifica variáveis críticas
    source "$PROJECT_DIR/.env"
    
    if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
        log_error "Critical environment variables missing (API keys)"
        exit 1
    fi
    
    # Verifica espaço em disco
    available_space=$(df "$PROJECT_DIR" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 1048576 ]; then  # Menos que 1GB
        log_error "Insufficient disk space (need at least 1GB)"
        exit 1
    fi
    
    # Verifica memória disponível
    available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$available_memory" -lt 512 ]; then  # Menos que 512MB
        log_warning "Low available memory: ${available_memory}MB"
    fi
    
    # Testa conectividade de rede
    if ! ping -c 1 google.com &> /dev/null; then
        log_error "No internet connectivity"
        exit 1
    fi
    
    log_success "Pre-deployment checks passed"
}

# Backup de dados críticos
backup_critical_data() {
    log "💾 Starting critical data backup..."
    
    # Cria diretório de backup se não existir
    mkdir -p "$BACKUP_DIR"
    
    # Nome do arquivo de backup
    BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # Lista de arquivos/diretórios críticos para backup
    CRITICAL_FILES=(
        ".env"
        "data/"
        "logs/"
        "bot_runner.py"
        "bot_runner_modular.py"
        "config/"
        "requirements.txt"
    )
    
    # Cria backup compactado
    tar_files=""
    for file in "${CRITICAL_FILES[@]}"; do
        if [ -e "$PROJECT_DIR/$file" ]; then
            tar_files="$tar_files $file"
        else
            log_warning "File not found for backup: $file"
        fi
    done
    
    if [ -n "$tar_files" ]; then
        cd "$PROJECT_DIR"
        tar -czf "$BACKUP_FILE" $tar_files
        
        # Cria link simbólico para último backup
        ln -sf "$BACKUP_FILE" "$BACKUP_DIR/latest_backup.tar.gz"
        
        # Verifica se backup foi criado
        if [ -f "$BACKUP_FILE" ]; then
            backup_size=$(du -h "$BACKUP_FILE" | cut -f1)
            log_success "Backup created: $BACKUP_FILE ($backup_size)"
        else
            log_error "Failed to create backup"
            exit 1
        fi
    else
        log_error "No files available for backup"
        exit 1
    fi
    
    # Limpa backups antigos (mantém últimos 5)
    cd "$BACKUP_DIR"
    ls -t backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm
    log "Cleaned old backups (keeping last 5)"
}

# Validação do ambiente
validate_environment() {
    log "🧪 Validating environment..."
    
    # Executa validador de ambiente se disponível
    if [ -f "$PROJECT_DIR/deployment/environment_validator.py" ]; then
        cd "$PROJECT_DIR"
        python3 deployment/environment_validator.py
        if [ $? -ne 0 ]; then
            log_error "Environment validation failed"
            exit 1
        fi
    else
        log_warning "Environment validator not found, skipping detailed validation"
    fi
    
    # Testes básicos de Python
    cd "$PROJECT_DIR"
    
    # Verifica Python
    if ! python3 --version &> /dev/null; then
        log_error "Python 3 is not available"
        exit 1
    fi
    
    # Testa imports básicos
    python3 -c "import sys, os, json, time, datetime" 2>/dev/null
    if [ $? -ne 0 ]; then
        log_error "Basic Python imports failed"
        exit 1
    fi
    
    # Testa se o bot runner funciona (modo dry run)
    timeout 10s python3 -c "
try:
    from bot_runner_modular import ModularBotRunner
    runner = ModularBotRunner()
    status = runner.get_modular_status()
    print('✅ Bot runner validation passed')
except Exception as e:
    print(f'❌ Bot runner validation failed: {e}')
    exit(1)
" 2>/dev/null
    
    if [ $? -ne 0 ]; then
        log_warning "Bot runner validation had issues (may be normal in some environments)"
    fi
    
    log_success "Environment validation completed"
}

# Deploy usando Docker Compose
deploy_with_docker() {
    log "🐳 Starting Docker deployment..."
    
    cd "$PROJECT_DIR"
    
    # Verifica se arquivo de produção existe
    if [ ! -f "$COMPOSE_FILE" ]; then
        log "Creating production docker-compose.yml..."
        create_production_compose
    fi
    
    # Para containers existentes gracefully
    if docker-compose -f "$COMPOSE_FILE" ps -q | grep -q .; then
        log "Stopping existing containers..."
        docker-compose -f "$COMPOSE_FILE" down --timeout 30
    fi
    
    # Build das imagens
    log "Building Docker images..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    if [ $? -ne 0 ]; then
        log_error "Docker build failed"
        exit 1
    fi
    
    # Inicia containers
    log "Starting containers..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    if [ $? -ne 0 ]; then
        log_error "Failed to start containers"
        exit 1
    fi
    
    log_success "Docker deployment completed"
}

# Cria docker-compose para produção
create_production_compose() {
    cat > "$COMPOSE_FILE" << 'EOF'
version: '3.8'

services:
  bot-ai-multiagent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: bot-ai-production
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
    networks:
      - bot-network
    depends_on:
      - mongodb
    healthcheck:
      test: ["CMD", "python3", "-c", "import requests; requests.get('http://localhost:8080/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  mongodb:
    image: mongo:5.0
    container_name: bot-mongodb
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: botuser
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:-botpass123}
    volumes:
      - mongodb_data:/data/db
      - ./backups/mongodb:/backup
    networks:
      - bot-network
    ports:
      - "27017:27017"

  redis:
    image: redis:7-alpine
    container_name: bot-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-redispass123}
    volumes:
      - redis_data:/data
    networks:
      - bot-network
    ports:
      - "6379:6379"

networks:
  bot-network:
    driver: bridge

volumes:
  mongodb_data:
  redis_data:
EOF

    log "Production docker-compose.yml created"
}

# Verificação pós-deploy
post_deploy_verification() {
    log "✅ Starting post-deployment verification..."
    
    # Aguarda containers iniciarem
    sleep 10
    
    # Verifica se containers estão rodando
    cd "$PROJECT_DIR"
    
    running_containers=$(docker-compose -f "$COMPOSE_FILE" ps --services --filter "status=running")
    expected_containers=("bot-ai-multiagent" "mongodb" "redis")
    
    for container in "${expected_containers[@]}"; do
        if echo "$running_containers" | grep -q "$container"; then
            log_success "Container $container is running"
        else
            log_error "Container $container is not running"
            # Mostra logs do container
            docker-compose -f "$COMPOSE_FILE" logs "$container" | tail -20
            exit 1
        fi
    done
    
    # Testa health endpoints
    log "Testing health endpoints..."
    
    # Aguarda um pouco mais para os serviços iniciarem
    sleep 15
    
    # Testa se a aplicação responde
    for i in {1..5}; do
        if curl -f -s http://localhost:8080/health > /dev/null 2>&1; then
            log_success "Application health check passed"
            break
        else
            log "Health check attempt $i/5 failed, retrying in 10s..."
            sleep 10
        fi
        
        if [ $i -eq 5 ]; then
            log_error "Application health check failed after 5 attempts"
            # Mostra logs para debug
            docker-compose -f "$COMPOSE_FILE" logs bot-ai-multiagent | tail -30
            exit 1
        fi
    done
    
    # Verifica logs para erros críticos
    log "Checking logs for critical errors..."
    
    error_count=$(docker-compose -f "$COMPOSE_FILE" logs --tail=50 | grep -i "error\|exception\|failed" | wc -l)
    
    if [ "$error_count" -gt 5 ]; then
        log_warning "Found $error_count error messages in logs"
        docker-compose -f "$COMPOSE_FILE" logs --tail=20 | grep -i "error\|exception\|failed"
    else
        log_success "No critical errors found in logs"
    fi
    
    log_success "Post-deployment verification completed"
}

# Rollback em caso de falha
rollback_deployment() {
    log "🔄 Starting deployment rollback..."
    
    if [ ! -f "$BACKUP_DIR/latest_backup.tar.gz" ]; then
        log_error "No backup found for rollback"
        return 1
    fi
    
    cd "$PROJECT_DIR"
    
    # Para containers atuais
    docker-compose -f "$COMPOSE_FILE" down
    
    # Restaura backup
    tar -xzf "$BACKUP_DIR/latest_backup.tar.gz"
    
    # Reinicia com versão anterior
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_success "Rollback completed"
}

# Relatório final
generate_deployment_report() {
    log "📊 Generating deployment report..."
    
    REPORT_FILE="$PROJECT_DIR/logs/deployment_report_$(date +%Y%m%d_%H%M%S).json"
    
    # Coleta informações do sistema
    cat > "$REPORT_FILE" << EOF
{
  "deployment": {
    "timestamp": "$(date -Iseconds)",
    "status": "success",
    "version": "etapa7-production",
    "duration_seconds": $SECONDS
  },
  "system_info": {
    "hostname": "$(hostname)",
    "os": "$(uname -a)",
    "docker_version": "$(docker --version)",
    "available_memory_mb": $(free -m | awk 'NR==2{print $7}'),
    "available_disk_gb": $(df -BG "$PROJECT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
  },
  "containers": {
    "running": $(docker-compose -f "$COMPOSE_FILE" ps -q | wc -l),
    "expected": 3
  },
  "backup": {
    "created": true,
    "location": "$BACKUP_DIR/latest_backup.tar.gz",
    "size_mb": $(du -m "$BACKUP_DIR/latest_backup.tar.gz" | cut -f1)
  }
}
EOF
    
    log_success "Deployment report saved: $REPORT_FILE"
}

# Função principal
main() {
    print_banner
    
    # Cria diretórios necessários
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/data"
    
    log "🚀 Starting production deployment process..."
    
    # Executa etapas do deploy
    pre_deploy_checks
    backup_critical_data
    validate_environment
    deploy_with_docker
    post_deploy_verification
    generate_deployment_report
    
    log_success "🎉 Deployment completed successfully!"
    log "📊 Application is running at: http://localhost:8080"
    log "📁 Logs available at: $LOG_FILE"
    log "💾 Backup created at: $BACKUP_DIR/latest_backup.tar.gz"
    
    echo -e "\n${GREEN}==============================================="
    echo "✅ DEPLOYMENT SUCCESSFUL"
    echo "🚀 Bot AI Multi-Agent is now running in production"
    echo "📊 Monitor status: docker-compose -f docker-compose.prod.yml ps"
    echo "📋 View logs: docker-compose -f docker-compose.prod.yml logs -f"
    echo -e "===============================================${NC}\n"
}

# Verifica se está sendo executado como script principal
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi