# 📧 Facturas App V2 - Descarga Masiva de Facturas de Gmail

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![Estado](https://img.shields.io/badge/Estado-Activo-success.svg)](https://facturas-app-v2.onrender.com/)

**Herramienta web gratuita para descargar facturas electrónicas de Gmail de forma automática y masiva.**

Ideal para contadores, empresas y profesionales en El Salvador 🇸🇻 que necesitan gestionar facturas electrónicas (DTE) de forma eficiente.

## 🌐 Demo en Vivo

**[🚀 Prueba la aplicación aquí](https://facturas-app-v2.onrender.com/)**

> ⏳ **Nota:** Como el servidor está en el plan gratuito de Render, la primera vez puede tardar ~50 segundos en cargar mientras se "despierta". ¡Vale la pena la espera!

---

## ✨ Características Principales

### 🔍 Búsqueda Inteligente
- **Escaneo automático** de correos en Gmail con facturas electrónicas
- **Filtros por fecha** para búsquedas precisas (rango personalizable)
- **Filtros por tipo** de archivo (PDF, JSON, DTE)
- Búsqueda por palabras clave en asuntos y remitentes

### 📥 Descarga Masiva
- **Descarga en lote** de múltiples facturas simultáneamente
- **Archivo ZIP automático** con todos los documentos seleccionados
- Conserva nombres originales de archivos
- Sin límites de descarga

### 🔒 Seguridad y Privacidad
- **OAuth 2.0 de Google** para autenticación segura
- **Sin almacenamiento** de credenciales
- Cookies HTTPOnly y Secure
- Cumple con políticas de privacidad de Google
- [Ver Política de Privacidad](https://facturas-app-v2.onrender.com/privacidad.html)

### 💼 Casos de Uso
- ✅ Contadores que gestionan facturas de múltiples clientes
- ✅ Empresas que necesitan consolidar facturas mensuales
- ✅ Profesionales que deben archivar comprobantes fiscales
- ✅ Declaraciones de IVA y renta en El Salvador

---

## 🛠️ Tecnologías

| Categoría | Tecnología |
|-----------|-----------|
| **Backend** | Python 3.9+, Flask 2.0+ |
| **API** | Gmail API (Google OAuth 2.0) |
| **Frontend** | HTML5, JavaScript ES6+, TailwindCSS |
| **Despliegue** | Docker, Render.com |
| **Seguridad** | HTTPOnly Cookies, CORS, dotenv |

---

## 🚀 Instalación Local

### Requisitos Previos
- Python 3.9 o superior
- Cuenta de Google Cloud con Gmail API habilitado
- Git

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/EliezerBD/facturas-app-v2.git
cd facturas-app-v2
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno**
```bash
# Copiar archivo de ejemplo
cp config.env.example config.env

# Editar config.env con tus credenciales de Google Cloud
```

4. **Ejecutar la aplicación**
```bash
python app.py
```

5. **Abrir en navegador**
```
http://localhost:5000
```

---

## � Configuración de Google Cloud

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear un nuevo proyecto
3. Habilitar Gmail API
4. Crear credenciales OAuth 2.0
5. Agregar URIs de redirección autorizados:
   - `http://localhost:5000/auth/callback` (desarrollo)
   - `https://tu-dominio.com/auth/callback` (producción)
6. Descargar credenciales y copiar Client ID y Client Secret al `config.env`

---

## 🐳 Despliegue con Docker

```bash
# Construir imagen
docker build -t facturas-app-v2 .

# Ejecutar contenedor
docker run -p 5000:5000 --env-file config.env facturas-app-v2
```

---

## 📖 Cómo Usar

1. **Iniciar sesión con Google** - Haz clic en "Iniciar sesión con Google"
2. **Autorizar acceso** - Permite acceso de solo lectura a Gmail
3. **Buscar facturas** - Usa filtros de fecha y palabras clave
4. **Seleccionar archivos** - Marca las facturas que deseas descargar
5. **Descargar** - Obtén un archivo ZIP con todas tus facturas

---

## 🌎 SEO y Visibilidad

Esta aplicación está optimizada para:
- **Búsquedas locales**: "descargar facturas gmail el salvador"
- **Keywords técnicos**: "descarga masiva DTE", "facturas electrónicas automáticas"
- **Open Graph** para compartir en redes sociales
- **Datos estructurados** Schema.org
- **Sitemap XML** para mejor indexación

---

##  Contribuciones

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add: nueva característica'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

##  Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## 👨 Autor

**Eliezer Beltrán**
- GitHub: [@EliezerBD](https://github.com/EliezerBD)
- Email: beltraneliezer133@gmail.com

---

##  Agradecimientos

- Google Gmail API por su excelente documentación
- Comunidad de Flask por el framework
- Todos los contribuidores y usuarios

---

##  Keywords SEO

`facturas gmail` · `descarga masiva facturas` · `facturas electrónicas` · `DTE El Salvador` · `Gmail API` · `descargar PDF gmail` · `automatizar facturas` · `buscador de facturas` · `facturas automáticas` · `gestión de facturas`

---

** Si te sirvió este proyecto, no olvides darle una estrella en GitHub! **

