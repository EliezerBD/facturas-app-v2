# Importación de librerías para manejo de datos, archivos zip y comunicaciones con la API de Google
import base64
import os
import zipfile
import io
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

class GmailService:
    """
    Servicio especializado en interactuar con la API de Gmail.
    Se encarga de buscar correos, procesar su contenido y descargar archivos adjuntos.
    """
    def __init__(self, token):
        # Crear objeto de credenciales de Google utilizando el token de acceso del usuario
        self.credentials = Credentials(token=token)
        # Construir el cliente del servicio de Gmail (versión v1)
        self.service = build('gmail', 'v1', credentials=self.credentials)

    def search_emails(self, search_term=None, start_date=None, end_date=None, file_type='all'):
        """
        Busca correos electrónicos en la cuenta del usuario aplicando múltiples filtros.
        """
        # Lista de palabras clave para identificar posibles facturas o documentos tributarios
        keywords = ["factura", "comprobante", "recibo", "pago", "DTE", "documento tributario", "FACT-"]
        
        # Agrupar las palabras clave usando el operador OR para la búsqueda de Gmail
        keywords_query = f"({' OR '.join(keywords)})"
        
        # Si se proporcionó un término de búsqueda manual, se añade a la consulta
        if search_term:
            query = f"{keywords_query} {search_term}"
        else:
            query = keywords_query
        
        # Requisito indispensable: el correo debe contener al menos un archivo adjunto
        query += " has:attachment"

        # Filtrar por extensión de archivo si no se seleccionó 'todos' (all)
        if file_type and file_type != 'all':
            query += f" filename:{file_type}"
        
        # Filtrar por fecha de inicio (formato after:YYYY/MM/DD)
        if start_date:
            query += f" after:{start_date.replace('-', '/')}"
        
        # Filtrar por fecha de fin (formato before:YYYY/MM/DD)
        if end_date:
            from datetime import datetime, timedelta
            try:
                # Gmail 'before' es exclusivo; sumamos un día para que el rango sea inclusivo
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                next_day = end_dt + timedelta(days=1)
                query += f" before:{next_day.strftime('%Y/%m/%d')}"
            except:
                # Si hay error en el formato, se usa la fecha tal cual reemplazando guiones por barras
                query += f" before:{end_date.replace('-', '/')}"
            
        print(f"Iniciando búsqueda en Gmail con la consulta: {query}")
        
        # Ejecutar la petición de listado de mensajes que coinciden con los criterios
        results = self.service.users().messages().list(
            userId='me', 
            q=query,
            maxResults=25 # Limitar a los 25 resultados más recientes para optimizar rendimiento
        ).execute()
        
        # Obtener la lista de mensajes (cada uno contiene ID y threadId)
        messages = results.get('messages', [])
        emails_found = []
        
        # Iterar sobre cada mensaje encontrado para extraer su información detallada
        for msg in messages:
            try:
                # Procesar el contenido del mensaje por su ID
                email_data = self._process_message(msg['id'])
                if email_data:
                    emails_found.append(email_data)
            except Exception as e:
                # En caso de error en un correo específico, imprimirlo y continuar con el siguiente
                print(f"Error procesando el correo con ID {msg['id']}: {str(e)}")
                continue
                
        return emails_found

    def _process_message(self, msg_id):
        """
        Método interno para obtener y estructurar los datos relevantes de un correo electrónico.
        """
        # Solicitar el contenido completo del mensaje
        message = self.service.users().messages().get(
            userId='me', 
            id=msg_id,
            format='full' 
        ).execute()
        
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        # Extraer el asunto (Subject), remitente (From) y fecha (Date) desde las cabeceras
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sin asunto')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Buscar recursivamente todos los adjuntos en las partes del mensaje (formato multipart)
        parts = payload.get('parts', [])
        attachments = self._find_attachments_recursive(msg_id, parts)
        
        # Si el correo no tiene adjuntos válidos (PDF, XML, JSON), se descarta de la lista
        if not attachments:
            return None
            
        # Retornar un diccionario estructurado con la información del correo
        return {
            'id': msg_id,
            'subject': subject,
            'from': sender,
            'date': date[:16] if date else 'Desconocida',
            'snippet': message.get('snippet', '')[:100] + '...', # Fragmento del texto del correo
            'attachments': attachments 
        }

    def _find_attachments_recursive(self, msg_id, parts):
        """
        Busca archivos adjuntos de forma recursiva en la estructura de partes del correo.
        """
        attachments = []
        if not parts:
            return []

        for part in parts:
            # Si la parte tiene nombre de archivo y un ID de adjunto, es un archivo real
            if part.get('filename') and part.get('body') and part.get('body').get('attachmentId'):
                filename = part.get('filename')
                # Solo procesar archivos con extensiones relevantes (PDF, XML, JSON)
                if filename.lower().endswith(('.pdf', '.xml', '.json')):
                    attachments.append({
                        'filename': filename,
                        'mimeType': part.get('mimeType'),
                        'attachmentId': part['body']['attachmentId'] # Necesario para la descarga posterior
                    })
            
            # Si la parte contiene sub-partes, realizar la búsqueda en ellas (recursión)
            if 'parts' in part:
                attachments.extend(self._find_attachments_recursive(msg_id, part['parts']))
                
        return attachments

    def download_attachments_as_zip(self, selected_emails):
        """
        Descarga los adjuntos y extrae metadatos si son JSON de DTE.
        """
        zip_buffer = io.BytesIO()
        all_extracted_metadata = [] # Nueva lista para guardar los datos de los JSON
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            filenames_added = set()

            for email in selected_emails:
                msg_id = email['id']
                for attachment in email.get('attachments', []):
                    try:
                        # Llamamos a la función y capturamos si extrajo info del DTE
                        dte_data = self._add_attachment_to_zip(zip_file, msg_id, attachment, filenames_added)
                        if dte_data:
                            all_extracted_metadata.append(dte_data)
                    except Exception as e:
                        print(f"Error descargando el archivo {attachment.get('filename')}: {str(e)}")
                        zip_file.writestr(f"ERROR_{attachment.get('filename')}.txt", str(e))

        zip_buffer.seek(0)
        return zip_buffer, all_extracted_metadata # Ahora devolvemos buffer y metadatos

    def _add_attachment_to_zip(self, zip_file, msg_id, attachment, filenames_added):
        """
        Descarga el adjunto y, si es JSON, extrae la información del DTE.
        """
        import json
        att_id = attachment['attachmentId']
        filename = attachment['filename']
        
        # Manejar colisiones de nombres
        original_filename = filename
        counter = 1
        while filename in filenames_added:
            base, ext = os.path.splitext(original_filename)
            filename = f"{base}_{counter}{ext}"
            counter += 1
        filenames_added.add(filename)

        # Petición a la API de Gmail
        attachment_data_raw = self.service.users().messages().attachments().get(
            userId='me', messageId=msg_id, id=att_id
        ).execute()
        
        file_data = base64.urlsafe_b64decode(attachment_data_raw['data'].encode('UTF-8'))
        
        # --- LÓGICA DE EXTRACCIÓN DTE ---
        dte_info = None
        if filename.lower().endswith('.json'):
            try:
                content = json.loads(file_data.decode('utf-8'))
                # Extraemos los campos que me mostraste en el ejemplo
                dte_info = {
                    'codigo_generacion': content.get('identificacion', {}).get('codigoGeneracion'),
                    'emisor_nombre': content.get('emisor', {}).get('nombre'),
                    'filename': filename
                }
            except:
                pass # Si no es un formato DTE válido, simplemente lo ignoramos
        
        # Escribir en el ZIP
        zip_file.writestr(filename, file_data)
        return dte_info

