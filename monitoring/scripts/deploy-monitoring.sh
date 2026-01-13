#!/bin/bash
# Comprehensive Monitoring Stack Deployment Script

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITORING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_COMPOSE_FILE="$MONITORING_DIR/docker-compose.monitoring.yml"
LOG_FILE="/var/log/monitoring-deployment.log"

# Default configuration
ENVIRONMENT="${ENVIRONMENT:-production}"
ENABLE_TRACING="${ENABLE_TRACING:-true}"
ENABLE_LOGGING="${ENABLE_LOGGING:-true}"
ENABLE_INCIDENT_RESPONSE="${ENABLE_INCIDENT_RESPONSE:-true}"
ENABLE_CUSTOM_EXPORTERS="${ENABLE_CUSTOM_EXPORTERS:-true}"
DRY_RUN="${DRY_RUN:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    local message="$2"
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        missing_tools+=("docker")
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
        missing_tools+=("docker-compose")
    fi
    
    # Check curl
    if ! command -v curl >/dev/null 2>&1; then
        missing_tools+=("curl")
    fi
    
    # Check jq
    if ! command -v jq >/dev/null 2>&1; then
        missing_tools+=("jq")
    fi
    
    # Check available disk space (minimum 10GB)
    local available_space=$(df / | awk 'NR==2 {print $4}')
    local required_space=10485760  # 10GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        log_error "Insufficient disk space. Required: 10GB, Available: $(($available_space / 1024 / 1024))GB"
        missing_tools+=("disk_space")
    fi
    
    # Check available memory (minimum 4GB)
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    local required_memory=4096  # 4GB in MB
    
    if [[ $available_memory -lt $required_memory ]]; then
        log_warning "Low memory available. Recommended: 4GB, Available: ${available_memory}MB"
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing prerequisites: ${missing_tools[*]}"
        log_info "Please install missing tools and try again"
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

# Create necessary directories
create_directories() {
    log_info "Creating monitoring directories..."
    
    local directories=(
        "/var/log/monitoring"
        "/var/lib/monitoring/{prometheus,grafana,alertmanager}"
        "/etc/monitoring"
        "/opt/monitoring/exporters"
        "/opt/monitoring/scripts"
    )
    
    for dir in "${directories[@]}"; do
        if [[ "$DRY_RUN" == "false" ]]; then
            sudo mkdir -p "$dir" 2>/dev/null || mkdir -p "$dir"
            sudo chown -R $(whoami):$(whoami) "$dir" 2>/dev/null || true
        fi
        log_info "Created directory: $dir"
    done
}

# Setup configuration files
setup_configurations() {
    log_info "Setting up configuration files..."
    
    # Create main docker-compose file
    create_docker_compose
    
    # Setup Prometheus configuration
    if [[ "$DRY_RUN" == "false" ]]; then
        cp "$MONITORING_DIR/config/prometheus.yml" "/etc/monitoring/prometheus.yml"
    fi
    
    # Setup Grafana dashboards
    if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "/var/lib/monitoring/grafana/dashboards"
        cp "$MONITORING_DIR/dashboards"/*.json "/var/lib/monitoring/grafana/dashboards/"
    fi
    
    # Setup alert rules
    if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "/etc/monitoring/alerts"
        cp "$MONITORING_DIR/alerts"/*.yml "/etc/monitoring/alerts/"
    fi
    
    log_success "Configuration files setup completed"
}

# Create main docker-compose file
create_docker_compose() {
    log_info "Creating Docker Compose configuration..."
    
    cat > "$DOCKER_COMPOSE_FILE" << 'EOF'
version: '3.8'

services:
  # Prometheus - Metrics Collection
  prometheus:
    image: prom/prometheus:v2.47.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./alerts:/etc/prometheus/alerts
      - /var/lib/monitoring/prometheus:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    networks:
      - monitoring

  # Grafana - Dashboards and Visualization
  grafana:
    image: grafana/grafana:10.1.0
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - /var/lib/monitoring/grafana:/var/lib/grafana
      - ./dashboards:/etc/grafana/provisioning/dashboards
      - ./config/grafana:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=changeme
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    networks:
      - monitoring

  # AlertManager - Alert Management
  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./config/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - /var/lib/monitoring/alertmanager:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    networks:
      - monitoring

  # Node Exporter - System Metrics
  node-exporter:
    image: prom/node-exporter:v1.6.1
    container_name: node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - monitoring

  # cAdvisor - Container Metrics
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.47.0
    container_name: cadvisor
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:rw
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    privileged: true
    devices:
      - /dev/kmsg
    networks:
      - monitoring

  # Blackbox Exporter - Blackbox Monitoring
  blackbox-exporter:
    image: prom/blackbox-exporter:v0.24.0
    container_name: blackbox-exporter
    ports:
      - "9115:9115"
    volumes:
      - ./config/blackbox.yml:/etc/blackbox_exporter/config.yml
    networks:
      - monitoring

  # Custom Trading Metrics Exporter
  trading-exporter:
    build:
      context: ./exporters/python
      dockerfile: Dockerfile
    container_name: trading-exporter
    ports:
      - "8080:8080"
    volumes:
      - ./exporters/python:/app
      - /var/log/trading-metrics:/var/log
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=trading
      - DB_USER=postgres
      - DB_PASSWORD=changeme
      - COLLECTION_INTERVAL=15
    depends_on:
      - postgres
      - redis
    networks:
      - monitoring

  # Database exporters
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:v0.13.2
    container_name: postgres-exporter
    ports:
      - "9187:9187"
    environment:
      - DATA_SOURCE_NAME=postgresql://postgres:changeme@postgres:5432/postgres?sslmode=disable
    depends_on:
      - postgres
    networks:
      - monitoring

  redis-exporter:
    image: oliver006/redis_exporter:v1.53.0
    container_name: redis-exporter
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=redis://redis:6379
    depends_on:
      - redis
    networks:
      - monitoring

  # Nginx Exporter
  nginx-exporter:
    image: nginx/nginx-prometheus-exporter:0.11.0
    container_name: nginx-exporter
    ports:
      - "9113:9113"
    command:
      - '-nginx.scrape-uri=http://nginx/nginx_status'
    depends_on:
      - nginx
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge

volumes:
  prometheus-data:
  grafana-data:
  alertmanager-data:
EOF

    # Add optional services based on configuration
    if [[ "$ENABLE_TRACING" == "true" ]]; then
        cat >> "$DOCKER_COMPOSE_FILE" << 'EOF'

  # Jaeger - Distributed Tracing
  jaeger:
    image: jaegertracing/all-in-one:1.52
    container_name: jaeger
    ports:
      - "16686:16686"
      - "14268:14268"
    networks:
      - monitoring

  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector:0.88.0
    container_name: otel-collector
    ports:
      - "4317:4317"
      - "4318:4318"
      - "8888:8888"
    volumes:
      - ./tracing/otel-collector.yaml:/etc/otelcol/config.yaml
    networks:
      - monitoring
EOF
    fi
    
    if [[ "$ENABLE_LOGGING" == "true" ]]; then
        cat >> "$DOCKER_COMPOSE_FILE" << 'EOF'

  # Elasticsearch - Log Storage
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    networks:
      - monitoring

  # Kibana - Log Visualization
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - monitoring

  # Logstash - Log Processing
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: logstash
    ports:
      - "5044:5044"
      - "9600:9600"
    volumes:
      - ./logging/config/logstash/logstash.yml:/usr/share/logstash/config/logstash.yml
      - ./logging/config/logstash/pipelines:/usr/share/logstash/pipeline
    environment:
      - "LS_JAVA_OPTS=-Xmx512m -Xms512m"
    depends_on:
      - elasticsearch
    networks:
      - monitoring

  # Filebeat - Log Collection
  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    container_name: filebeat
    user: root
    volumes:
      - ./logging/config/filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - ELASTICSEARCH_HOST=elasticsearch:9200
    networks:
      - monitoring

volumes:
  elasticsearch-data:
EOF
    fi

    log_success "Docker Compose file created: $DOCKER_COMPOSE_FILE"
}

# Setup incident response system
setup_incident_response() {
    if [[ "$ENABLE_INCIDENT_RESPONSE" != "true" ]]; then
        return
    fi
    
    log_info "Setting up incident response system..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Make script executable
        chmod +x "$MONITORING_DIR/incident_response/scripts/incident-response.sh"
        
        # Setup configuration
        cp "$MONITORING_DIR/incident_response/config/incident-response.conf" "/etc/monitoring/incident-response.conf"
        
        # Create systemd service (optional)
        if command -v systemctl >/dev/null 2>&1; then
            create_systemd_service
        fi
    fi
    
    log_success "Incident response system setup completed"
}

# Create systemd service for incident response
create_systemd_service() {
    local service_file="/etc/systemd/system/incident-response.service"
    
    cat > "$service_file" << EOF
[Unit]
Description=Incident Response System for Trading Platform
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$MONITORING_DIR/incident_response/scripts
ExecStart=$MONITORING_DIR/incident_response/scripts/incident-response.sh check-health
Restart=always
RestartSec=10
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable incident-response.service
    
    log_success "Systemd service created: $service_file"
}

# Setup custom exporters
setup_custom_exporters() {
    if [[ "$ENABLE_CUSTOM_EXPORTERS" != "true" ]]; then
        return
    fi
    
    log_info "Setting up custom exporters..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Build Python exporter
        if [[ -f "$MONITORING_DIR/exporters/python/Dockerfile" ]]; then
            docker build -t trading-metrics-exporter:latest "$MONITORING_DIR/exporters/python/"
        fi
    fi
    
    log_success "Custom exporters setup completed"
}

# Start monitoring stack
start_monitoring_stack() {
    log_info "Starting monitoring stack..."
    
    cd "$SCRIPT_DIR"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would start services with: docker-compose up -d"
        return
    fi
    
    # Start services
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" up -d
    fi
    
    # Wait for services to be ready
    wait_for_services
    
    log_success "Monitoring stack started successfully"
}

# Wait for services to be ready
wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    local services=(
        "http://localhost:9090"
        "http://localhost:3000"
        "http://localhost:9093"
    )
    
    for service in "${services[@]}"; do
        log_info "Checking $service..."
        local max_attempts=30
        local attempt=1
        
        while [[ $attempt -le $max_attempts ]]; do
            if curl -f -s "$service" >/dev/null 2>&1; then
                log_success "$service is ready"
                break
            fi
            
            if [[ $attempt -eq $max_attempts ]]; then
                log_warning "$service failed to become ready after $max_attempts attempts"
            else
                sleep 10
                ((attempt++))
            fi
        done
    done
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    local errors=0
    
    # Check Prometheus
    if ! curl -f -s "http://localhost:9090/api/v1/query?query=up" >/dev/null 2>&1; then
        log_error "Prometheus is not responding"
        ((errors++))
    fi
    
    # Check Grafana
    if ! curl -f -s "http://localhost:3000/api/health" >/dev/null 2>&1; then
        log_error "Grafana is not responding"
        ((errors++))
    fi
    
    # Check AlertManager
    if ! curl -f -s "http://localhost:9093/api/v1/status" >/dev/null 2>&1; then
        log_error "AlertManager is not responding"
        ((errors++))
    fi
    
    # Check custom exporters
    if [[ "$ENABLE_CUSTOM_EXPORTERS" == "true" ]]; then
        if ! curl -f -s "http://localhost:8080/metrics" >/dev/null 2>&1; then
            log_error "Custom trading exporter is not responding"
            ((errors++))
        fi
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "All services are responding correctly"
    else
        log_error "$errors service(s) are not responding correctly"
        return 1
    fi
}

# Display deployment information
display_deployment_info() {
    log_info "Deployment Information:"
    echo ""
    echo "Monitoring Stack URLs:"
    echo "  - Prometheus:     http://localhost:9090"
    echo "  - Grafana:        http://localhost:3000 (admin/changeme)"
    echo "  - AlertManager:   http://localhost:9093"
    echo ""
    
    if [[ "$ENABLE_TRACING" == "true" ]]; then
        echo "  - Jaeger:         http://localhost:16686"
        echo "  - OpenTelemetry:  http://localhost:4317 (OTLP)"
        echo ""
    fi
    
    if [[ "$ENABLE_LOGGING" == "true" ]]; then
        echo "  - Elasticsearch:  http://localhost:9200"
        echo "  - Kibana:         http://localhost:5601"
        echo ""
    fi
    
    if [[ "$ENABLE_CUSTOM_EXPORTERS" == "true" ]]; then
        echo "  - Trading Metrics: http://localhost:8080/metrics"
        echo ""
    fi
    
    echo "Configuration Files:"
    echo "  - Main Config:     /etc/monitoring/"
    echo "  - Docker Compose:  $DOCKER_COMPOSE_FILE"
    echo "  - Logs:           /var/log/monitoring/"
    echo ""
    echo "Useful Commands:"
    echo "  - View logs:       docker-compose -f $DOCKER_COMPOSE_FILE logs -f [service]"
    echo "  - Stop services:   docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "  - Restart:         docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo ""
}

# Main deployment function
deploy_monitoring_stack() {
    log_info "Starting deployment of trading system monitoring stack..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Enable Tracing: $ENABLE_TRACING"
    log_info "Enable Logging: $ENABLE_LOGGING"
    log_info "Enable Incident Response: $ENABLE_INCIDENT_RESPONSE"
    log_info "Enable Custom Exporters: $ENABLE_CUSTOM_EXPORTERS"
    log_info "Dry Run: $DRY_RUN"
    
    check_prerequisites
    create_directories
    setup_configurations
    setup_incident_response
    setup_custom_exporters
    start_monitoring_stack
    
    if verify_deployment; then
        log_success "Deployment completed successfully!"
        display_deployment_info
    else
        log_error "Deployment verification failed"
        exit 1
    fi
}

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy comprehensive monitoring stack for trading system.

Options:
    -e, --environment ENV       Set environment (development|staging|production)
    -t, --no-tracing           Disable tracing components
    -l, --no-logging           Disable logging components
    -i, --no-incident          Disable incident response
    -x, --no-exporters         Disable custom exporters
    -d, --dry-run              Show what would be done without executing
    -h, --help                 Show this help message

Environment Variables:
    ENVIRONMENT                 Environment setting
    ENABLE_TRACING             Enable tracing components (true/false)
    ENABLE_LOGGING             Enable logging components (true/false)
    ENABLE_INCIDENT_RESPONSE   Enable incident response (true/false)
    ENABLE_CUSTOM_EXPORTERS    Enable custom exporters (true/false)
    DRY_RUN                    Dry run mode (true/false)

Examples:
    $0                         # Standard deployment
    $0 --environment staging   # Deploy to staging
    $0 --dry-run              # Preview changes
    $0 --no-logging           # Deploy without ELK stack
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--no-tracing)
                ENABLE_TRACING="false"
                shift
                ;;
            -l|--no-logging)
                ENABLE_LOGGING="false"
                shift
                ;;
            -i|--no-incident)
                ENABLE_INCIDENT_RESPONSE="false"
                shift
                ;;
            -x|--no-exporters)
                ENABLE_CUSTOM_EXPORTERS="false"
                shift
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Main execution
main() {
    parse_arguments "$@"
    
    # Check if running as root for system operations
    if [[ $EUID -eq 0 ]] && [[ "$DRY_RUN" == "false" ]]; then
        log_warning "Running as root. This is not recommended for production deployments."
    fi
    
    deploy_monitoring_stack
}

# Signal handlers for graceful shutdown
trap 'log_info "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"