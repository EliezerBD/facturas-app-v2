# 📧 Buscador de Facturas de Gmail

Simple herramienta web para encontrar facturas en tu Gmail y descargarlas todas juntas en un ZIP.

**¿Para qué sirve?**
Te ahorra el trabajo de buscar correo por correo. Pones filtros (fecha, palabras clave) y la app te da un ZIP con todos los PDFs/XMLs que encuentre.

---

## 🚀 Cómo usarlo (Localmente en tu PC)

### Requisitos
- Tener instalada una versión de Python reciente
- Tener una cuenta de **Google Cloud** configurada (ver abajo "Configurar Google")

### 1. Descargar y Configurar
Clona este repo y crea un archivo llamado `.env` (o `config.env`) dentro de la carpeta `backend/` con tus datos:

```env
CLIENT_ID=tu_cliente_id_de_google.apps.googleusercontent.com
CLIENT_SECRET=tu_secreto_de_cliente
FRONTEND_URL=http://localhost:5000
REDIRECT_URI=http://localhost:5000/auth/callback
APP_PASSWORD=tu_contraseña_si_usas_login_simple
```

### 2. Ejecutar (Opción fácil: Docker)
Si tienes Docker Desktop instalado, es lo mejor. Solo corre:

```bash
docker-compose up --build
```
Y abre `http://localhost:5000`.

### 3. Ejecutar (Opción manual: Python)
Si no usas Docker:

```bash
cd backend
pip install -r requirements.txt
python app.py
```

---

## ☁️ Cómo subirlo a Render (Gratis)

Esta app está optimizada para Docker en Render. Sigue estos pasos exactos:

1. Crea una cuenta en [Render.com](https://render.com).
2. Crea un **New Web Service**.
3. Conecta este repositorio de GitHub.
4. **Configuración CLAVE:**
   - **Runtime:** `Docker` (¡Importante! No elijas Python)
   - **Root Directory:** `backend`
5. **Variables de Entorno (Environment):**
   Agrega las mismas variables de tu `.env` pero adaptadas a la nube:
   - `FRONTEND_URL`: `https://tu-app.onrender.com`
   - `REDIRECT_URI`: `https://tu-app.onrender.com/auth/callback`
   - `CLIENT_ID` y `CLIENT_SECRET` (Mismos de Google)

---

## � Configurar Google (El paso "aburrido" pero necesario)

Para que Google te deje entrar a tu correo, debes configurar su consola:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Crea credenciales **OAuth 2.0 Web Client**.
3. Agrega en **Orígenes autorizados**:
   - `http://localhost:5000` (Local)
   - `https://tu-app.onrender.com` (Producción)
4. Agrega en **URIs de redirección**:
   - `http://localhost:5000/auth/callback`
   - `https://tu-app.onrender.com/auth/callback`

---

## �️ Tecnologías
- **Backend:** Flask (Python) con estructura modular.
- **Frontend:** HTML5 + Vanilla JS + TailwindCSS (Rápido y bonito).
- **Seguridad:** Cookies HttpOnly, y verificación de sesion segura.
- **Servidor:** Gunicorn (listo para producción).
