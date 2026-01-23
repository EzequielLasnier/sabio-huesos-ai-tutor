# voice_gemini_bot.py (modificado para Token Efímero, RAG correcto)

import os
import asyncio
import traceback
import pyaudio
import logging
from datetime import datetime
import requests
import json
import pathlib

from google.oauth2.credentials import Credentials as AccessTokenCredentials
from google import genai
# --- import google.generativeai as genai ---
from google.genai import types
# --- from google.generativeai import types ---
from concurrent.futures import ProcessPoolExecutor

from langchain_client import load_and_persist_db, initialize_worker, get_rag_response_langchain

# --- CONFIGURACIÓN ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
# --- CHUNK_SIZE = 4096 ---
CHUNK_SIZE = 1024
# --- MODEL = "models/gemini-1.5-flash-latest" ---  
# --- MODEL = "gemini-live-2.5-flash-preview" ---
# --- MODEL = "gemini-2.5-flash-native-audio-preview-09-2025" (no acepta español es-ES, si Español es-US)---
# --- MODEL = "models/gemini-2.0-flash-exp" ---
MODEL = "gemini-2.0-flash-live-preview-04-09" # --- Modelo actualizado con mejor soporte de voz y español para utilizar Live.connect ---
TOKEN_SERVER_URL = "http://localhost:8000/get_token"

# --- CAMBIO CLAVE: Añadir rutas para leer el project_id ---
BASE_DIR = pathlib.Path(__file__).parent
SERVICE_ACCOUNT_FILE = BASE_DIR / "service-account-key.json"
# Ubicación estándar para modelos de Gemini.
LOCATION = "us-central1"


CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        language_code="es-US",
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Sulafat"),
        )
    ),
    system_instruction=types.Content(
        parts=[types.Part.from_text(text="""Sos un esqueleto conversacional divertido, que habla de los huesos, sólo de temas de los huesos. Cualquier otra pregunta de un tema diferente, respondes: \"Me gusta hablar más de los huesos\"

Antes de responder, preguntar el nombre de quien te habla para poder responder de manera más cercana

Recordar lo siguiente:

1- Tu nombre es PEPE el esqueleto. Antes de comenzar: "Puedes hacer 5 preguntas sobre huesos."
2- Preguntar a quien te hable si quiere saber algún detalle de algún hueso.
3- Responder en un tono amigable. 
4- Solo responder de la temática huesos. 
5- Recordar a quien habla la cantidad de preguntas restantes que puede hacer. 
6- Conversación agradable y amigable. 
7- Responder en español de Argentina.
8- Responder siempre teniendo encuenta que las respuestas las escuchan chicos de primaria.
9- Después de responder las preguntas, de vez en cuando realiza un chiste sobre huesos.
10- Al terminar de responder la 5 pregunta, decir: que buenas preguntas, muchas gracias que tengas un lindo día."""
    )],
        role="user"
    ),
)

pya = pyaudio.PyAudio()

def get_ephemeral_token():
    """Obtiene un token de corta duración desde nuestro servidor backend."""
    try:
        response = requests.get(TOKEN_SERVER_URL)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: No se pudo conectar al servidor de tokens en {TOKEN_SERVER_URL}.")
        print(f"Asegúrate de que el script 'token_server.py' se está ejecutando.")
        return None

# --- CAMBIO CLAVE: Nueva función para leer el Project ID ---
def get_project_id():
    """Lee el project_id desde el archivo de la cuenta de servicio para evitar hardcodearlo."""
    try:
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            data = json.load(f)
            return data.get('project_id')
    except Exception as e:
        print(f"❌ ERROR: No se pudo leer el project_id desde {SERVICE_ACCOUNT_FILE}: {e}")
        return None

class AudioLoop:
    # ... (El resto de la clase AudioLoop no necesita cambios)
    def __init__(self):
        self.audio_stream = None
        self.session = None
        self.mic_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue(maxsize=40)
        self.current_transcript = ""
        self.bot_is_speaking = asyncio.Event()
        self.rag_executor = ProcessPoolExecutor(
            max_workers=1,
            initializer=initialize_worker
        )

    def _drain_mic_queue(self):
        count = 0
        while not self.mic_queue.empty():
            try:
                self.mic_queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        if count > 0:
            print(f"[{datetime.now()}] 🎤 Cola del micrófono drenada ({count} paquetes descartados).")

    async def listen_audio(self):
        try:
            mic_info = pya.get_default_input_device_info()
            self.audio_stream = await asyncio.to_thread(
                pya.open, format=FORMAT, channels=CHANNELS, rate=SEND_SAMPLE_RATE,
                input=True, input_device_index=mic_info["index"], frames_per_buffer=CHUNK_SIZE
            )
            print(f"[{datetime.now()}] 🎙️  Grabando audio...")
            while True:
                data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, exception_on_overflow=False)
                await self.mic_queue.put(data)
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Error en listen_audio: {e}")
            traceback.print_exc()

    async def send_realtime(self):
        while True:
            try:
                if not self.bot_is_speaking.is_set():
                    audio_data = await self.mic_queue.get()
                    if self.session:
                        await self.session.send_realtime_input(
                            audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                        )
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"[{datetime.now()}] ⚠️ Advertencia en send_realtime: {e}")
                await asyncio.sleep(0.5)

    async def play_audio(self):
        audio_stream = None
        try:
            while True:
                audio_data = await self.out_queue.get()
                if audio_data is None:
                    if audio_stream:
                        await asyncio.to_thread(audio_stream.stop_stream)
                        await asyncio.to_thread(audio_stream.close)
                        audio_stream = None
                    continue
                if not audio_stream:
                    audio_stream = await asyncio.to_thread(
                        pya.open, format=FORMAT, channels=CHANNELS, rate=RECEIVE_SAMPLE_RATE, output=True
                    )
                await asyncio.to_thread(audio_stream.write, audio_data)
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Error en play_audio: {e}")
        finally:
            if audio_stream:
                audio_stream.close()

    async def _handle_rag_turn(self, final_query):
        start_time = datetime.now()
        print(f"[{start_time}] ⏳ Main: Enviando consulta RAG ('{final_query}') al worker...")
        try:
            loop = asyncio.get_running_loop()
            rag_response = await loop.run_in_executor(
                self.rag_executor, get_rag_response_langchain, final_query
            )
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"[{end_time}] ✔️ Main: Recibida respuesta del worker en {duration:.2f}s: '{rag_response}'")
            if self.session:
                await self.session.send_model_content(
                    turns=types.Content(role='model', parts=[types.Part(text=rag_response)]),
                    turn_complete=True
                )
        except Exception as e:
            print(f"[{datetime.now()}] ❌ ERROR CRÍTICO en _handle_rag_turn: {e}")
            traceback.print_exc()

    async def receive_audio(self):
        while True:
            bot_speech_started = False
            try:
                if not self.session:
                    await asyncio.sleep(1)
                    continue
                async for response in self.session.receive():
                    if response.text:
                        self.current_transcript += response.text + " "
                    if response.data:
                        if not bot_speech_started:
                            self.bot_is_speaking.set()
                            bot_speech_started = True
                        await self.out_queue.put(response.data)
                    if response.server_content and response.server_content.turn_complete:
                        await self.out_queue.put(None)
                        final_query = self.current_transcript.strip()
                        self.current_transcript = ""
                        bot_speech_started = False
                        self._drain_mic_queue()
                        self.bot_is_speaking.clear()
                        print(f"[{datetime.now()}] 🤗 BOT TERMINÓ DE HABLAR -> Micrófono activado.")
                        if "en que puedo ayudarte" in final_query.lower() or "hola" in final_query.lower() or not final_query:
                            print(f"✅ Turno de saludo del bot completado. Esperando al usuario.")
                        elif final_query:
                            print(f"✅ Turno del usuario completado. Consulta final: {final_query}")
                            asyncio.create_task(self._handle_rag_turn(final_query))
            except Exception as e:
                print(f"[{datetime.now()}] ❌ Error en receive_audio: {e}. Reiniciando escucha...")
                await asyncio.sleep(1)

    async def run(self):
        logging.getLogger("google.generativeai.client").setLevel(logging.ERROR)
        try:
            print(f"[{datetime.now()}] 🔑 Obteniendo token efímero del servidor...")
            ephemeral_token = get_ephemeral_token()
            project_id = get_project_id()
            if not ephemeral_token or not project_id:
                return

            print(f"[{datetime.now()}] ✅ Token y Project ID obtenidos exitosamente.")

            creds = AccessTokenCredentials(token=ephemeral_token)
            
            # --- CAMBIO CLAVE: Inicializar el cliente con todo el contexto necesario ---
            client = genai.Client(credentials=creds, project=project_id, location=LOCATION, vertexai=True)

            await load_and_persist_db()
            print(f"[{datetime.now()}] ✅ Base de datos FAISS lista en disco.")

            self.bot_is_speaking.clear()

            async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                self.session = session
                print(f"[{datetime.now()}] 🚀 Lanzando tareas principales...")
                main_tasks = [
                    self.listen_audio(),
                    self.send_realtime(),
                    self.receive_audio(),
                    self.play_audio(),
                ]
                await asyncio.gather(*main_tasks)

        except asyncio.CancelledError:
            print("\n👋 Tareas canceladas.")
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Error fatal en run: {e}")
            traceback.print_exc()
        finally:
            self.rag_executor.shutdown(wait=True)
            if self.audio_stream:
                try: self.audio_stream.close()
                except: pass
            pya.terminate()
            print(f"[{datetime.now()}] 🛑 Conexión y ejecutor cerrados.")

if __name__ == "__main__":
    main = AudioLoop()
    try:
        asyncio.run(main.run())
    except KeyboardInterrupt:
        print("\n👋 Sesión terminada por el usuario.")

