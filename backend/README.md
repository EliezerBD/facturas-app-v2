# 📧 Descargador de Facturas de Gmail

Aplicación Flask para buscar y descargar automáticamente facturas desde Gmail.

## 🚀 Configuración Inicial

### 1. Instalar Dependencias
```bash
py -m pip install -r requirements.txt
```

### 2. Obtener Credenciales de Google OAuth

Para que la aplicación pueda acceder a Gmail, necesitas crear credenciales OAuth:

#### Paso a paso:
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Activa la API de Gmail:
   - Ve a "APIs y servicios" → "Biblioteca"
   - Busca "Gmail API" y actívala
4. Crea credenciales OAuth 2.0:
   - Ve a "APIs y servicios" → "Credenciales"
   - Click en "Crear credenciales" → "ID de cliente de OAuth"
   - Tipo de aplicación: "Aplicación web"
   - URI de redireccionamiento autorizado: `http://localhost:5000/auth/callback`
   - Copia el **Client ID** y **Client Secret**

#### Configurar el archivo `config.env`:
```env
CLIENT_ID=tu_client_id_aqui.apps.googleusercontent.com
CLIENT_SECRET=tu_client_secret_aqui
```

### 3A. Ejecutar en Modo Local (Sin Docker)

Para desarrollo local, actualiza las URLs en `app.py` y `auth_service.py`:

**En `app.py` (líneas 20-23):**
```python
allowed_origins = [
    "http://localhost:5000",
    "http://127.0.0.1:5000"
]
```

**En `app.py` (línea 32):**
```python
FRONTEND_URL = 'http://localhost:5000'
```

**En `services/auth_service.py` (línea 12):**
```python
self.redirect_uri = 'http://localhost:5000/auth/callback'
```

### 4A. Iniciar el Servidor (Sin Docker)
```bash
py app.py
```

Abre tu navegador en: http://localhost:5000

---

## 🐳 Opción 2: Ejecutar con Docker (RECOMENDADO)

### 3B. Asegurar que tienes Docker instalado
```bash
docker --version
docker-compose --version
```

Si no tienes Docker, descárgalo de: https://www.docker.com/products/docker-desktop

### 4B. Construir y ejecutar con Docker Compose

```bash
# Construir la imagen y levantar el contenedor
docker-compose up --build
```

La aplicación estará disponible en: http://localhost:5000

**Comandos útiles:**
```bash
# Ejecutar en segundo plano (detached mode)
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Detener los contenedores
docker-compose down

# Reconstruir la imagen si cambias dependencias
docker-compose up --build

# Entrar al contenedor (para debugging)
docker exec -it facturas-gmail-app bash
```

### Ventajas de usar Docker:
✅ **Entorno aislado** - No contaminas tu sistema con dependencias  
✅ **Portabilidad** - Funciona igual en cualquier máquina  
✅ **Hot reload** - Los cambios en el código se reflejan automáticamente  
✅ **Fácil limpieza** - `docker-compose down` elimina todo

---

## 📁 Estructura del Proyecto

```
backend/
├── app.py              # Servidor Flask principal
├── config.env          # Credenciales (NO subir a Git)
├── requirements.txt    # Dependencias Python
├── services/
│   ├── auth_service.py    # Manejo de OAuth2
│   └── gmail_service.py   # Interacción con Gmail API
└── static/
    ├── index.html         # Frontend
    ├── appwed.js         # Lógica del cliente
    └── style.css         # Estilos
```

## 🔒 Seguridad

- ⚠️ **NUNCA** subas `config.env` a GitHub
- Las credenciales se guardan en cookies HTTPOnly para protegerlas de XSS
- Solo se pide permiso de lectura (`gmail.readonly`)

## 🛠️ Funcionalidades

✅ Autenticación con Google OAuth  
✅ Búsqueda automática de facturas por palabras clave  
✅ Filtros por fecha y tipo de archivo  
✅ Descarga masiva en formato ZIP  
✅ Interfaz moderna con Tailwind CSS

## 🐛 Troubleshooting

**Error: "Sesión no válida"**
- Verifica que `config.env` tenga las credenciales correctas
- Revisa que la URL de redirección coincida en Google Cloud y en el código

**Error: "Token expirado"**
- Cierra sesión y vuelve a autenticarte

**No encuentra facturas**
- Verifica que los correos tengan adjuntos PDF/XML/JSON
- Ajusta las palabras clave en `gmail_service.py` línea 25
