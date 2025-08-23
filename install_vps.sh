#!/bin/bash

# ======== SCRIPT DE INSTALACIÓN PARA VPS ========
echo "🤖 Instalando Bot de Trading en VPS..."

# Actualizar el sistema
echo "📦 Actualizando sistema..."
sudo apt update && sudo apt upgrade -y

# Instalar Python y pip
echo "🐍 Instalando Python..."
sudo apt install python3 python3-pip python3-venv -y

# Crear entorno virtual
echo "🔧 Creando entorno virtual..."
python3 -m venv trading_bot_env
source trading_bot_env/bin/activate

# Instalar dependencias
echo "📚 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Crear directorio para logs
echo "📁 Creando directorios..."
mkdir -p logs
mkdir -p data

# Dar permisos de ejecución
chmod +x *.py

echo "✅ Instalación completada!"
echo ""
echo "🚀 Para ejecutar el bot:"
echo "   source trading_bot_env/bin/activate"
echo "   python SPKUSDT/neutralspk.py"
echo ""
echo "📱 Comandos de Telegram disponibles:"
echo "   • iniciar - Inicia el bot"
echo "   • consultar - Muestra mensajes"
echo "   • finalizar - Detiene el bot"
echo "   • estado - Muestra estado" 