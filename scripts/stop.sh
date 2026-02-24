#!/bin/bash
# Lantrn Agent Builder - Stop Script for Mac Ultra + NAS Deployment
# Graceful shutdown of all services

set -e

# ============================================
# Configuration
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ============================================
# Helper Functions
# ============================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ============================================
# Shutdown Banner
# ============================================
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                                                              ║${NC}"
echo -e "${BOLD}${CYAN}║           🛑 LANTRN AGENT BUILDER - SHUTDOWN                 ║${NC}"
echo -e "${BOLD}${CYAN}║           Graceful Service Termination                       ║${NC}"
echo -e "${BOLD}${CYAN}║                                                              ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# Parse Arguments
# ============================================
FORCE=false
CLEANUP=false
VOLUMES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -c|--cleanup)
            CLEANUP=true
            shift
            ;;
        -v|--volumes)
            VOLUMES=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -f, --force     Force stop without graceful shutdown"
            echo "  -c, --cleanup   Remove orphaned containers and clean up"
            echo "  -v, --volumes   Remove volumes (WARNING: deletes all data)"
            echo "  -h, --help      Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                  # Graceful shutdown"
            echo "  $0 --force          # Force stop"
            echo "  $0 --cleanup        # Stop and clean up"
            echo "  $0 --volumes        # Stop and remove all data"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================
# Check Docker
# ============================================
log_step "🔍 Checking Docker Status"

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
fi

if ! docker info &> /dev/null; then
    log_warning "Docker daemon is not running"
    exit 0
fi

cd "$PROJECT_DIR"

# Check if services are running
if ! docker compose ps -q 2>/dev/null | grep -q .; then
    log_info "No services are currently running"
    
    if [ "$CLEANUP" = true ]; then
        log_info "Running cleanup..."
        docker compose down --remove-orphans 2>/dev/null || true
    fi
    
    exit 0
fi

# ============================================
# Display Current Status
# ============================================
log_step "📊 Current Service Status"

docker compose ps

# ============================================
# Graceful Shutdown
# ============================================
log_step "🛑 Stopping Services"

if [ "$FORCE" = true ]; then
    log_warning "Force stopping services..."
    docker compose kill
else
    log_info "Initiating graceful shutdown..."
    
    # Send SIGTERM for graceful shutdown
    docker compose stop --timeout 30
    
    # Wait for services to stop
    log_info "Waiting for services to stop..."
    sleep 5
    
    # Check if any services are still running
    RUNNING=$(docker compose ps -q 2>/dev/null | wc -l)
    if [ "$RUNNING" -gt 0 ]; then
        log_warning "Some services are still running, forcing stop..."
        docker compose kill
    fi
fi

log_success "All services stopped"

# ============================================
# Cleanup (Optional)
# ============================================
if [ "$CLEANUP" = true ] || [ "$VOLUMES" = true ]; then
    log_step "🧹 Cleaning Up"
    
    if [ "$VOLUMES" = true ]; then
        log_warning "Removing volumes (all data will be lost)..."
        read -p "Are you sure? This will delete all models, blueprints, and runs! (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose down -v --remove-orphans
            log_success "All containers and volumes removed"
        else
            log_info "Volume removal cancelled"
            docker compose down --remove-orphans
        fi
    else
        log_info "Removing containers and orphaned resources..."
        docker compose down --remove-orphans
        log_success "Cleanup complete"
    fi
fi

# ============================================
# Final Status
# ============================================
log_step "📋 Final Status"

echo ""
docker compose ps 2>/dev/null || echo "No containers running"
echo ""

# ============================================
# Display Summary
# ============================================
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║                                                              ║${NC}"
echo -e "${BOLD}${GREEN}║           ✅ SHUTDOWN COMPLETE                               ║${NC}"
echo -e "${BOLD}${GREEN}║                                                              ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Useful Commands:${NC}"
echo -e "  🚀 Start services:  ${CYAN}./scripts/start.sh${NC}"
echo -e "  📊 View status:    ${CYAN}docker compose ps${NC}"
echo -e "  📋 View logs:      ${CYAN}docker compose logs${NC}"
echo ""
