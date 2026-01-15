#!/bin/bash
# ARES Services Manager - Non-Docker Setup
# This script manages all ARES services with auto-restart capability

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# PID file directory
PID_DIR="$SCRIPT_DIR/.pids"
mkdir -p "$PID_DIR"

# Log directory
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Load NVM if available (for Node.js)
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    source "$HOME/.nvm/nvm.sh"
fi

# Ensure Node.js is in PATH
if ! command -v node &> /dev/null && [ -d "$HOME/.nvm/versions/node" ]; then
    export PATH="$HOME/.nvm/versions/node/$(ls -1 $HOME/.nvm/versions/node | tail -1)/bin:$PATH"
fi

# Function to check if a process is running
is_running() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to find a service process by pattern
find_service_process() {
    local service=$1
    case $service in
        frontend)
            # Look for vite process
            pgrep -f "node.*vite" | head -1
            ;;
        backend)
            # Look for Django runserver
            pgrep -f "python.*manage.py runserver" | head -1
            ;;
        openrouter)
            # Look for openrouter service
            pgrep -f "tsx.*openrouter-service" | head -1
            ;;
    esac
}

# Function to start a service
start_service() {
    local name=$1
    local pid_file="$PID_DIR/$name.pid"
    local log_file="$LOG_DIR/$name.log"
    
    # Check if already running
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if is_running "$pid"; then
            echo -e "${YELLOW}$name is already running (PID: $pid)${NC}"
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    
    echo -e "${GREEN}Starting $name...${NC}"
    
    case $name in
        openrouter)
            cd "$SCRIPT_DIR/openrouter-service"
            # Use dev mode for hot reload during development
            if [ "$ARES_ENV" = "production" ]; then
                npm run build
                npm start > "$log_file" 2>&1 &
            else
                npm run dev > "$log_file" 2>&1 &
            fi
            echo $! > "$pid_file"
            cd "$SCRIPT_DIR"
            ;;
        backend)
            # Try uv first, then venv, then system python
            if command -v uv &> /dev/null; then
                uv run python manage.py runserver 0.0.0.0:8000 > "$log_file" 2>&1 &
            elif [ -d ".venv" ]; then
                source .venv/bin/activate
                python manage.py runserver 0.0.0.0:8000 > "$log_file" 2>&1 &
            else
                python3 manage.py runserver 0.0.0.0:8000 > "$log_file" 2>&1 &
            fi
            echo $! > "$pid_file"
            ;;
        frontend)
            cd "$SCRIPT_DIR"
            # Check if port 3000 is in use before starting
            if command -v lsof &> /dev/null; then
                local port_pid=$(lsof -ti:3000 2>/dev/null || echo "")
                if [ -n "$port_pid" ]; then
                    echo -e "${RED}Port 3000 is already in use (PID: $port_pid). Killing it...${NC}"
                    kill "$port_pid" 2>/dev/null || true
                    sleep 1
                    if kill -0 "$port_pid" 2>/dev/null; then
                        kill -9 "$port_pid" 2>/dev/null || true
                    fi
                    sleep 1
                fi
            elif command -v fuser &> /dev/null; then
                if fuser 3000/tcp &> /dev/null; then
                    echo -e "${RED}Port 3000 is already in use. Freeing it...${NC}"
                    fuser -k 3000/tcp 2>/dev/null || true
                    sleep 2
                fi
            fi
            # Use dev mode for hot reload during development
            if [ "$ARES_ENV" = "production" ]; then
                npm run build
                # In production, you'd serve with nginx or a static server
                # For now, still use dev server
                npm run dev > "$log_file" 2>&1 &
            else
                npm run dev > "$log_file" 2>&1 &
            fi
            echo $! > "$pid_file"
            ;;
    esac
    
    # Wait a moment and check if it started
    sleep 2
    local pid=$(cat "$pid_file" 2>/dev/null || echo "")
    if is_running "$pid"; then
        echo -e "${GREEN}$name started successfully (PID: $pid)${NC}"
        return 0
    else
        echo -e "${RED}$name failed to start. Check $log_file for details.${NC}"
        rm -f "$pid_file"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local name=$1
    local pid_file="$PID_DIR/$name.pid"
    local pid=""
    
    # First try to get PID from file
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
    fi
    
    # If no PID file or PID not running, try to find the process
    if [ -z "$pid" ] || ! is_running "$pid"; then
        pid=$(find_service_process "$name")
    fi
    
    # Special handling for frontend: kill all vite processes and free port 3000
    if [ "$name" = "frontend" ]; then
        echo -e "${YELLOW}Stopping $name...${NC}"
        
        # Kill all vite processes
        pkill -f "node.*vite" 2>/dev/null || true
        
        # Also kill any process using port 3000
        if command -v lsof &> /dev/null; then
            local port_pid=$(lsof -ti:3000 2>/dev/null || echo "")
            if [ -n "$port_pid" ]; then
                echo -e "${YELLOW}Killing process using port 3000 (PID: $port_pid)...${NC}"
                kill "$port_pid" 2>/dev/null || true
                sleep 1
                # Force kill if still running
                if kill -0 "$port_pid" 2>/dev/null; then
                    kill -9 "$port_pid" 2>/dev/null || true
                fi
            fi
        elif command -v fuser &> /dev/null; then
            fuser -k 3000/tcp 2>/dev/null || true
        fi
        
        # Wait for processes to fully terminate
        sleep 2
        
        # Verify no vite processes are running
        local remaining=$(pgrep -f "node.*vite" | wc -l)
        if [ "$remaining" -gt 0 ]; then
            echo -e "${YELLOW}Force killing remaining vite processes...${NC}"
            pkill -9 -f "node.*vite" 2>/dev/null || true
            sleep 1
        fi
        
        rm -f "$pid_file"
        echo -e "${GREEN}$name stopped${NC}"
        return 0
    fi
    
    if [ -z "$pid" ] || ! is_running "$pid"; then
        echo -e "${YELLOW}$name is not running${NC}"
        rm -f "$pid_file"
        return 0
    fi
    
    echo -e "${YELLOW}Stopping $name (PID: $pid)...${NC}"
    kill "$pid" 2>/dev/null || true
    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! is_running "$pid"; then
            break
        fi
        sleep 1
    done
    # Force kill if still running
    if is_running "$pid"; then
        kill -9 "$pid" 2>/dev/null || true
    fi
    
    rm -f "$pid_file"
    echo -e "${GREEN}$name stopped${NC}"
}

# Function to restart a service
restart_service() {
    local name=$1
    stop_service "$name"
    # Wait longer for frontend to ensure port 3000 is fully released
    if [ "$name" = "frontend" ]; then
        sleep 3
        # Verify port 3000 is free before starting
        if command -v lsof &> /dev/null; then
            local port_in_use=$(lsof -ti:3000 2>/dev/null | wc -l)
            if [ "$port_in_use" -gt 0 ]; then
                echo -e "${YELLOW}Port 3000 still in use, waiting a bit more...${NC}"
                sleep 2
            fi
        fi
    else
        sleep 1
    fi
    start_service "$name"
}

# Function to check status of all services
status_services() {
    echo -e "${GREEN}=== ARES Services Status ===${NC}"
    for service in openrouter backend frontend; do
        local pid_file="$PID_DIR/$service.pid"
        local pid=""
        local found_pid=""
        
        # First check PID file
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if is_running "$pid"; then
                echo -e "${GREEN}✓ $service: running (PID: $pid from file)${NC}"
                continue
            else
                # Stale PID file, remove it
                rm -f "$pid_file"
            fi
        fi
        
        # If no valid PID file, try to find the process
        found_pid=$(find_service_process "$service")
        if [ -n "$found_pid" ] && is_running "$found_pid"; then
            echo -e "${YELLOW}⚠ $service: running (PID: $found_pid, but no PID file - started outside script?)${NC}"
            # Optionally update the PID file
            echo "$found_pid" > "$pid_file"
        else
            echo -e "${RED}✗ $service: not running${NC}"
        fi
    done
}

# Function to monitor and auto-restart services
monitor_services() {
    echo -e "${GREEN}Starting service monitor (auto-restart enabled)...${NC}"
    while true; do
        for service in openrouter backend frontend; do
            local pid_file="$PID_DIR/$service.pid"
            if [ -f "$pid_file" ]; then
                local pid=$(cat "$pid_file")
                if ! is_running "$pid"; then
                    echo -e "${YELLOW}$service crashed, restarting...${NC}"
                    start_service "$service"
                fi
            else
                # Service not running, start it
                start_service "$service"
            fi
        done
        sleep 5
    done
}

# Main command handler
case "${1:-}" in
    start)
        if [ -n "$2" ]; then
            # Start specific service
            start_service "$2"
        else
            # Start all services
            start_service openrouter
            sleep 2
            start_service backend
            sleep 2
            start_service frontend
            echo -e "${GREEN}All services started. Use './start-ares-services.sh status' to check status.${NC}"
        fi
        ;;
    stop)
        if [ -n "$2" ]; then
            # Stop specific service
            stop_service "$2"
        else
            # Stop all services
            stop_service frontend
            stop_service backend
            stop_service openrouter
        fi
        ;;
    restart)
        if [ -n "$2" ]; then
            # Restart specific service
            restart_service "$2"
        else
            # Restart all services
            restart_service openrouter
            sleep 2
            restart_service backend
            sleep 2
            restart_service frontend
        fi
        ;;
    status)
        status_services
        ;;
    monitor)
        # Start all services first
        start_service openrouter
        sleep 2
        start_service backend
        sleep 2
        start_service frontend
        # Then monitor
        monitor_services
        ;;
    logs)
        if [ -z "$2" ]; then
            echo "Usage: $0 logs <service>"
            echo "Services: openrouter, backend, frontend"
            exit 1
        fi
        tail -f "$LOG_DIR/$2.log"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|monitor|logs} [service]"
        echo ""
        echo "Commands:"
        echo "  start [service]    - Start all services or specific service (openrouter, backend, frontend)"
        echo "  stop [service]    - Stop all services or specific service"
        echo "  restart [service] - Restart all services or specific service"
        echo "  status            - Show status of all services"
        echo "  monitor           - Start services and monitor with auto-restart"
        echo "  logs <service>    - Show logs for a service (e.g., logs backend)"
        exit 1
        ;;
esac

