# 🇸🇻 Buscador de Facturas Electrónicas (DTE) - El Salvador

Este proyecto soluciona el caos de recibir **Facturas Electrónicas (DTE)** por correo.
Automatiza la búsqueda y descarga masiva de facturas desde Gmail, facilitando la contabilidad y el cumplimiento con Hacienda.

**Funcionalidades:**
1.  **🔍 Busca** facturas automáticamente en Gmail.
2.  **📅 Filtra** por fechas o tipo de archivo.
3.  **📦 Descarga** todo en un solo ZIP ordenado.

---

## 🚀 Cómo usarlo

### 1. Configuración (Local)
Clona el proyecto y crea un archivo `.env` o `config.env` con tus credenciales:

```env
CLIENT_ID=...
CLIENT_SECRET=...
FRONTEND_URL=http://localhost:5000
REDIRECT_URI=http://localhost:5000/auth/callback
```

### 2. Ejecutar con Docker (Fácil)
```bash
docker-compose up --build
```
Abre `http://localhost:5000`.

### 3. Subir a Producción (Render)
Esta app está lista para **Render**.

1. Crea un **Web Service**.
2. Conecta tu GitHub.
3. **Configuración:**
   - **Runtime:** `Docker`
   - **Root Directory:** `.` (Déjalo en blanco)
4. Agrega tus variables de entorno (`CLIENT_ID`, etc).

---

## 🛠️ Estructura
El proyecto está organizado para ser simple y modular:
- `app.py`: Servidor principal.
- `services/`: Lógica de conexión con Gmail.
- `static/`: Frontend (HTML/JS).
- `Dockerfile`: Configuración de despliegue.
