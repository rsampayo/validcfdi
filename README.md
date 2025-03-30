# CFDI Verification API

API para verificar la validez de Comprobantes Fiscales Digitales por Internet (CFDI) con el SAT.

## Descripción

Esta API proporciona un servicio REST que permite verificar el estado de CFDIs a través del servicio web del SAT, utilizando autenticación por token.

## Características

- Verificación de CFDIs con el servicio oficial del SAT
- Verificación por lotes de múltiples CFDIs en una sola petición
- Autenticación mediante Bearer token
- Gestión de tokens por superadministradores
- Base de datos local de empresas EFOS (Lista 69-B)
- Verificación automática de RFCs contra lista de EFOS
- Documentación automática con OpenAPI
- Base de datos PostgreSQL (con SQLite como alternativa para desarrollo)
- Fácil despliegue en Heroku

## Requisitos

- Python 3.9+
- PostgreSQL 12+ (opcional para producción)
- SQLite (alternativa para desarrollo)
- Dependencias listadas en `requirements.txt`

## Instalación Local

1. Clonar el repositorio
2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```
3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar base de datos:

   ### Opción A: SQLite (más sencillo para desarrollo)
   ```bash
   # No se requiere configuración adicional, SQLite es el valor predeterminado
   # Solo asegúrese de que la variable USE_SQLITE=true en el archivo .env
   ```

   ### Opción B: PostgreSQL (recomendado para producción)
   - Instalar PostgreSQL si no lo tienes: [Descargar PostgreSQL](https://www.postgresql.org/download/)
   - Puedes utilizar el script asistente para crear la base de datos y usuario:
   ```bash
   python init_postgres.py
   ```
   - O manualmente crear una base de datos: 
   ```sql
   CREATE USER cfdi_user WITH PASSWORD 'secure-password';
   CREATE DATABASE cfdi_api OWNER cfdi_user;
   GRANT ALL PRIVILEGES ON DATABASE cfdi_api TO cfdi_user;
   ```
   - Configurar credenciales en `.env` (ver el siguiente paso)
   - Establecer `USE_SQLITE=false` en el archivo `.env`

5. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env según la base de datos elegida
```
6. Configurar el primer superadmin y token:
```bash
python setup_admin.py
# O para una configuración rápida con valores por defecto:
python init_admin.py
```
7. Ejecutar el servidor:
```bash
uvicorn main:app --reload
```

La API estará disponible en `http://localhost:8000`

## Autenticación

La API utiliza dos métodos de autenticación:

### Bearer Token (para clientes regulares)

Los clientes deben incluir un token de autorización en el encabezado de sus solicitudes:

```
Authorization: Bearer your-api-token
```

### HTTP Basic Auth (para superadministradores)

Los superadministradores utilizan autenticación básica para gestionar tokens:

```
Authorization: Basic base64(username:password)
```

## Gestión de Tokens

Los superadministradores pueden gestionar los tokens de API mediante los siguientes endpoints:

### Crear Token

```bash
curl -X 'POST' \
  'http://localhost:8000/admin/tokens' \
  -H 'accept: application/json' \
  -H 'Authorization: Basic YWRtaW46cGFzc3dvcmQ=' \
  -H 'Content-Type: application/json' \
  -d '{
  "description": "Token para cliente X"
}'
```

### Listar Tokens

```bash
curl -X 'GET' \
  'http://localhost:8000/admin/tokens' \
  -H 'accept: application/json' \
  -H 'Authorization: Basic YWRtaW46cGFzc3dvcmQ='
```

### Regenerar Token

```bash
curl -X 'POST' \
  'http://localhost:8000/admin/tokens/1/regenerate' \
  -H 'accept: application/json' \
  -H 'Authorization: Basic YWRtaW46cGFzc3dvcmQ='
```

## Uso de la API

### Verificar un CFDI

```bash
curl -X 'POST' \
  'https://tu-app.herokuapp.com/verify-cfdi' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer tu-token-secreto' \
  -H 'Content-Type: application/json' \
  -d '{
  "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
  "emisor_rfc": "CDZ050722LA9",
  "receptor_rfc": "XIN06112344A",
  "total": "12000.00"
}'
```

### Verificar Múltiples CFDIs (Procesamiento por Lotes)

```bash
curl -X 'POST' \
  'https://tu-app.herokuapp.com/verify-cfdi-batch' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer tu-token-secreto' \
  -H 'Content-Type: application/json' \
  -d '{
  "cfdis": [
    {
      "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
      "emisor_rfc": "CDZ050722LA9",
      "receptor_rfc": "XIN06112344A",
      "total": "12000.00"
    },
    {
      "uuid": "9876543f-a01b-4ec6-8699-54c5f7e3b111", 
      "emisor_rfc": "ABC123456789",
      "receptor_rfc": "XYZ987654321",
      "total": "5000.00"
    }
  ]
}'
```

Esta funcionalidad permite verificar múltiples CFDIs en una sola petición, lo que reduce la latencia y el número de conexiones necesarias. Las validaciones se procesan en paralelo para optimizar el rendimiento. Cada CFDI incluido en la petición se valida independientemente, y el resultado incluye tanto la información de la solicitud como la respuesta.

### Verificar Estado del Servicio

```bash
curl -X 'GET' \
  'https://tu-app.herokuapp.com/health' \
  -H 'accept: application/json'
```

## Funcionalidad EFOS (Lista 69-B del SAT)

La API incluye funcionalidad para descargar, procesar y consultar la lista oficial de Empresas que Facturan Operaciones Simuladas (EFOS) publicada por el SAT en el Artículo 69-B del Código Fiscal de la Federación.

### Características de la Funcionalidad EFOS

- Descarga automática de la lista oficial del SAT
- Limpieza y procesamiento del archivo CSV
- Almacenamiento de datos en base de datos local
- Actualización programada y automática
- Verificación de RFCs contra la lista de EFOS
- Integración con la verificación de CFDI para alertar sobre emisores o receptores en la lista EFOS

### Verificar un RFC contra la Lista EFOS

```bash
curl -X 'POST' \
  'https://tu-app.herokuapp.com/check-rfc-efos' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer tu-token-secreto' \
  -H 'Content-Type: application/json' \
  -d '{
  "rfc": "RFC123456ABC"
}'
```

### Verificar Múltiples RFCs contra la Lista EFOS (Procesamiento por Lotes)

```bash
curl -X 'POST' \
  'https://tu-app.herokuapp.com/check-rfc-efos-batch' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer tu-token-secreto' \
  -H 'Content-Type: application/json' \
  -d '{
  "rfcs": ["RFC123456ABC", "XYZ987654321", "AAA080808HL8"]
}'
```

Esta funcionalidad permite verificar múltiples RFCs en una sola petición, lo que reduce la latencia y el número de conexiones necesarias. Cada RFC se verifica independientemente, y el resultado incluye información sobre si el RFC está en la lista EFOS y sus detalles si es el caso.

### Actualizar Manualmente la Base de Datos EFOS

Este endpoint está protegido y solo puede ser accedido por superadministradores:

```bash
curl -X 'POST' \
  'https://tu-app.herokuapp.com/update-efos-database' \
  -H 'accept: application/json' \
  -H 'Authorization: Basic YWRtaW46cGFzc3dvcmQ=' \
  -H 'Content-Type: application/json' \
  -d '{
  "run_in_background": true
}'
```

### Programar Actualizaciones Automáticas

Para mantener la base de datos EFOS actualizada, puedes ejecutar el programador en segundo plano:

```bash
python efos_scheduler.py
```

Esto ejecutará un proceso que actualizará la base de datos EFOS según la configuración especificada en el archivo `.env`.

### Configuración EFOS

En el archivo `.env`, puedes configurar las siguientes opciones:

```
# EFOS Settings
EFOS_CSV_URL=http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv
EFOS_UPDATE_INTERVAL_DAYS=1
EFOS_UPDATE_TIME=03:00
```

- `EFOS_CSV_URL`: URL del archivo CSV oficial del SAT
- `EFOS_UPDATE_INTERVAL_DAYS`: Frecuencia de actualización en días
- `EFOS_UPDATE_TIME`: Hora del día para realizar la actualización (formato 24h)

## Despliegue en Heroku

1. Crear una cuenta en Heroku (si no la tienes)
2. Instalar [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
3. Iniciar sesión en Heroku:
```bash
heroku login
```
4. Crear una nueva aplicación:
```bash
heroku create nombre-de-tu-app
```
5. Provisionar una base de datos PostgreSQL:
```bash
heroku addons:create heroku-postgresql:mini
```
6. Configurar variables de entorno:
```bash
heroku config:set SECRET_KEY=tu-clave-secreta
# Asegurarse de usar PostgreSQL en producción
heroku config:set USE_SQLITE=false
# Para crear un superadmin inicial
heroku config:set SUPERADMIN_USERNAME=admin
heroku config:set SUPERADMIN_PASSWORD=password-seguro
# Configuración EFOS
heroku config:set EFOS_UPDATE_INTERVAL_DAYS=1
heroku config:set EFOS_UPDATE_TIME=03:00
```
7. Desplegar la aplicación:
```bash
git push heroku main
```
8. Crear el superadmin inicial:
```bash
heroku run python init_admin.py
```
9. Iniciar una actualización inicial de la base de datos EFOS:
```bash
heroku run python -c "from database import SessionLocal; import efos_manager; efos_manager.update_efos_database(SessionLocal())"
```
10. Configurar el programador para actualizaciones automáticas (requiere un dyno worker):
```bash
heroku ps:scale worker=1
```

## Documentación API

La documentación OpenAPI está disponible en `/docs` o `/redoc` una vez que el servidor está corriendo.

## Seguridad

En producción, asegúrate de:

1. Usar HTTPS
2. Configurar claves seguras como variables de entorno
3. Cambiar las credenciales de administrador por defecto
4. Limitar el acceso a los endpoints de administración a IPs específicas
5. Utilizar contraseñas fuertes para PostgreSQL 