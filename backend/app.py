from flask import Flask, request, jsonify, send_from_directory, redirect, send_file, make_response
from flask_cors import CORS
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
import os
import zipfile
import io
from dotenv import load_dotenv

load_dotenv('config.env')

app = Flask(__name__)
# Permitir credenciales y todos los orígenes para la API
CORS(app, resources={
    "/api/*": {"origins": "*", "supports_credentials": True},
    "/auth/*": {"origins": "*", "supports_credentials": True}
})

# --- Configuración Google ---
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
# Asegúrate que esta es la URL exacta en tu consola de Google Cloud
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'https://facturas-app-v2-2.onrender.com/auth/callback')
# URL del frontend al que redirigiremos con el token
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://facturas-app-v2-2.onrender.com')

# --- Servir el frontend ---
@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Proteger contra la descarga de archivos sensibles
    if path == 'app.py' or path == 'config.env':
        return jsonify({'error': 'Acceso prohibido'}), 403
    return send_from_directory('.', path)

# --- Páginas requeridas para OAuth ---
@app.route('/privacy')
def privacy():
    return "Política de Privacidad - Esta app respeta tu privacidad y solo accede a los datos necesarios para buscar facturas en Gmail."

@app.route('/terms')
def terms():
    return "Términos de Servicio - Esta app es para uso personal de búsqueda de facturas en Gmail."

# --- Autenticación Google ---
@app.route('/auth/google', methods=['GET'])
def google_auth():
    """Genera URL para autenticar con Google"""
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
        flow.redirect_uri = REDIRECT_URI
        
        auth_url, state = flow.authorization_url(prompt='consent')
        
        return jsonify({'authUrl': auth_url, 'state': state})
    
    except Exception as e:
        print(f"Error en /auth/google: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/auth/callback', methods=['GET'])
def google_callback():
    """Maneja el callback de Google y guarda el token en una Cookie segura"""
    try:
        code = request.args.get('code')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
        flow.redirect_uri = REDIRECT_URI
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        access_token = credentials.token
        
        # ### CAMBIO DE SEGURIDAD ###
        # Redirigir al frontend, sin el token en la URL
        redirect_url = f"{FRONTEND_URL}/#auth_success"
        
        # Crear una respuesta de redirección
        response = make_response(redirect(redirect_url))
        
        # Establecer la cookie segura
        response.set_cookie(
            'gmail_token',            # Nombre de la cookie
            access_token,             # El token real
            httponly=True,            # ¡Importante! El JS no puede leerla.
            secure=True,              # Solo enviar por HTTPS
            samesite='Lax'            # Protección contra CSRF
        )
        return response
        
    except Exception as e:
        print(f"Error en /auth/callback: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """Borra la cookie de sesión del usuario"""
    try:
        response = make_response(jsonify({'success': True, 'message': 'Sesión cerrada'}))
        # Envía una cookie con el mismo nombre, pero vacía y expirada
        response.set_cookie(
            'gmail_token', 
            '', 
            expires=0, 
            httponly=True, 
            secure=True, 
            samesite='Lax'
        )
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Lógica de Búsqueda de Adjuntos (Mejorada) ---

def find_attachments_recursive(service, user_id, msg_id, parts):
    """
    Función recursiva para encontrar todos los adjuntos en un email,
    incluyendo los que están anidados.
    """
    attachments = []
    if not parts:
        return []

    for part in parts:
        if part.get('filename') and part.get('body') and part.get('body').get('attachmentId'):
            filename = part.get('filename')
            # Filtrar solo PDF y XML (o los que necesites)
            if filename.lower().endswith(('.pdf', '.xml', '.json')):
                attachments.append({
                    'filename': filename,
                    'mimeType': part.get('mimeType'),
                    'attachmentId': part['body']['attachmentId']
                })
        
        # Búsqueda recursiva si hay partes anidadas
        if 'parts' in part:
            attachments.extend(find_attachments_recursive(service, user_id, msg_id, part['parts']))
            
    return attachments

# --- API de Búsqueda (Con Fechas y Cookie Segura) ---
@app.route('/api/search', methods=['POST'])
def search_emails():
    """Busca emails REALES en Gmail del usuario"""
    try:
        data = request.json
        search_term = data.get('search', '').lower()
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        
        # ### CAMBIO DE SEGURIDAD ###
        # Leer el token desde la cookie, no desde el JSON
        access_token = request.cookies.get('gmail_token')
        
        if not access_token:
            return jsonify({'error': 'Sesión no válida o expirada'}), 401
        
        keywords = ["factura", "comprobante", "recibo", "pago", "DTE", "documento tributario", "FACT-"]
        
        if search_term:
            query = f"({') OR ('.join(keywords)}) {search_term}"
        else:
            query = f"({' OR '.join(keywords)})"
        
        query += " has:attachment"
        
        if start_date:
            query += f" after:{start_date}"
        if end_date:
            query += f" before:{end_date}"
        
        credentials = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=credentials)
        
        print(f"Buscando en Gmail con query: {query}")
        
        results = service.users().messages().list(
            userId='me', 
            q=query,
            maxResults=20
        ).execute()
        
        messages = results.get('messages', [])
        emails_found = []
        
        for i, msg in enumerate(messages):
            try:
                message = service.users().messages().get(
                    userId='me', 
                    id=msg['id'],
                    format='full' 
                ).execute()
                
                payload = message.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sin asunto')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                parts = payload.get('parts', [])
                attachments = find_attachments_recursive(service, 'me', msg['id'], parts)
                
                if not attachments:
                    continue 
                
                emails_found.append({
                    'id': msg['id'],
                    'subject': subject,
                    'from': sender,
                    'date': date[:16] if date else 'Desconocida',
                    'snippet': message.get('snippet', '')[:100] + '...',
                    'attachments': attachments 
                })
                
            except Exception as e:
                print(f"Error procesando email {msg['id']}: {str(e)}")
                continue
        
        # Devolver 200 OK (implícito) con los datos
        return jsonify({
            'success': True,
            'emails': emails_found,
            'total': len(emails_found)
        })
        
    except Exception as e:
        print(f"Error en búsqueda Gmail: {str(e)}")
        if 'Token has been expired' in str(e) or 'invalid_grant' in str(e):
            return jsonify({'error': 'Token expirado, por favor inicie sesión de nuevo'}), 401
        return jsonify({'error': str(e)}), 500

# --- API de Descarga (Con Cookie Segura) ---
@app.route('/api/download-batch', methods=['POST'])
def download_batch():
    """Descarga los ADJUNTOS REALES en un ZIP"""
    try:
        data = request.json
        selected_emails = data.get('emails', [])
        
        # ### CAMBIO DE SEGURIDAD ###
        # Leer el token desde la cookie
        access_token = request.cookies.get('gmail_token')
        
        if not access_token:
            return jsonify({'error': 'Sesión no válida o expirada'}), 401
        if not selected_emails:
            return jsonify({'error': 'No se seleccionaron emails'}), 400

        credentials = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=credentials)
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            filenames_added = set() 

            for email in selected_emails:
                msg_id = email['id']
                
                for attachment in email.get('attachments', []):
                    try:
                        att_id = attachment['attachmentId']
                        filename = attachment['filename']
                        
                        original_filename = filename
                        counter = 1
                        while filename in filenames_added:
                            base, ext = os.path.splitext(original_filename)
                            filename = f"{base}_{counter}{ext}"
                            counter += 1
                        filenames_added.add(filename)

                        print(f"Descargando: {filename} (de msg {msg_id})")
                        attachment_data_raw = service.users().messages().attachments().get(
                            userId='me', 
                            messageId=msg_id, 
                            id=att_id
                        ).execute()
                        
                        file_data = base64.urlsafe_b64decode(attachment_data_raw['data'].encode('UTF-8'))
                        
                        zip_file.writestr(filename, file_data)
                        
                    except Exception as e:
                        print(f"Error descargando adjunto {attachment.get('filename')}: {str(e)}")
                        zip_file.writestr(f"ERROR_{attachment.get('filename', 'id_'+att_id)}.txt", f"No se pudo descargar este archivo: {str(e)}")

        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='facturas_descargadas.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        print(f"Error en /api/download-batch: {str(e)}")
        if 'Token has been expired' in str(e) or 'invalid_grant' in str(e):
            return jsonify({'error': 'Token expirado, por favor inicie sesión de nuevo'}), 401
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))