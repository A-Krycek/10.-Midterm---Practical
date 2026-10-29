# Guion y Lista de Verificación para el Video de Demostración

Este documento es una guía estructurada para grabar el video explicativo de la entrega. Asegura cubrir todos los criterios de evaluación del Midterm para obtener la máxima calificación (8/8 puntos).

Duración recomendada del video: **5 a 8 minutos**.

---

## Estructura y Guion Minuto a Minuto

### 1. Introducción y Repositorio (0:00 - 1:00)
- **Qué mostrar en pantalla:**
  - Repositorio en GitHub o GitLab abierto en el navegador.
  - El proyecto en VS Code mostrando la organización modular de carpetas (`backend/`, `frontend/`, `docs/`).
- **Qué decir (Puntos clave):**
  - "Buenas, en este video presento el desarrollo y despliegue del acortador de enlaces cloud utilizando la arquitectura integrada de AWS: Amazon S3 para el frontend estático, Amazon EC2 ejecutando FastAPI con Uvicorn, y Amazon DynamoDB para la persistencia NoSQL de los enlaces."
  - "El proyecto está organizado de manera modular: el backend separa la capa de configuración, modelos con Pydantic, conexión a DynamoDB con Boto3 y las rutas de la API, mientras que el frontend está desarrollado en HTML, CSS y JavaScript puro."

---

### 2. Demostración de Servicios en la Consola de AWS (1:00 - 2:30)
- **Qué mostrar en pantalla:**
  1. **Amazon DynamoDB:**
     - Mostrar la tabla `url_shortener_links`.
     - Señalar que la Partition Key es `short_code` (String).
     - Mostrar la pestaña *Explore table items* para indicar que actualmente está lista para recibir registros.
  2. **Rol IAM (Mínimo Privilegio):**
     - Mostrar el rol `EC2-URLShortener-Role` y su política asociada con permisos exclusivos `dynamodb:PutItem` y `dynamodb:GetItem` sobre la tabla.
     - Destacar: *"No hay credenciales ni llaves de acceso estáticas (Access Keys) en el código; Boto3 adquiere credenciales temporales a través del Instance Profile de EC2"*.
  3. **Amazon EC2:**
     - Mostrar la instancia en ejecución con su IP pública.
     - Mostrar el **Security Group**: puerto 22 (SSH) y puerto 8000 abierto para permitir las peticiones del frontend y las redirecciones de los usuarios.
     - Abrir la terminal SSH y ejecutar:
       ```bash
       sudo systemctl status urlshortener
       ```
       Destacar: *"El backend se ejecuta como un servicio daemon gestionado por systemd, lo que garantiza persistencia y reinicio automático"*.
  4. **Amazon S3:**
     - Mostrar el bucket S3 con los archivos subidos (`index.html`, `styles.css`, `app.js`, `config.js`).
     - Mostrar la configuración de *Static Website Hosting* activa con su URL pública.

---

### 3. Pruebas Funcionales Integradas (2:30 - 5:30)

#### Prueba A: Acortar un enlace y persistencia en DynamoDB (POST /shorten)
1. Abrir la página web desde la URL de S3 en el navegador.
2. Mostrar que el indicador de estado señala conexión exitosa con la API de EC2.
3. Ingresar una URL original de prueba (por ejemplo: `https://www.google.com` o `https://aws.amazon.com/dynamodb/`).
4. Hacer clic en **Acortar URL**.
5. Explicar el resultado:
   - Se generó dinámicamente un UUID como `short_code`.
   - Se muestra el enlace corto generado: `http://<IP_EC2>:8000/<UUID>`.
6. Cambiar a la consola de AWS DynamoDB y refrescar la tabla:
   - Señalar el nuevo ítem creado con los tres atributos: `short_code`, `original_url` y `created_at`.

#### Prueba B: Redirección HTTP 307 (GET /{short_code})
1. En la web de S3, hacer clic en el botón **Copiar** (notar el feedback visual *"¡Copiado!"*).
2. Abrir una nueva pestaña en el navegador y pegar el enlace corto.
3. Presionar Enter y mostrar la barra de direcciones:
   - El navegador navega y redirige automáticamente hacia la URL de destino original.
   - En la consola del desarrollador (F12 > Red/Network) o en los logs de EC2 con `journalctl`, mostrar que el código de respuesta fue `307 Temporary Redirect`.

#### Prueba C: Consultar información del enlace (GET /urls/{short_code})
1. En la sección "Consultar Información" de la web, pegar el UUID generado y pulsar **Consultar**.
2. Mostrar que el backend devuelve el JSON con `short_code`, `original_url` y `created_at`.
3. También puedes abrir directamente en el navegador la URL `http://<IP_EC2>:8000/urls/<UUID>` para mostrar la respuesta JSON directa de la API.

#### Prueba D: Comprobación de Enlace Inexistente (HTTP 404 Not Found)
1. En el formulario de consulta o directamente en la barra del navegador, ingresar un UUID que no exista (por ejemplo: `http://<IP_EC2>:8000/00000000-0000-0000-0000-000000000000`).
2. Mostrar que el backend devuelve un código `404 Not Found` con el mensaje de error correspondiente.

#### Prueba E: Validación de URL y errores
1. En el formulario de acortamiento, ingresar un texto inválido (como `no-es-una-url`).
2. Intentar enviarlo y mostrar el mensaje de validación amigable al usuario.

#### Prueba F: Persistencia tras reinicio
1. En la terminal de EC2, reiniciar el servicio:
   ```bash
   sudo systemctl restart urlshortener
   ```
2. Volver a abrir uno de los enlaces cortos previamente generados y demostrar que sigue funcionando de manera continua sin pérdida de datos.

---

### 4. Conclusión (5:30 - 6:00)
- Recapitular:
  - Frontend servido globalmente desde Amazon S3.
  - Backend REST en Amazon EC2 orquestado con FastAPI y systemd.
  - Persistencia segura y escalable en Amazon DynamoDB sin credenciales duras gracias al rol IAM.
- Despedida formal.
