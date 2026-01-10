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
        Implementa lógica de agrupación y renombrado inteligente basado en el código de generación del DTE.
        """
        import json  # Importación local para asegurar disponibilidad
        
        zip_buffer = io.BytesIO()
        all_extracted_metadata = []
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
             # Set para manejar colisiones de nombres dentro del ZIP
            filenames_added = set()

            for email in selected_emails:
                msg_id = email['id']
                attachments = email.get('attachments', [])
                
                # --- PASO 1: Buscar el código de generación en los JSON del correo ---
                nombre_factura_oficial = None
                emisor_dte = None

                for att in attachments:
                    if att['filename'].lower().endswith('.json'):
                        # Descargamos momentáneamente para leerlo y buscar el código
                        att_id = att['attachmentId']
                        try:
                            raw_data = self.service.users().messages().attachments().get(
                                userId='me', messageId=msg_id, id=att_id
                            ).execute()
                            file_content = base64.urlsafe_b64decode(raw_data['data'].encode('UTF-8'))
                            
                            dict_data = json.loads(file_content.decode('utf-8'))
                            # Extraemos el código de Generación (identificador único de Hacienda)
                            codigo = dict_data.get('identificacion', {}).get('codigoGeneracion')
                            
                            if codigo:
                                nombre_factura_oficial = f"DTE_{codigo}"
                                emisor_dte = dict_data.get('emisor', {}).get('nombre')
                                
                                # Guardamos los metadatos para el historial
                                all_extracted_metadata.append({
                                    'codigo_generacion': codigo,
                                    'emisor_nombre': emisor_dte,
                                    'filename': att['filename'] # Guardamos referencia al nombre original
                                })
                                break # Ya encontramos el identificador principal, no es necesario seguir buscando en otros JSON
                        except Exception as e:
                            print(f"Error analizando JSON {att['filename']}: {str(e)}")
                            continue

                # --- PASO 2: Descargar y renombrar todos los archivos del mismo correo ---
                for att in attachments:
                    try:
                        att_id = att['attachmentId']
                        original_filename = att['filename']
                        ext = os.path.splitext(original_filename)[1] # Obtiene extensión (.pdf, .json, etc.)
                        
                        # Definir el nuevo nombre: Oficial si se encontró código, o mantener original
                        if nombre_factura_oficial:
                            nuevo_nombre = f"{nombre_factura_oficial}{ext}"
                        else:
                            nuevo_nombre = original_filename
                            
                        # Manejo de colisiones: si el nombre ya existe en el ZIP, agregar contador
                        # Esto es vital si procesamos varios correos que no tengan DTE (ej. "factura.pdf")
                        nombre_final = nuevo_nombre
                        counter = 1
                        while nombre_final in filenames_added:
                            base, f_ext = os.path.splitext(nuevo_nombre)
                            nombre_final = f"{base}_{counter}{f_ext}"
                            counter += 1
                        filenames_added.add(nombre_final)

                        # Descarga real del archivo para guardarlo
                        att_data_raw = self.service.users().messages().attachments().get(
                            userId='me', messageId=msg_id, id=att_id
                        ).execute()
                        file_data = base64.urlsafe_b64decode(att_data_raw['data'].encode('UTF-8'))
                        
                        # Escribir en el archivo ZIP con el nombre final determinado
                        zip_file.writestr(nombre_final, file_data)
                        
                    except Exception as e:
                        print(f"Error descargando/guardando el archivo {att.get('filename')}: {str(e)}")
                        # Opcional: Escribir un archivo de error en el zip
                        zip_file.writestr(f"ERROR_{att.get('filename')}.txt", str(e))

        zip_buffer.seek(0)
        return zip_buffer, all_extracted_metadata

