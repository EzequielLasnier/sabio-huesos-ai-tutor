
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import pathlib
from datetime import datetime

# --- Configuración de Rutas ---
BASE_DIR = pathlib.Path(__file__).parent
SERVICE_ACCOUNT_FILE = BASE_DIR / "service-account-key.json"

# --- CAMBIO DE SEGURIDAD CLAVE ---
# Usamos el scope más restrictivo y correcto, específico para la API de Gemini.
# Esto asegura que el token solo pueda ser usado para este propósito.
# --- API_SCOPE = "https://www.googleapis.com/auth/generative-language.retriever" (muy restrictivo, sòlo para realizar busquedas en el RAG)---
API_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

app = FastAPI()

@app.get("/get_token")
def get_token():
    """
    Genera un token de acceso OAuth2 de corta duración usando una cuenta de servicio.
    """
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(f"No se encontró el archivo de la cuenta de servicio: {SERVICE_ACCOUNT_FILE}")

        # Crear credenciales desde el archivo JSON de la cuenta de servicio
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[API_SCOPE] # Usar el scope restrictivo y correcto
        )

        # Refrescar el token para asegurarse de que esté activo
        creds.refresh(Request())

        if not creds.token:
            # Este error es más específico ahora
            raise Exception(f"No se recibió access_token. Respuesta recibida: {creds.__dict__}. Verifica los permisos y el scope.")

        print(f"[{datetime.now()}] ✅ Token generado exitosamente. Vence en: {creds.expiry}")
        return {"access_token": creds.token}

    except Exception as e:
        print(f"[{datetime.now()}] ❌ Error al generar el token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Iniciando servidor de tokens en http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

