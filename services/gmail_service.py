import base64
import os
import zipfile
import io
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

class GmailService:
    """
    Servicio encargado de interactuar con la API de Gmail.
    Realiza búsquedas, procesa correos y descarga adjuntos.
    """
    def __init__(self, token):
        # Creamos las credenciales usando el token del usuario
        self.credentials = Credentials(token=token)
        # Construimos el cliente de la API de Gmail (versión v1)
        self.service = build('gmail', 'v1', credentials=self.credentials)

    def search_emails(self, search_term=None, start_date=None, end_date=None, file_type='all'):
        """
        Busca emails en Gmail que coincidan con los filtros.
        Devuelve una lista simplificada de emails encontrados.
        """
        # Palabras clave para intentar encontrar facturas automáticamente
        keywords = ["factura", "comprobante", "recibo", "pago", "DTE", "documento tributario", "FACT-"]
        
        # Construcción de la query de búsqueda (sintaxis de Gmail: "label:inbox has:attachment ...")
        # Unimos las palabras clave con OR en un solo grupo
        keywords_query = f"({' OR '.join(keywords)})"
        
        if search_term:
            # Si el usuario escribió algo, buscamos (palabras clave) AND (término de búsqueda)
            query = f"{keywords_query} {search_term}"
        else:
            # Si no, solo buscamos las palabras clave
            query = keywords_query
        
        # Filtro obligatorio: debe tener adjuntos
        query += " has:attachment"

        # Filtro de tipo de archivo si no es 'all'
        if file_type and file_type != 'all':
            query += f" filename:{file_type}"
        
        # Filtros de fecha (Gmail prefiere YYYY/MM/DD)
        if start_date:
            query += f" after:{start_date.replace('-', '/')}"
        if end_date:
            # Gmail 'before' es EXCLUSIVO (no incluye el día exacto).
            # Para que sea inclusivo, sumamos un día.
            from datetime import datetime, timedelta
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                next_day = end_dt + timedelta(days=1)
                query += f" before:{next_day.strftime('%Y/%m/%d')}"
            except:
                # Si falla el parseo, usamos el formato original con slashes
                query += f" before:{end_date.replace('-', '/')}"
            
        print(f"Buscando en Gmail con query: {query}")
        
        # Ejecutar la búsqueda (solo trae IDs y snippets, no el contenido completo aún)
        results = self.service.users().messages().list(
            userId='me', 
            q=query,
            maxResults=25 # Límite de resultados para no saturar
        ).execute()
        
        messages = results.get('messages', [])
        emails_found = []
        
        # Procesar cada mensaje encontrado para obtener detalles
        for msg in messages:
            try:
                email_data = self._process_message(msg['id'])
                if email_data:
                    emails_found.append(email_data)
            except Exception as e:
                print(f"Error procesando email {msg['id']}: {str(e)}")
                continue
                
        return emails_found

    def _process_message(self, msg_id):
        """
        Método privado para obtener los detalles completos de un mensaje específico.
        """
        message = self.service.users().messages().get(
            userId='me', 
            id=msg_id,
            format='full' # Pedimos toda la info (headers, cuerpo, adjuntos)
        ).execute()
        
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        # Extraer metadatos de los headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sin asunto')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Buscar adjuntos (puede haber anidados, por eso usamos una función recursiva)
        parts = payload.get('parts', [])
        attachments = self._find_attachments_recursive(msg_id, parts)
        
        # Si no tiene adjuntos válidos (PDF/XML/JSON), ignoramos este correo
        if not attachments:
            return None
            
        return {
            'id': msg_id,
            'subject': subject,
            'from': sender,
            'date': date[:16] if date else 'Desconocida',
            'snippet': message.get('snippet', '')[:100] + '...',
            'attachments': attachments 
        }

    def _find_attachments_recursive(self, msg_id, parts):
        """
        Busca adjuntos explorando todas las partes del email (multipart).
        Es recursiva porque un email puede tener partes dentro de partes.
        """
        attachments = []
        if not parts:
            return []

        for part in parts:
            # Verificamos si esta parte es un adjunto real
            if part.get('filename') and part.get('body') and part.get('body').get('attachmentId'):
                filename = part.get('filename')
                # Filtramos por extensión
                if filename.lower().endswith(('.pdf', '.xml', '.json')):
                    attachments.append({
                        'filename': filename,
                        'mimeType': part.get('mimeType'),
                        'attachmentId': part['body']['attachmentId'] # ID necesario para descargarlo luego
                    })
            
            # Si esta parte tiene sub-partes, nos llamamos a nosotros mismos (recursión)
            if 'parts' in part:
                attachments.extend(self._find_attachments_recursive(msg_id, part['parts']))
                
        return attachments

    def download_attachments_as_zip(self, selected_emails):
        """
        Crea un archivo ZIP en memoria que contiene todos los adjuntos solicitados.
        """
        zip_buffer = io.BytesIO() # Buffer en memoria (no guardamos en disco del servidor)
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            filenames_added = set() # Para evitar nombres duplicados dentro del ZIP

            for email in selected_emails:
                msg_id = email['id']
                for attachment in email.get('attachments', []):
                    try:
                        self._add_attachment_to_zip(zip_file, msg_id, attachment, filenames_added)
                    except Exception as e:
                        print(f"Error descargando adjunto {attachment.get('filename')}: {str(e)}")
                        # Si falla uno, agregamos un archivo de texto explicando el error
                        zip_file.writestr(f"ERROR_{attachment.get('filename')}.txt", str(e))

        zip_buffer.seek(0) # Rebobinar el buffer para poder leerlo desde el principio
        return zip_buffer

    def _add_attachment_to_zip(self, zip_file, msg_id, attachment, filenames_added):
        """
        Descarga el contenido binario de un adjunto y lo escribe en el ZIP.
        """
        att_id = attachment['attachmentId']
        filename = attachment['filename']
        
        # Lógica para renombrar si ya existe un archivo con el mismo nombre
        original_filename = filename
        counter = 1
        while filename in filenames_added:
            base, ext = os.path.splitext(original_filename)
            filename = f"{base}_{counter}{ext}"
            counter += 1
        filenames_added.add(filename)

        print(f"Descargando: {filename}")
        
        # Petición a la API de Gmail para obtener los datos del adjunto
        attachment_data_raw = self.service.users().messages().attachments().get(
            userId='me', 
            messageId=msg_id, 
            id=att_id
        ).execute()
        
        # Los datos vienen en Base64 URL-safe, hay que decodificarlos a binario
        file_data = base64.urlsafe_b64decode(attachment_data_raw['data'].encode('UTF-8'))
        
        # Escribir en el ZIP
        zip_file.writestr(filename, file_data)
