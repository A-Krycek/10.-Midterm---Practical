# Guía Rápida de Configuración de systemd en EC2

`systemd` es el sistema de inicialización y gestión de servicios estándar en distribuciones Linux modernas (Ubuntu, Debian, Amazon Linux 2023, RedHat). Garantiza que el backend de FastAPI:
- Se ejecute en segundo plano sin depender de una sesión interactiva SSH.
- Se reinicie automáticamente si ocurre algún fallo o caída imprevista (`Restart=always`).
- Se inicie automáticamente si la máquina virtual de EC2 es reiniciada.

---

## Estructura del Archivo de Servicio

El archivo se encuentra en `backend/service/urlshortener.service`:

```ini
[Unit]
Description=FastAPI URL Shortener Service (EC2)
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/aws-url-shortener/backend
EnvironmentFile=/home/ubuntu/aws-url-shortener/backend/.env
ExecStart=/home/ubuntu/aws-url-shortener/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

> **Nota:** Si estás usando Amazon Linux 2023 en lugar de Ubuntu, cambia `User=ubuntu` y `Group=ubuntu` por `User=ec2-user` y `Group=ec2-user`, y actualiza las rutas sustituyendo `/home/ubuntu` por `/home/ec2-user`.

---

## Comandos de Instalación y Administración

### 1. Copiar el archivo al directorio del sistema
```bash
sudo cp /home/ubuntu/aws-url-shortener/backend/service/urlshortener.service /etc/systemd/system/
```

### 2. Recargar el demonio de systemd
```bash
sudo systemctl daemon-reload
```

### 3. Habilitar el servicio para arranque automático al reiniciar la máquina
```bash
sudo systemctl enable urlshortener
```

### 4. Iniciar el servicio
```bash
sudo systemctl start urlshortener
```

### 5. Consultar el estado del servicio
```bash
sudo systemctl status urlshortener
```

### 6. Reiniciar o detener el servicio
```bash
# Reiniciar el servicio tras cambios en el código
sudo systemctl restart urlshortener

# Detener el servicio
sudo systemctl stop urlshortener
```

### 7. Ver los registros en tiempo real (Logs)
Para verificar las peticiones HTTP y depurar cualquier incidencia:
```bash
sudo journalctl -u urlshortener -f
```
*(Presiona `Ctrl + C` para salir del visor de logs).*
