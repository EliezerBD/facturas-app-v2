from flask import Flask, request, jsonify, send_from_directory, redirect, send_file
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
CORS(app)

# Configuración Google
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'https://facturas-app-v2-2.onrender.com/auth/callback')

# Almacenar tokens (en memoria, para desarrollo)
user_tokens = {}

# Servir el frontend
@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# Páginas requeridas para OAuth
@app.route('/privacy')
def privacy():
    return "Política de Privacidad - Esta app respeta tu privacidad y solo accede a los datos necesarios para buscar facturas en Gmail."

@app.route('/terms')
def terms():
    return "Términos de Servicio - Esta app es para uso personal de búsqueda de facturas en Gmail."

# Rutas adicionales de callback para compatibilidad
@app.route('/auth/google/callback')
def google_callback_alias1():
    return google_callback()

@app.route('/api/auth/callback/google')
def google_callback_alias2():
    return google_callback()

@app.route('/callback')
def google_callback_alias3():
    return google_callback()

# Autenticación Google
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
        user_tokens[state] = None
        
        return jsonify({'authUrl': auth_url, 'state': state})  # ⬅️ IMPORTANTE: Devolver state
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/callback', methods=['GET'])
def google_callback():
    """Maneja el callback de Google"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
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
        
        # Guardar token CON EL STATE CORRECTO
        user_tokens[state] = credentials.token
        
        return redirect('https://facturas-app-v2-2.onrender.com/#auth_success')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# BÚSQUEDA REAL EN GMAIL - VERSIÓN SEGURA
@app.route('/api/search', methods=['POST'])
def search_emails():
    """Busca emails REALES en Gmail del usuario actual"""
    try:
        data = request.json
        search_term = data.get('search', '').lower()
        file_type = data.get('fileType', 'all')
        user_state = data.get('state')  # ⬅️ IDENTIFICAR USUARIO
        
        # Palabras clave para buscar facturas
        keywords = ["factura", "comprobante", "recibo", "pago", "DTE", "documento tributario", "FACT-"]
        
        # Construir query de búsqueda
        if search_term:
            query = f"({') OR ('.join(keywords)}) {search_term}"
        else:
            query = f"({' OR '.join(keywords)})"
        
        # ⬅️ SEGURO: Verificar usuario específico
        if not user_state or user_state not in user_tokens:
            return jsonify({'error': 'Usuario no autenticado'}), 401
            
        access_token = user_tokens[user_state]
        if not access_token:
            return jsonify({'error': 'Token de acceso no disponible'}), 401
        
        # Crear servicio de Gmail con el token DEL USUARIO CORRECTO
        credentials = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=credentials)
        
        # Buscar emails en Gmail
        print(f"Buscando en Gmail con query: {query}")
        results = service.users().messages().list(
            userId='me', 
            q=query,
            maxResults=20
        ).execute()
        
        messages = results.get('messages', [])
        emails_found = []
        
        # Procesar cada email encontrado
        for i, msg in enumerate(messages):
            try:
                message = service.users().messages().get(
                    userId='me', 
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                # Extraer metadatos
                headers = message.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sin asunto')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Verificar si tiene adjuntos
                has_attachments = any(
                    part.get('filename') for part in 
                    message.get('payload', {}).get('parts', [])
                )
                
                # Determinar tipo de archivo (simplificado)
                email_type = 'pdf' if '.pdf' in subject.lower() else 'json' if '.json' in subject.lower() else 'other'
                
                emails_found.append({
                    'id': msg['id'],
                    'subject': subject,
                    'from': sender,
                    'date': date[:10] if date else 'Desconocida',
                    'has_attachments': has_attachments,
                    'type': email_type,
                    'snippet': message.get('snippet', '')[:100] + '...'
                })
                
                print(f"Email {i+1}: {subject}")
                
            except Exception as e:
                print(f"Error procesando email {msg['id']}: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'emails': emails_found,
            'total': len(emails_found),
            'searchTerm': search_term,
            'fileType': file_type,
            'message': f'Encontrados {len(emails_found)} emails reales en Gmail'
        })
        
    except Exception as e:
        print(f"Error en búsqueda Gmail: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """Obtiene emails de ejemplo (para desarrollo)"""
    try:
        return jsonify({
            'success': True,
            'emails': [],
            'total': 0,
            'message': 'Usa la búsqueda para encontrar emails reales'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# DESCARGA EN ZIP - VERSIÓN SEGURA
@app.route('/api/download-batch', methods=['POST'])
def download_batch():
    """Descarga todos los archivos en ZIP"""
    try:
        data = request.json
        selected_emails = data.get('emails', [])
        user_state = data.get('state')  # ⬅️ VERIFICAR USUARIO
        
        # Verificar autenticación
        if not user_state or user_state not in user_tokens:
            return jsonify({'error': 'Usuario no autenticado'}), 401
        
        # Crear ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for email in selected_emails:
                content = f"Factura: {email['subject']}\nDe: {email['from']}\nFecha: {email['date']}"
                safe_filename = f"factura_{email['id']}.txt"
                zip_file.writestr(safe_filename, content)
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='facturas_descargadas.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))