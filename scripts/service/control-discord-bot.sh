#!/bin/bash
# Easy Discord Bot control script

SERVICE_NAME="ares-discord-bot"

case "$1" in
    start)
        echo "Starting Discord Bot..."
        sudo systemctl start ${SERVICE_NAME}
        sleep 2
        if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
            echo "✓ Discord Bot started"
        else
            echo "✗ Failed to start Discord Bot"
            echo "Check logs: sudo journalctl -u ${SERVICE_NAME} -n 50"
            exit 1
        fi
        ;;
    stop)
        echo "Stopping Discord Bot..."
        sudo systemctl stop ${SERVICE_NAME}
        sleep 1
        if ! sudo systemctl is-active --quiet ${SERVICE_NAME}; then
            echo "✓ Discord Bot stopped"
        else
            echo "✗ Failed to stop Discord Bot"
            exit 1
        fi
        ;;
    status)
        if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
            echo "✓ Discord Bot is running"
            sudo systemctl status ${SERVICE_NAME} --no-pager -l
        else
            echo "✗ Discord Bot is not running"
        fi
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    logs)
        echo "=== Discord Bot Logs (last 50 lines) ==="
        sudo journalctl -u ${SERVICE_NAME} -n 50 --no-pager
        ;;
    follow)
        echo "Following Discord Bot logs (Ctrl+C to exit)..."
        sudo journalctl -u ${SERVICE_NAME} -f
        ;;
    enable)
        echo "Enabling Discord Bot to start on boot..."
        sudo systemctl enable ${SERVICE_NAME}
        echo "✓ Discord Bot will start on boot"
        ;;
    disable)
        echo "Disabling Discord Bot from starting on boot..."
        sudo systemctl disable ${SERVICE_NAME}
        echo "✓ Discord Bot will not start on boot"
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart|logs|follow|enable|disable}"
        echo ""
        echo "Easy control for Discord Bot service"
        echo "  start    - Start the Discord Bot"
        echo "  stop     - Stop the Discord Bot"
        echo "  status   - Check if Discord Bot is running"
        echo "  restart  - Restart the Discord Bot"
        echo "  logs     - Show last 50 lines of logs"
        echo "  follow   - Follow logs in real-time"
        echo "  enable   - Enable auto-start on boot"
        echo "  disable  - Disable auto-start on boot"
        exit 1
        ;;
esac

exit 0

