#!/bin/bash

# ======== SCRIPT DE GESTIÓN DEL BOT ========

BOT_DIR="/home/ubuntu/trading"
SERVICE_NAME="trading-bot"

case "$1" in
    start)
        echo "🚀 Iniciando bot de trading..."
        sudo systemctl start $SERVICE_NAME
        sudo systemctl enable $SERVICE_NAME
        echo "✅ Bot iniciado y configurado para auto-inicio"
        ;;
    stop)
        echo "🛑 Deteniendo bot de trading..."
        sudo systemctl stop $SERVICE_NAME
        sudo systemctl disable $SERVICE_NAME
        echo "✅ Bot detenido"
        ;;
    restart)
        echo "🔄 Reiniciando bot de trading..."
        sudo systemctl restart $SERVICE_NAME
        echo "✅ Bot reiniciado"
        ;;
    status)
        echo "📊 Estado del bot:"
        sudo systemctl status $SERVICE_NAME
        ;;
    logs)
        echo "📋 Últimos logs del bot:"
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    install)
        echo "🔧 Instalando bot como servicio..."
        sudo cp trading-bot.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable $SERVICE_NAME
        echo "✅ Servicio instalado y habilitado"
        ;;
    update)
        echo "📦 Actualizando bot..."
        cd $BOT_DIR
        git pull origin main
        source trading_bot_env/bin/activate
        pip install -r requirements.txt
        sudo systemctl restart $SERVICE_NAME
        echo "✅ Bot actualizado y reiniciado"
        ;;
    *)
        echo "🤖 Script de gestión del Bot de Trading"
        echo ""
        echo "Uso: $0 {start|stop|restart|status|logs|install|update}"
        echo ""
        echo "Comandos disponibles:"
        echo "  start   - Inicia el bot"
        echo "  stop    - Detiene el bot"
        echo "  restart - Reinicia el bot"
        echo "  status  - Muestra el estado"
        echo "  logs    - Muestra los logs en tiempo real"
        echo "  install - Instala el bot como servicio"
        echo "  update  - Actualiza el bot desde git"
        echo ""
        echo "📱 Comandos de Telegram:"
        echo "  • iniciar - Inicia el trading"
        echo "  • consultar - Muestra mensajes"
        echo "  • finalizar - Detiene el trading"
        echo "  • estado - Muestra estado"
        exit 1
        ;;
esac 