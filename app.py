# Importación de librerías necesarias de Flask y Python
from flask import Flask, request, jsonify, send_from_directory, redirect, make_response, send_file
from flask_cors import CORS
import os
from dotenv import load_dotenv
from services.auth_service import AuthService
from services.gmail_service import GmailService
from services.supabase_service import SupabaseService

# Cargar variables de entorno desde el archivo config.env para manejar secretos de forma segura
load_dotenv('config.env')

# Inicializar la aplicación Flask configurando la carpeta de archivos estáticos
app = Flask(__name__, static_folder='static', static_url_path='')

# Configuración de CORS para permitir peticiones desde dominios específicos
allowed_origins = [
    "http://localhost:5000",                   # Entorno de desarrollo local
    "http://127.0.0.1:5000",                   # Entorno de desarrollo local (alternativo)
    "https://facturas-app-v2.onrender.com",   # Dominio de producción principal
    "https://facturas-app-iujw.onrender.com"   # Dominio de producción secundario en Render
]

# Aplicar la configuración de CORS a las rutas de API y autenticación
CORS(app, resources={
    r"/api/*": {"origins": allowed_origins, "supports_credentials": True},
    r"/auth/*": {"origins": allowed_origins, "supports_credentials": True}
})

# Definir la URL del frontend para redirecciones, priorizando la variable de entorno
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5000')

# Ruta para servir la página principal del frontend
@app.route('/')
def serve_frontend():
    # Envía el archivo index.html ubicado en la carpeta static
    return send_from_directory(app.static_folder, 'index.html')

# Ruta para iniciar el proceso de autenticación con Google
@app.route('/auth/google', methods=['GET'])
def google_auth():
    try:
        # Instanciar el servicio de autenticación
        auth_service = AuthService()
        # Obtener la URL de autorización y el estado único
        auth_url, state = auth_service.get_auth_url()
        # Retornar la URL al frontend para la redirección
        return jsonify({'authUrl': auth_url, 'state': state})
    except Exception as e:
        # En caso de error, retornar el mensaje y código 500
        return jsonify({'error': str(e)}), 500

# Ruta de retorno (callback) después de que el usuario se autentica en Google
@app.route('/auth/callback', methods=['GET'])
def google_callback():
    try:
        # Obtener el código de autorización enviado por Google
        code = request.args.get('code')
        auth_service = AuthService()
        # Intercambiar el código por un token de acceso
        access_token = auth_service.get_token_from_code(code)
        
        # Crear una respuesta que redirige al usuario al frontend con un hash de éxito
        response = make_response(redirect(f"{FRONTEND_URL}/#auth_success"))
        
        # Verificar si la aplicación se está ejecutando en producción para configurar la seguridad de la cookie
        is_production = 'localhost' not in FRONTEND_URL and '127.0.0.1' not in FRONTEND_URL
        
        # Guardar el token de acceso en una cookie segura del navegador
        response.set_cookie(
            'gmail_token', 
            access_token, 
            httponly=True,            # Previene acceso desde scripts de JavaScript
            secure=is_production,     # Solo se envía por HTTPS en producción
            samesite='Lax',           # Protección básica contra CSRF
            max_age=3600              # Duración de 1 hora
        )
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ruta para cerrar la sesión del usuario
@app.route('/auth/logout', methods=['POST'])
def logout():
    # Crear respuesta de confirmación de cierre de sesión
    response = make_response(jsonify({'success': True, 'message': 'Sesión cerrada'}))
    # Eliminar la cookie gmail_token configurando su expiración en el pasado
    response.set_cookie('gmail_token', '', expires=0, httponly=True, secure=False, samesite='Lax')
    return response

# Ruta para verificar si hay una sesión activa y obtener info del usuario
@app.route('/auth/check-session', methods=['GET'])
def check_session():
    # Obtener el token de la cookie
    token = request.cookies.get('gmail_token')
    if token:
        try:
            auth_service = AuthService()
            # Obtener información del perfil del usuario usando el token
            user_info = auth_service.get_user_info(token)
            if user_info and 'email' in user_info:
                return jsonify({
                    'authenticated': True,
                    'email': user_info['email']
                })
        except Exception:
            pass
        # Si el token existe pero no se pudo obtener el email, se considera autenticado
        return jsonify({'authenticated': True})
    # Si no hay token, el usuario no está autenticado
    return jsonify({'authenticated': False}), 401

# Ruta para buscar correos electrónicos que contengan facturas
@app.route('/api/search', methods=['POST'])
def search_emails():
    try:
        # Obtener el token de acceso de las cookies
        access_token = request.cookies.get('gmail_token')
        if not access_token:
            return jsonify({'error': 'Sesión no válida'}), 401
            
        # Obtener los datos de búsqueda enviados en el cuerpo JSON
        data = request.json
        
        # Inicializar el servicio de Gmail con el token del usuario
        gmail_service = GmailService(access_token)
        # Realizar la búsqueda con los parámetros proporcionados
        emails = gmail_service.search_emails(
            search_term=data.get('search', '').lower(),
            start_date=data.get('startDate'),
            end_date=data.get('endDate'),
            file_type=data.get('fileType', 'all')
        )
        
        # --- NUEVO: MARCAR SI YA FUERON DESCARGADOS ---
        supabase_service = SupabaseService()
        auth_service = AuthService()
        user_info = auth_service.get_user_info(access_token)
        user_email = user_info.get('email', 'anónimo')
        
        user_history = supabase_service.get_user_history(user_email)
        # Crear un set de IDs de mensajes ya descargados por este usuario
        downloaded_ids = {h['gmail_message_id'] for h in user_history if h.get('gmail_message_id')}

        for email in emails:
            email['downloaded'] = email['id'] in downloaded_ids

        # Retornar la lista de correos encontrados
        return jsonify({'success': True, 'emails': emails, 'total': len(emails)})
        
    except Exception as e:
        print(f"Error búsqueda: {str(e)}")
        # Manejar específicamente el caso de token expirado
        if 'Token has been expired' in str(e) or 'invalid_grant' in str(e):
            return jsonify({'error': 'Token expirado'}), 401
        return jsonify({'error': str(e)}), 500

# Ruta para descargar múltiples adjuntos en un archivo comprimido ZIP
@app.route('/api/download-batch', methods=['POST'])
def download_batch():
    try:
        # Obtener el token de acceso de las cookies
        access_token = request.cookies.get('gmail_token')
        if not access_token:
            return jsonify({'error': 'Sesión no válida'}), 401
            
        # Obtener la lista de correos seleccionados
        data = request.json
        selected_emails = data.get('emails', [])
        if not selected_emails:
            return jsonify({'error': 'No se seleccionaron emails'}), 400

        # Inicializar el servicio de Gmail
        gmail_service = GmailService(access_token)
        # Generar el archivo ZIP y extraer metadatos de los JSON de DTE
        zip_buffer, dte_metadata = gmail_service.download_attachments_as_zip(selected_emails)
        
        # Enviar el archivo ZIP generado al usuario
        response = send_file(
            zip_buffer,
            as_attachment=True,
            download_name='facturas_descargadas.zip',
            mimetype='application/zip'
        )
        
        # --- NUEVO: ENVIAR METADATOS DTE EN LOS HEADERS ---
        # Convertimos la lista de metadatos a JSON para que el frontend pueda leerla
        import json
        response.headers['X-DTE-Metadata'] = json.dumps(dte_metadata)
        # Exponemos el header para que JavaScript pueda acceder a él (CORS)
        response.headers['Access-Control-Expose-Headers'] = 'X-DTE-Metadata'
        # --- NUEVO: GUARDAR EN SUPABASE DESDE EL BACKEND ---
        try:
            # Obtener el email del usuario para el registro
            auth_service = AuthService()
            user_info = auth_service.get_user_info(access_token)
            user_email = user_info.get('email', 'anónimo')

            # Preparar los datos para el historial
            supabase_service = SupabaseService()
            history_rows = []
            
            # Crear un mapa para buscar metadatos por nombre de archivo
            dte_map = {m['filename']: m for m in dte_metadata}

            for email in selected_emails:
                for att in email.get('attachments', []):
                    # Solo registrar archivos PDF, XML o JSON
                    filename = att.get('filename', '')
                    if not filename.lower().endswith(('.pdf', '.xml', '.json')):
                        continue
                        
                    dte = dte_map.get(filename, {})
                    history_rows.append({
                        "usuario_email": user_email,
                        "asunto_correo": email.get('subject', 'Sin asunto'),
                        "nombre_archivo": filename,
                        "emisor": email.get('from', 'Desconocido'),
                        "codigo_generacion": dte.get('codigo_generacion'),
                        "numero_control": dte.get('numero_control'),
                        "monto_total": dte.get('monto_total'),
                        "receptor_nombre": dte.get('receptor_nombre'),
                        "gmail_message_id": email.get('id')
                    })

            if history_rows:
                supabase_service.save_history(history_rows)
        except Exception as se:
            print(f"Error al registrar historial en backend: {str(se)}")

        return response
        
    except Exception as e:
        print(f"Error descarga: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Punto de entrada principal para ejecutar la aplicación
if __name__ == '__main__':
    # Ejecutar la aplicación en el puerto configurado por el entorno o el 5000 por defecto
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
