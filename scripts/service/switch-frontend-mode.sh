#!/bin/bash
# Switch between production (static files) and development (Vite hot reload) modes

NGINX_PROD_CONF="/home/gabe/ares/internaldocuments/deployment/nginx-ares.conf"
NGINX_DEV_CONF="/home/gabe/ares/internaldocuments/deployment/nginx-ares-dev.conf"
NGINX_ENABLED="/etc/nginx/sites-enabled/ares"

case "$1" in
    dev)
        echo "Switching to DEVELOPMENT mode (hot reload)..."
        sudo cp "$NGINX_DEV_CONF" "$NGINX_ENABLED"
        sudo nginx -t && sudo systemctl reload nginx
        echo ""
        echo "Now run: npm run dev"
        echo "Then access: https://aresai.space"
        echo ""
        echo "Hot reload is now active. Changes to src/ will appear immediately."
        ;;
    prod)
        echo "Switching to PRODUCTION mode (static files)..."
        sudo cp "$NGINX_PROD_CONF" "$NGINX_ENABLED"
        sudo nginx -t && sudo systemctl reload nginx
        echo ""
        echo "Don't forget to build first: npm run build"
        echo "Then access: https://aresai.space"
        ;;
    status)
        if grep -q "proxy_pass http://127.0.0.1:3000" "$NGINX_ENABLED" 2>/dev/null; then
            echo "Currently in: DEVELOPMENT mode (Vite dev server)"
            if pgrep -f "vite" > /dev/null; then
                echo "Vite dev server: RUNNING"
            else
                echo "Vite dev server: NOT RUNNING (run: npm run dev)"
            fi
        else
            echo "Currently in: PRODUCTION mode (static files)"
        fi
        ;;
    *)
        echo "Usage: $0 {dev|prod|status}"
        echo ""
        echo "  dev    - Switch to development mode (Vite hot reload)"
        echo "  prod   - Switch to production mode (static files)"
        echo "  status - Show current mode"
        exit 1
        ;;
esac
