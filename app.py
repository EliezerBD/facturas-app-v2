from flask import Flask, request, jsonify, send_from_directory, redirect, make_response, send_file
from flask_cors import CORS
import os
from dotenv import load_dotenv
from services.auth_service import AuthService
from services.gmail_service import GmailService

# Cargar variables de entorno desde el archivo config.env
# Esto es crucial para no tener secretos (claves) escritos directamente en el código
load_dotenv('config.env')

# Inicializar la aplicación Flask
# static_folder='static': Indica dónde están los archivos públicos (HTML, CSS, JS)
# static_url_path='': Permite acceder a ellos desde la raíz (ej. /index.html en lugar de /static/index.html)
app = Flask(__name__, static_folder='static', static_url_path='')

# Configuración de CORS (Cross-Origin Resource Sharing)
# Definimos explícitamente qué dominios pueden hablar con nuestro backend.
# Usar "*" con supports_credentials=True es inseguro y bloqueado por navegadores.
allowed_origins = [
    "http://localhost:5000",                   # Desarrollo local
    "http://127.0.0.1:5000",                   # Desarrollo local (IP)
    "https://facturas-app-v2.onrender.com",   # Tu dominio de producción V2
    "https://facturas-app-iujw.onrender.com"   # Nuevo dominio Render
]

CORS(app, resources={
    r"/api/*": {"origins": allowed_origins, "supports_credentials": True},
    r"/auth/*": {"origins": allowed_origins, "supports_credentials": True}
})

# URL del frontend para redirecciones (se usa después del login de Google)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5000')

# --- Rutas Estáticas ---
@app.route('/')
def serve_frontend():
    """
    Ruta principal (Home).
    Sirve el archivo index.html desde la carpeta estática.
    """
    return send_from_directory(app.static_folder, 'index.html')

# --- Rutas de Autenticación ---
@app.route('/auth/google', methods=['GET'])
def google_auth():
    """
    Paso 1 del Login:
    Genera la URL de Google donde el usuario elegirá su cuenta y dará permisos.
    Devuelve esta URL al frontend para que redirija al usuario.
    """
    try:
        auth_service = AuthService()
        auth_url, state = auth_service.get_auth_url()
        return jsonify({'authUrl': auth_url, 'state': state})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/callback', methods=['GET'])
def google_callback():
    """
    Paso 2 del Login (Callback):
    Google redirige aquí después de que el usuario acepta.
    Trae un 'code' que intercambiamos por un 'access_token'.
    """
    try:
        code = request.args.get('code')
        auth_service = AuthService()
        access_token = auth_service.get_token_from_code(code)
        
        # Creamos una respuesta de redirección hacia el frontend
        # Añadimos #auth_success para que el frontend sepa que todo salió bien
        response = make_response(redirect(f"{FRONTEND_URL}/#auth_success"))
        
        # Detectamos si estamos en producción (no localhost)
        is_production = 'localhost' not in FRONTEND_URL and '127.0.0.1' not in FRONTEND_URL
        
        # Guardamos el token en una Cookie Segura
        # httponly=True: JavaScript NO puede leerla (protege contra XSS)
        # secure=is_production: En local es False, en la nube True (HTTPS obligatorio)
        # samesite='Lax': Protege contra ataques CSRF
        response.set_cookie(
            'gmail_token', 
            access_token, 
            httponly=True, 
            secure=is_production, 
            samesite='Lax',
            max_age=3600 # La sesión dura 1 hora (igual que el token de Google)
        )
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """
    Cierra la sesión borrando la cookie del navegador.
    """
    response = make_response(jsonify({'success': True, 'message': 'Sesión cerrada'}))
    # Para borrar una cookie, la sobrescribimos con una fecha de expiración en el pasado (expires=0)
    response.set_cookie('gmail_token', '', expires=0, httponly=True, secure=False, samesite='Lax')
    return response


@app.route('/auth/check-session', methods=['GET'])
def check_session():
    """
    Verifica si el usuario tiene una sesión activa (cookie válida).
    """
    token = request.cookies.get('gmail_token')
    if token:
        try:
            auth_service = AuthService()
            user_info = auth_service.get_user_info(token)
            if user_info and 'email' in user_info:
                return jsonify({
                    'authenticated': True,
                    'email': user_info['email']
                })
        except Exception:
            pass
        return jsonify({'authenticated': True})
    return jsonify({'authenticated': False}), 401

# --- Rutas de API (Gmail) ---
@app.route('/api/search', methods=['POST'])
def search_emails():
   
    """ Busca correos en Gmail.
     Requiere que el usuario tenga la cookie 'gmail_token'. """
  
    try:
        # 1. Obtener token de la cookie
        access_token = request.cookies.get('gmail_token')
        if not access_token:
            return jsonify({'error': 'Sesión no válida'}), 401
            
        # 2. Obtener filtros del cuerpo de la petición (JSON)
        data = request.json
        
        # 3. Usar el servicio de Gmail para buscar
        gmail_service = GmailService(access_token)
        emails = gmail_service.search_emails(
            search_term=data.get('search', '').lower(),
            start_date=data.get('startDate'),
            end_date=data.get('endDate'),
            file_type=data.get('fileType', 'all')
        )
        
        return jsonify({'success': True, 'emails': emails, 'total': len(emails)})
        
    except Exception as e:
        print(f"Error búsqueda: {str(e)}")
        # Detectar si el token expiró para avisar al frontend que debe desloguear
        if 'Token has been expired' in str(e) or 'invalid_grant' in str(e):
            return jsonify({'error': 'Token expirado'}), 401
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-batch', methods=['POST'])
def download_batch():
   
    try:
        access_token = request.cookies.get('gmail_token')
        if not access_token:
            return jsonify({'error': 'Sesión no válida'}), 401
            
        data = request.json
        selected_emails = data.get('emails', [])
        if not selected_emails:
            return jsonify({'error': 'No se seleccionaron emails'}), 400

        # Usar el servicio para generar el ZIP en memoria
        gmail_service = GmailService(access_token)
        zip_buffer = gmail_service.download_attachments_as_zip(selected_emails)
        
        # Enviar el archivo ZIP al navegador
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='facturas_descargadas.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        print(f"Error descarga: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Iniciar el servidor
    # host='0.0.0.0' permite conexiones externas (necesario para Docker/Render)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))