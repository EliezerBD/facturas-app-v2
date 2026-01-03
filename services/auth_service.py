# Importación de librerías para manejo de sistema y autenticación de Google
import os
from google_auth_oauthlib.flow import Flow

class AuthService:
    """
    Servicio encargado de manejar todo el flujo de autenticación OAuth2 con Google.
    Permite obtener la URL de login y canjear el código por un token.
    """
    def __init__(self):
        # Obtener el ID de cliente de Google desde las variables de entorno
        self.client_id = os.getenv('CLIENT_ID')
        # Obtener el Secreto de cliente de Google desde las variables de entorno
        self.client_secret = os.getenv('CLIENT_SECRET')
        # Definir la URL de redirección a la que Google enviará al usuario tras el login
        # Se prioriza la variable REDIRECT_URI, con un valor por defecto para producción
        self.redirect_uri = os.environ.get('REDIRECT_URI', 'https://facturas-app-v2.onrender.com/auth/callback')
        
        # Definir los alcances (scopes) de los permisos solicitados al usuario
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly', # Permiso para leer correos de Gmail
            'https://www.googleapis.com/auth/userinfo.email',   # Permiso para ver la dirección de correo
            'https://www.googleapis.com/auth/userinfo.profile', # Permiso para ver info básica del perfil
            'openid'                                           # Protocolo de autenticación estándar
        ]
        
        # Configurar el diccionario de configuración para el flujo de trabajo de Google
        self.flow_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth", # Endpoint de autorización
                "token_uri": "https://oauth2.googleapis.com/token"         # Endpoint para obtener tokens
            }
        }

    def get_auth_url(self):
        """
        Genera la URL de autorización a la que el frontend debe redirigir al usuario.
        """
        # Crear el objeto Flow utilizando la configuración definida
        flow = Flow.from_client_config(
            self.flow_config,
            scopes=self.scopes
        )
        # Establecer la URL de redirección en el flujo
        flow.redirect_uri = self.redirect_uri
        
        # Generar la URL de autorización solicitando consentimiento explícito (prompt='consent')
        auth_url, state = flow.authorization_url(prompt='consent')
        return auth_url, state

    def get_token_from_code(self, code):
        """
        Intercambia el código de autorización temporal por un token de acceso permanente.
        """
        # Crear nuevamente el objeto Flow para el intercambio
        flow = Flow.from_client_config(
            self.flow_config,
            scopes=self.scopes
        )
        # Asegurar que la URL de redirección coincida con la usada inicialmente
        flow.redirect_uri = self.redirect_uri
        
        # Realizar la petición a los servidores de Google para obtener el token
        flow.fetch_token(code=code)
        
        # Retornar únicamente la cadena del token de acceso
        return flow.credentials.token

    def get_user_info(self, access_token):
        """
        Utiliza el token de acceso para obtener información detallada del perfil del usuario.
        """
        import requests
        try:
            # Realizar una petición GET al endpoint de información de usuario de Google
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'} # Incluir el token en la cabecera
            )
            # Si la respuesta es exitosa (200 OK), retornar los datos en formato JSON
            if response.status_code == 200:
                return response.json()
            # En caso contrario, retornar None
            return None
        except Exception as e:
            # Capturar e imprimir cualquier error durante la comunicación
            print(f"Error obteniendo user info: {str(e)}")
            return None

