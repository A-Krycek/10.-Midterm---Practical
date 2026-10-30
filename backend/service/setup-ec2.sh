#!/usr/bin/env bash
# Script de aprovisionamiento rápido y configuración para Amazon EC2 (Ubuntu / Debian)
# Ejecutar en la instancia EC2 con: bash service/setup-ec2.sh

set -e

echo "=========================================================="
echo "  Despliegue Automatizado: FastAPI URL Shortener en EC2   "
echo "=========================================================="

# 1. Obtener la IP pública
echo "[1/6] Detectando dirección IP pública..."
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)
PUBLIC_IP=""
if [ -n "$TOKEN" ]; then
    PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
fi

if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s https://checkip.amazonaws.com 2>/dev/null || curl -s https://ifconfig.me 2>/dev/null || true)
fi

if [ -n "$PUBLIC_IP" ]; then
    echo "IP pública detectada: $PUBLIC_IP"
    read -p "Presiona ENTER para usar esta IP o escribe una diferente: " USER_IP
    PUBLIC_IP=${USER_IP:-$PUBLIC_IP}
else
    read -p "Ingresa la IP pública de tu instancia EC2: " PUBLIC_IP
fi

if [ -z "$PUBLIC_IP" ]; then
    echo "Error: Se requiere una dirección IP pública para configurar BASE_URL."
    exit 1
fi

# 2. Actualizar sistema e instalar paquetes base
echo "[2/6] Instalando dependencias del sistema operativo (Python3, venv, git)..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl

# 3. Preparar entorno virtual
echo "[3/6] Creando entorno virtual de Python e instalando dependencias..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 4. Crear archivo .env
echo "[4/6] Generando archivo de configuración .env..."
cat <<EOF > "$BACKEND_DIR/.env"
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=url_shortener_links
BASE_URL=http://${PUBLIC_IP}:8000
CORS_ORIGINS=*
EOF

# 5. Configurar servicio systemd
echo "[5/6] Instalando y habilitando servicio systemd persistente..."
CURRENT_USER=$(whoami)
SERVICE_PATH="/etc/systemd/system/urlshortener.service"

sudo bash -c "cat <<EOF > $SERVICE_PATH
[Unit]
Description=FastAPI URL Shortener Service (EC2)
After=network.target

[Service]
User=${CURRENT_USER}
Group=${CURRENT_USER}
WorkingDirectory=${BACKEND_DIR}
EnvironmentFile=${BACKEND_DIR}/.env
ExecStart=${BACKEND_DIR}/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable urlshortener
sudo systemctl restart urlshortener

# 6. Verificación del servicio
echo "[6/6] Verificando salud del servicio..."
sleep 2

if sudo systemctl is-active --quiet urlshortener; then
    echo ""
    echo "=========================================================="
    echo "  ¡DESPLIEGUE EXITOSO EN AMAZON EC2!                     "
    echo "=========================================================="
    echo "  - Estado del servicio: Activo (running)"
    echo "  - Endpoint raíz:       http://${PUBLIC_IP}:8000/"
    echo "  - Chequeo de salud:    http://${PUBLIC_IP}:8000/health"
    echo "  - Documentación API:   http://${PUBLIC_IP}:8000/docs"
    echo ""
    echo "  Comandos útiles:"
    echo "    Ver estado:   sudo systemctl status urlshortener"
    echo "    Ver logs:     sudo journalctl -u urlshortener -f"
    echo "    Reiniciar:    sudo systemctl restart urlshortener"
    echo "=========================================================="
else
    echo "ADVERTENCIA: El servicio no se encuentra en estado 'active'. Revisa los logs con:"
    echo "sudo journalctl -u urlshortener -n 50"
fi
