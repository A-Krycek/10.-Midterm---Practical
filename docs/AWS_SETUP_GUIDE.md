# Guía de Despliegue en AWS: Acortador de Enlaces

Esta guía detalla paso a paso la configuración y despliegue de los tres servicios requeridos para el examen práctico: **Amazon DynamoDB**, **Amazon EC2** y **Amazon S3**.

---

## 1. Configuración de Amazon DynamoDB

1. Inicia sesión en la **Consola de Administración de AWS**.
2. Dirígete al servicio **DynamoDB** y haz clic en **Create table** (Crear tabla).
3. Configura los siguientes parámetros:
   - **Table name (Nombre de la tabla):** `url_shortener_links`
   - **Partition key (Clave de partición):** `short_code` (Tipo: **String**)
   - **Sort key (Clave de ordenación):** *Dejar en blanco (no se requiere).*
   - **Table settings (Configuración de la tabla):** Selecciona **Customize settings** (Personalizar) y elige **On-demand** (Bajo demanda) para optimizar costos dentro de la capa gratuita, o **Default settings** (Provisión por defecto).
4. Haz clic en **Create table**.
5. Espera unos segundos hasta que el estado de la tabla sea **Active**.
6. Copia el **ARN** de la tabla (lo necesitarás en el paso 2 para la política IAM). Lo encuentras en la pestaña *Additional info* (Información adicional):
   `arn:aws:dynamodb:<tu-region>:<tu-cuenta-id>:table/url_shortener_links`

---

## 2. Creación del Rol IAM para la Instancia EC2

Para cumplir con la buena práctica de seguridad (mínimo privilegio y sin claves quemadas en el código), la instancia EC2 usará un rol IAM con credenciales temporales gestionadas automáticamente por Boto3.

1. Dirígete al servicio **IAM** en la consola de AWS.
2. En el menú lateral, selecciona **Policies** (Políticas) > **Create policy** (Crear política).
3. Cambia a la pestaña **JSON** y pega la siguiente política de privilegios mínimos:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBTableAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/url_shortener_links"
    }
  ]
}
```

4. Haz clic en **Next**, asigna como nombre: `URLShortenerDynamoDBPolicy` y haz clic en **Create policy**.
5. Ahora, en el menú lateral de IAM, haz clic en **Roles** > **Create role** (Crear rol).
6. Configuración del rol:
   - **Trusted entity type:** AWS service (Servicio de AWS).
   - **Use case:** EC2.
   - Haz clic en **Next**.
7. En el buscador de permisos, busca y selecciona la política que acabas de crear: `URLShortenerDynamoDBPolicy`.
8. Haz clic en **Next**, nombra al rol: `EC2-URLShortener-Role` y haz clic en **Create role**.

---

## 3. Lanzamiento y Configuración de Amazon EC2

### 3.1 Crear el Security Group
1. Ve al servicio **EC2** > **Security Groups** > **Create security group**.
2. Nombre: `url-shortener-sg`.
3. Descripción: `Permite trafico SSH y puerto 8000 para FastAPI URL Shortener`.
4. En **Inbound rules** (Reglas de entrada), añade:
   - **Regla 1 (SSH):** Tipo: `SSH`, Puerto: `22`, Origen: `My IP` (Tu dirección IP actual) o `0.0.0.0/0`.
   - **Regla 2 (FastAPI):** Tipo: `Custom TCP`, Puerto: `8000`, Origen: `0.0.0.0/0` (Cualquier lugar, para que el frontend en S3 y los navegadores puedan acceder).
5. Haz clic en **Create security group**.

### 3.2 Lanzar la Instancia EC2
1. En el panel de EC2, haz clic en **Launch instances** (Lanzar instancias).
2. Configuración:
   - **Name:** `URL-Shortener-Backend`
   - **AMI:** `Ubuntu Server 24.04 LTS` o `Ubuntu Server 22.04 LTS` (o `Amazon Linux 2023`).
   - **Instance type:** `t2.micro` o `t3.micro` (Apto para capa gratuita).
   - **Key pair:** Selecciona tu par de claves `.pem` existente o crea uno nuevo para conectarte por SSH.
   - **Network settings:** Selecciona el Security Group creado previamente (`url-shortener-sg`).
   - En **Advanced details** (Detalles avanzados):
     - **IAM instance profile:** Selecciona `EC2-URLShortener-Role`.
3. Haz clic en **Launch instance**.
4. Una vez iniciada, copia la **Dirección IP pública IPv4** de la instancia (por ejemplo: `54.210.45.67`).

### 3.3 Configuración del Backend en EC2 (Vía SSH)
Conéctate por SSH a la instancia:
```bash
ssh -i "tu-llave.pem" ubuntu@<IP_PUBLICA_EC2>
```

Actualiza los paquetes e instala Git, Python y venv:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

Clona tu repositorio del proyecto:
```bash
git clone https://github.com/A-Krycek/10.-Midterm---Practical.git aws-url-shortener
cd aws-url-shortener/backend
```

#### Opción A: Despliegue Rápido Automatizado (Recomendado)
Puedes ejecutar el script automatizado que detecta tu IP pública, instala dependencias, crea el `.env` y configura `systemd` en un solo comando:
```bash
bash service/setup-ec2.sh
```

#### Opción B: Configuración Manual Paso a Paso
Crea y activa el entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Crea el archivo `.env`:
```bash
nano .env
```
Pega el siguiente contenido (reemplazando `<IP_PUBLICA_EC2>` con la IP de tu instancia):
```env
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=url_shortener_links
BASE_URL=http://<IP_PUBLICA_EC2>:8000
CORS_ORIGINS=*
```
*Guarda los cambios con `Ctrl + O`, presiona `Enter` y sal con `Ctrl + X`.*

### 3.4 Configuración del Servicio Persistente con systemd (Paso Manual)
Para que el backend siga funcionando al cerrar la sesión SSH o al reiniciar el servidor:

1. Copia el archivo de servicio a systemd:
```bash
sudo cp service/urlshortener.service /etc/systemd/system/
```

2. Si tu usuario es diferente a `ubuntu` o tu ruta difiere, ajusta el archivo con `sudo nano /etc/systemd/system/urlshortener.service`.

3. Recarga systemd e inicia el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable urlshortener
sudo systemctl start urlshortener
```

4. Verifica el estado:
```bash
sudo systemctl status urlshortener
```
*(Debe mostrar estado `active (running)` con color verde).*

5. Comprueba el endpoint de salud desde la terminal:
```bash
curl http://localhost:8000/health
```

---

## 4. Despliegue del Frontend en Amazon S3

### 4.1 Preparar los archivos locales
Antes de subir los archivos, abre `frontend/config.js` y coloca la IP pública de tu EC2:
```javascript
const APP_CONFIG = {
  API_BASE_URL: "http://<IP_PUBLICA_EC2>:8000"
};
```

### 4.2 Crear el Bucket en S3
1. Ve al servicio **S3** en la consola de AWS.
2. Haz clic en **Create bucket** (Crear bucket).
3. Nombre del bucket: Elige un nombre único a nivel global, por ejemplo: `acortador-enlaces-<tu-nombre>-midterm`.
4. Región: La misma que tu DynamoDB (ej. `us-east-1`).
5. En **Block Public Access settings for this bucket**:
   - **Desmarca** la casilla `Block all public access`.
   - Marca la casilla de advertencia que dice `I acknowledge that the current settings might result in this bucket and the objects within becoming public`.
6. Haz clic en **Create bucket**.

### 4.3 Habilitar el Alojamiento Web Estático (Static Website Hosting)
1. Entra al bucket creado.
2. Ve a la pestaña **Properties** (Propiedades).
3. Baja hasta la sección **Static website hosting** (Alojamiento de sitios web estáticos) y haz clic en **Edit** (Editar).
4. Selecciona **Enable** (Habilitar).
5. Hosting type: `Host a static website`.
6. **Index document:** escribe `index.html`.
7. Haz clic en **Save changes** (Guardar cambios).
8. Copia la URL del sitio web generada (ej: `http://acortador-enlaces-midterm.s3-website-us-east-1.amazonaws.com`).

### 4.4 Configurar la Política de Acceso Público al Bucket
1. En el mismo bucket, ve a la pestaña **Permissions** (Permisos).
2. En la sección **Bucket policy** (Política de bucket), haz clic en **Edit**.
3. Pega la siguiente política (reemplaza `NOMBRE_DE_TU_BUCKET` por el nombre de tu bucket):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::NOMBRE_DE_TU_BUCKET/*"
    }
  ]
}
```
4. Haz clic en **Save changes**.

### 4.5 Subir los archivos del Frontend
1. Ve a la pestaña **Objects** (Objetos) de tu bucket.
2. Haz clic en **Upload** (Cargar).
3. Arrastra o selecciona los archivos de la carpeta `frontend/`:
   - `index.html`
   - `styles.css`
   - `app.js`
   - `config.js`
4. Haz clic en **Upload**.

---

## 5. Verificación de Integración de los 3 Servicios

1. Abre en tu navegador la URL de Static Website Hosting de S3:
   `http://<tu-bucket>.s3-website-<region>.amazonaws.com`
2. Verifica que el indicador de estado del Backend EC2 aparezca en color verde (Online).
3. Ingresa una URL original (ejemplo: `https://aws.amazon.com/dynamodb/`).
4. Haz clic en **Acortar URL**:
   - Observa el enlace corto generado con formato `http://<IP_EC2>:8000/<UUID>`.
5. Ve a la consola de DynamoDB > `url_shortener_links` > **Explore items**:
   - Comprueba que el registro se ha creado con su `short_code`, `original_url` y `created_at`.
6. En la interfaz web, haz clic en **Copiar** y abre el enlace corto en una pestaña nueva:
   - Comprueba que el navegador es redirigido automáticamente (código HTTP 307) a la URL de destino original.
7. En la sección de consulta (Endpoint 3), ingresa el UUID y haz clic en **Consultar**:
   - Comprueba que se devuelve el JSON correspondiente.
8. Ingresa un UUID inexistente:
   - Comprueba que se recibe el mensaje `404 Not Found`.
