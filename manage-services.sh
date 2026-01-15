#!/bin/bash
# ARES Service Manager
# Manage backend (Gunicorn) and frontend (Vite dev) services

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_status() {
    clear
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}           ARES Service Manager${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo ""

    # Backend status
    if systemctl is-active --quiet ares-backend; then
        echo -e "  Backend (Gunicorn):    ${GREEN}● RUNNING${NC}"
    else
        echo -e "  Backend (Gunicorn):    ${RED}○ STOPPED${NC}"
    fi

    # Frontend status
    if systemctl is-active --quiet ares-frontend-dev; then
        echo -e "  Frontend (Vite Dev):   ${GREEN}● RUNNING${NC}"
    else
        echo -e "  Frontend (Vite Dev):   ${RED}○ STOPPED${NC}"
    fi

    # Nginx status
    if systemctl is-active --quiet nginx; then
        echo -e "  Nginx:                 ${GREEN}● RUNNING${NC}"
    else
        echo -e "  Nginx:                 ${RED}○ STOPPED${NC}"
    fi

    # Discord Bot status
    if systemctl is-active --quiet ares-discord-bot; then
        echo -e "  Discord Bot:            ${GREEN}● RUNNING${NC}"
    else
        echo -e "  Discord Bot:            ${RED}○ STOPPED${NC}"
    fi

    # Check which mode nginx is in
    if grep -q "proxy_pass http://127.0.0.1:3000" /etc/nginx/sites-enabled/ares 2>/dev/null; then
        echo -e "  Mode:                  ${YELLOW}DEVELOPMENT${NC} (hot reload)"
    else
        echo -e "  Mode:                  ${BLUE}PRODUCTION${NC} (static files)"
    fi

    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────${NC}"
    echo ""
}

show_menu() {
    echo "  1) Restart Backend"
    echo "  2) Restart Frontend"
    echo "  3) Restart Both"
    echo "  4) Stop Backend"
    echo "  5) Stop Frontend"
    echo "  6) Start Backend"
    echo "  7) Start Frontend"
    echo "  8) View Backend Logs"
    echo "  9) View Frontend Logs"
    echo "  d) Switch to Dev Mode"
    echo "  p) Switch to Prod Mode"
    echo "  b) Start Discord Bot"
    echo "  s) Stop Discord Bot"
    echo "  r) Restart Discord Bot"
    echo "  l) View Discord Bot Logs"
    echo "  R) Refresh Status"
    echo "  q) Quit"
    echo ""
    echo -n "  Select option: "
}

restart_backend() {
    echo -e "\n${YELLOW}Restarting backend...${NC}"
    sudo systemctl restart ares-backend
    sleep 1
    if systemctl is-active --quiet ares-backend; then
        echo -e "${GREEN}Backend restarted successfully${NC}"
    else
        echo -e "${RED}Backend failed to start${NC}"
    fi
    sleep 1
}

restart_frontend() {
    echo -e "\n${YELLOW}Restarting frontend...${NC}"
    sudo systemctl restart ares-frontend-dev
    sleep 1
    if systemctl is-active --quiet ares-frontend-dev; then
        echo -e "${GREEN}Frontend restarted successfully${NC}"
    else
        echo -e "${RED}Frontend failed to start${NC}"
    fi
    sleep 1
}

stop_backend() {
    echo -e "\n${YELLOW}Stopping backend...${NC}"
    sudo systemctl stop ares-backend
    echo -e "${GREEN}Backend stopped${NC}"
    sleep 1
}

stop_frontend() {
    echo -e "\n${YELLOW}Stopping frontend...${NC}"
    sudo systemctl stop ares-frontend-dev
    echo -e "${GREEN}Frontend stopped${NC}"
    sleep 1
}

start_backend() {
    echo -e "\n${YELLOW}Starting backend...${NC}"
    sudo systemctl start ares-backend
    sleep 1
    if systemctl is-active --quiet ares-backend; then
        echo -e "${GREEN}Backend started successfully${NC}"
    else
        echo -e "${RED}Backend failed to start${NC}"
    fi
    sleep 1
}

start_frontend() {
    echo -e "\n${YELLOW}Starting frontend...${NC}"
    sudo systemctl start ares-frontend-dev
    sleep 1
    if systemctl is-active --quiet ares-frontend-dev; then
        echo -e "${GREEN}Frontend started successfully${NC}"
    else
        echo -e "${RED}Frontend failed to start${NC}"
    fi
    sleep 1
}

view_backend_logs() {
    echo -e "\n${BLUE}=== Backend Logs (last 30 lines) ===${NC}\n"
    tail -30 /home/gabe/ares/logs/gunicorn-error.log 2>/dev/null || echo "No logs found"
    echo ""
    echo -n "Press Enter to continue..."
    read
}

view_frontend_logs() {
    echo -e "\n${BLUE}=== Frontend Logs (last 30 lines) ===${NC}\n"
    tail -30 /home/gabe/ares/logs/vite-dev.log 2>/dev/null || echo "No logs found"
    echo ""
    echo -n "Press Enter to continue..."
    read
}

switch_to_dev() {
    echo -e "\n${YELLOW}Switching to DEVELOPMENT mode...${NC}"
    sudo cp /home/gabe/ares/internaldocuments/deployment/nginx-ares-dev.conf /etc/nginx/sites-enabled/ares
    sudo nginx -t && sudo systemctl reload nginx
    echo -e "${GREEN}Switched to dev mode (hot reload enabled)${NC}"
    sleep 1
}

switch_to_prod() {
    echo -e "\n${YELLOW}Switching to PRODUCTION mode...${NC}"
    sudo cp /home/gabe/ares/internaldocuments/deployment/nginx-ares.conf /etc/nginx/sites-enabled/ares
    sudo nginx -t && sudo systemctl reload nginx
    echo -e "${GREEN}Switched to production mode${NC}"
    echo -e "${YELLOW}Note: Run 'npm run build' if you haven't already${NC}"
    sleep 2
}

start_discord_bot() {
    echo -e "\n${YELLOW}Starting Discord Bot...${NC}"
    sudo systemctl start ares-discord-bot
    sleep 1
    if systemctl is-active --quiet ares-discord-bot; then
        echo -e "${GREEN}Discord Bot started successfully${NC}"
    else
        echo -e "${RED}Discord Bot failed to start${NC}"
        echo -e "${YELLOW}Check logs: sudo journalctl -u ares-discord-bot -n 50${NC}"
    fi
    sleep 1
}

stop_discord_bot() {
    echo -e "\n${YELLOW}Stopping Discord Bot...${NC}"
    sudo systemctl stop ares-discord-bot
    echo -e "${GREEN}Discord Bot stopped${NC}"
    sleep 1
}

restart_discord_bot() {
    echo -e "\n${YELLOW}Restarting Discord Bot...${NC}"
    sudo systemctl restart ares-discord-bot
    sleep 1
    if systemctl is-active --quiet ares-discord-bot; then
        echo -e "${GREEN}Discord Bot restarted successfully${NC}"
    else
        echo -e "${RED}Discord Bot failed to start${NC}"
    fi
    sleep 1
}

view_discord_bot_logs() {
    echo -e "\n${BLUE}=== Discord Bot Logs (last 30 lines) ===${NC}\n"
    sudo journalctl -u ares-discord-bot -n 30 --no-pager
    echo ""
    echo -n "Press Enter to continue..."
    read
}

# Main loop
while true; do
    show_status
    show_menu
    read -r choice

    case $choice in
        1) restart_backend ;;
        2) restart_frontend ;;
        3) restart_backend; restart_frontend ;;
        4) stop_backend ;;
        5) stop_frontend ;;
        6) start_backend ;;
        7) start_frontend ;;
        8) view_backend_logs ;;
        9) view_frontend_logs ;;
        d|D) switch_to_dev ;;
        p|P) switch_to_prod ;;
        b|B) start_discord_bot ;;
        s|S) stop_discord_bot ;;
        r) restart_discord_bot ;;
        l|L) view_discord_bot_logs ;;
        R) ;; # Just refresh
        q|Q) echo -e "\n${BLUE}Goodbye!${NC}\n"; exit 0 ;;
        *) echo -e "${RED}Invalid option${NC}"; sleep 1 ;;
    esac
done
