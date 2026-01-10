import os
import requests
import json

class SupabaseService:
    def __init__(self):
        self.url = os.environ.get('SUPABASE_URL')
        self.key = os.environ.get('SUPABASE_KEY')
        self.base_url = f"{self.url}/rest/v1/historial_facturas"

    def save_history(self, history_data):
        if not self.url or not self.key:
            print("Supabase credentials not configured in environment")
            return False

        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

        try:
            response = requests.post(self.base_url, headers=headers, data=json.dumps(history_data))
            if response.status_code in [200, 201]:
                print("History saved to Supabase successfully")
                return True
            else:
                print(f"Error saving to Supabase: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Connection error with Supabase: {str(e)}")
            return False

    def get_user_history(self, user_email):
        """
        Recupera todo el historial de un usuario específico para saber qué ha descargado.
        """
        if not self.url or not self.key:
            return []

        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        
        params = {
            "usuario_email": f"eq.{user_email}",
            "select": "codigo_generacion,nombre_archivo,gmail_message_id,emisor"
        }

        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error recuperando historial: {str(e)}")
            return []

    def save_refresh_token(self, email, refresh_token):
        """
        Guarda o actualiza el refresh token de Google para un usuario.
        """
        if not self.url or not self.key:
            return False

        # Endpoint para la tabla users
        users_url = f"{self.url}/rest/v1/users"
        
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates" # Upsert (inserta o actualiza si existe)
        }
        
        data = {
            "email": email,
            "google_refresh_token": refresh_token,
            "updated_at": "now()"
        }

        try:
            # Usamos POST con Prefer: resolution=merge-duplicates para comportamiento de UPSERT
            response = requests.post(users_url, headers=headers, data=json.dumps(data))
            if response.status_code in [200, 201]:
                print(f"Refresh token saved for {email}")
                return True
            else:
                print(f"Error saving refresh token: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Connection error saving token: {str(e)}")
            return False
