import os
from google_auth_oauthlib.flow import Flow

class AuthService:
    """
    Servicio encargado de manejar la autenticación OAuth2 con Google.
    """
    def __init__(self):
        # Cargamos las credenciales desde variables de entorno
        self.client_id = os.getenv('CLIENT_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')
        # Si falla la variable de entorno, usamos la URL de Render a la fuerza
        self.redirect_uri = os.environ.get('REDIRECT_URI', 'https://facturas-app-v2.onrender.com/auth/callback')
        
        # Definimos los permisos (scopes) que necesitamos
        # gmail.readonly: Solo permite leer correos y adjuntos, no enviar ni borrar
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
        ]
        
        # Configuración estándar para el flujo de Google
        self.flow_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }

    def get_auth_url(self):
        """
        Genera la URL a la que debemos enviar al usuario para que inicie sesión en Google.
        """
        flow = Flow.from_client_config(
            self.flow_config,
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        # prompt='consent': Fuerza a que Google pregunte siempre por permisos (útil para pruebas)
        auth_url, state = flow.authorization_url(prompt='consent')
        return auth_url, state

    def get_token_from_code(self, code):
        """
        Recibe el 'código' temporal que nos dio Google y lo canjea por un Token de Acceso real.
        Este token es la 'llave' para leer los correos.
        """
        flow = Flow.from_client_config(
            self.flow_config,
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        # Hace la petición a Google para obtener el token
        flow.fetch_token(code=code)
        
        # Devuelve solo el token (string)
        return flow.credentials.token
    def get_user_info(self, access_token):
        """
        Obtiene la información del perfil del usuario (como el email) 
        usando el token de acceso.
        """
        import requests
        try:
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error obteniendo user info: {str(e)}")
            return None
