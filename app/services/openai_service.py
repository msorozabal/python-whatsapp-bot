import shelve
from flask import current_app
import logging
import requests
import json
from datetime import datetime
import uuid
import os

# Google Cloud
from google.cloud import storage

# Para cargar variables de entorno
from dotenv import load_dotenv

# Importar MessageHandler para la integración con Streamlit
from app.utils.message_handler import MessageHandler

# Cargar .env
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar el MessageHandler para la integración con Streamlit
message_handler = MessageHandler()

# ------------------------------------------------------------------------
# 1. CONFIGURACIÓN GCS
# ------------------------------------------------------------------------
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./kapta-service-account.json")
client = storage.Client.from_service_account_json(creds_path)
GCS_BUCKET_NAME = "kapta-bucket"  # Cámbialo si es distinto

# ------------------------------------------------------------------------
# 2. FUNCIONES PARA SUBIR A GCS
# ------------------------------------------------------------------------
def download_image_bytes(image_url):
    """
    Descarga la imagen desde 'image_url' y retorna los bytes.
    Intenta incluir el header de autorización si ACCESS_TOKEN está definido en current_app.
    """
    headers = {}
    try:
        token = current_app.config.get('ACCESS_TOKEN')
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        logger.error(f"Error accediendo a current_app config: {e}")
    try:
        resp = requests.get(image_url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.error(f"No se pudo descargar la imagen {image_url}: {e}")
        return b""

def upload_bytes_to_gcs(destination_blob_name, file_bytes, content_type="image/jpeg"):
    """
    Sube 'file_bytes' al bucket 'GCS_BUCKET_NAME' en la ruta 'destination_blob_name'.
    Retorna la URL del blob (si el bucket es público).
    """
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(file_bytes, content_type=content_type)
    logger.info(f"Subido gs://{GCS_BUCKET_NAME}/{destination_blob_name}")
    return blob.public_url

def upload_json_to_gcs(destination_blob_name, data_dict):
    """
    Sube 'data_dict' como un archivo JSON al bucket 'GCS_BUCKET_NAME'.
    """
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    json_str = json.dumps(data_dict, ensure_ascii=False, indent=2)
    blob.upload_from_string(json_str, content_type="application/json")
    logger.info(f"JSON subido gs://{GCS_BUCKET_NAME}/{destination_blob_name}")
    return blob.public_url

# ------------------------------------------------------------------------
# 3. SCRIPT Y EJEMPLOS
# ------------------------------------------------------------------------
"""
La secuencia para ambos canales es la siguiente:
  PASO 0: Mensaje inicial.
  PASO 1: Nombre de la tienda.
  PASO 2: Dirección de la tienda.
  PASO 3: Ubicación actual (mensaje de tipo location de WhatsApp).
  PASO 4 en adelante: Se piden las fotos (para fachada y otras secciones).
"""

SCRIPT_CONTENT = {
    "ONBOARDING": [
        "Para comenzar con el proceso de registro necesitamos validar tus datos. Por favor envíame una foto de tu cédula (frente y reverso).",
        "Gracias, ¿me ayudas a contestar estas preguntas?\n¿Para qué cliente de Eficacia trabajas?\n¿Visitas principalmente supermercados o tiendas de barrio?"
    ],
    "CANAL_TRADICIONAL": [
        "👋Hola, {name}! Estoy listo para registrar la tienda. ¿Listo?",
        "Por favor, envíame *el nombre de la tienda*.",
        "Excelente. Ahora envíame *la dirección de la tienda*.",
        "Perfecto, ahora compárteme la *ubicación actual de la tienda* (mensaje de tipo location).",
        "Ahora, envíame una foto de la fachada de la tienda (1 foto requerida).",
        "🥃 Toma 3 fotos de la sección de bebidas alcohólicas...",
        "🥤 Envía 3 fotos de las bebidas sin alcohol...",
        "🍪 Manda 3 fotos de la sección de snacks...",
        "🥚 Envía 3 fotos de la sección de huevos...",
        "🚬 Toma 3 fotos de la sección de cigarrillos...",
        "🧴 Envía 3 fotos de la sección de cuidado personal...",
        "🎤 Por último, envía un audio.",
        "✅ ¡Gracias {name} por compartir toda la información!"
    ],
    "CANAL_MODERNO": [
        "👋Hola, {name}! Estoy listo para registrar la tienda. ¿Listo?",
        "Por favor, envíame *el nombre de la tienda*.",
        "Excelente. Ahora envíame *la dirección de la tienda*.",
        "Perfecto, ahora compárteme la *ubicación actual de la tienda* (mensaje de tipo location).",
        "Ahora, envíame una foto de la fachada de la tienda (1 foto requerida).",
        "🥃 Toma 3 fotos de la sección de bebidas alcohólicas...",
        "🥤 Envía 3 fotos de las bebidas sin alcohol...",
        "🍪 Manda 3 fotos de la sección de snacks...",
        "🥚 Envía 3 fotos de la sección de huevos...",
        "🚬 Toma 3 fotos de la sección de cigarrillos...",
        "🧴 Envía 3 fotos de la sección de cuidado personal...",
        "🎤 Por último, envía un audio.",
        "✅ ¡Gracias {name} por compartir toda la información!"
    ]
}

EXAMPLE_IMAGES = {
    "fachada": "https://example.com/images/fachada.jpg",
    "bebidas_alcoholicas": "https://example.com/images/bebidas_alcoholicas.jpg",
    "bebidas_no_alcoholicas": "https://example.com/images/bebidas_no_alcoholicas.jpg",
    "snacks": "https://example.com/images/snacks.jpg",
    "huevos": "https://example.com/images/huevos.jpg",
    "cigarrillos": "https://example.com/images/cigarrillos.jpg",
    "cuidado_personal": "https://example.com/images/cuidado_personal.jpg"
}

def get_example_image_url(section):
    return EXAMPLE_IMAGES.get(section, "https://example.com/images/default.jpg")

# ------------------------------------------------------------------------
# 4. SLACK WEBHOOKS
# ------------------------------------------------------------------------
SLACK_WEBHOOK_URL = os.getenv("WEBHOOK_SLACK")

def post_to_slack_onboarding(username, phone_number, webhook_url=SLACK_WEBHOOK_URL):
    try:
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        data = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "🚀 NUEVO USUARIO EN ONBOARDING 🚀", "emoji": True}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*Se ha iniciado un nuevo proceso de onboarding...*"}},
                {"type": "divider"},
                {"type": "section", "fields": [
                    {"type": "mrkdwn", "text": f"*Usuario:* `{username}`"},
                    {"type": "mrkdwn", "text": f"*Teléfono:* `{phone_number}`"}
                ]},
                {"type": "section", "text": {"type": "mrkdwn", "text": "⏱️ *Estado:* Iniciando proceso de validación"}},
                {"type": "divider"},
                {"type": "context", "elements": [
                    {"type": "mrkdwn", "text": f"📅 Fecha y hora: {current_time}"}
                ]}
            ]
        }
        resp = requests.post(webhook_url, json=data, headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            logger.error(f"Error Slack onboarding: {resp.status_code} {resp.text}")
            return False
        logger.info(f"Onboarding notificado para {username}")
        return True
    except Exception as e:
        logger.error(f"Excepción Slack onboarding: {e}")
        return False

def post_to_slack_new_store(username, phone_number, client_info, store_type, webhook_url=SLACK_WEBHOOK_URL):
    try:
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        canal = "Canal Moderno" if "supermercados" in store_type.lower() else "Canal Tradicional"
        data = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "🚨 ¡NUEVA TIENDA EN PROCESO! 🚨", "emoji": True}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"✨ El usuario {username} ha comenzado a registrar una nueva tienda ✨"}},
                {"type": "divider"},
                {"type": "section", "fields": [
                    {"type": "mrkdwn", "text": f"*Usuario:* `{username}`"},
                    {"type": "mrkdwn", "text": f"*Teléfono:* `{phone_number}`"}
                ]},
                {"type": "section", "fields": [
                    {"type": "mrkdwn", "text": f"*Cliente:* `{client_info}`"},
                    {"type": "mrkdwn", "text": f"*Canal:* `{canal}`"}
                ]},
                {"type": "section", "text": {"type": "mrkdwn", "text": "⏱️ *Estado:* En proceso de registro"}},
                {"type": "divider"},
                {"type": "context", "elements": [
                    {"type": "mrkdwn", "text": f"📅 Fecha y hora: {current_time}"}
                ]}
            ]
        }
        resp = requests.post(webhook_url, json=data, headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            logger.error(f"Error Slack new store: {resp.status_code} {resp.text}")
            return False
        logger.info(f"Nueva tienda notificada para {username}")
        return True
    except Exception as e:
        logger.error(f"Excepción Slack new store: {e}")
        return False

def post_to_slack_end_process(username, phone_number, total_time_str, webhook_url=SLACK_WEBHOOK_URL):
    try:
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        data = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "✅ FIN DEL PROCESO ✅", "emoji": True}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*El usuario {username} ha completado todo el proceso.*"}},
                {"type": "divider"},
                {"type": "section", "fields": [
                    {"type": "mrkdwn", "text": f"*Usuario:* `{username}`"},
                    {"type": "mrkdwn", "text": f"*Teléfono:* `{phone_number}`"},
                    {"type": "mrkdwn", "text": f"*Tiempo total:* `{total_time_str}`"}
                ]},
                {"type": "section", "text": {"type": "mrkdwn", "text": "⏱️ *Estado:* Finalizado"}},
                {"type": "divider"},
                {"type": "context", "elements": [
                    {"type": "mrkdwn", "text": f"📅 Fecha y hora: {current_time}"}
                ]}
            ]
        }
        resp = requests.post(webhook_url, json=data, headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            logger.error(f"Error Slack end process: {resp.status_code} {resp.text}")
            return False
        logger.info(f"Fin del proceso notificado para {username}")
        return True
    except Exception as e:
        logger.error(f"Excepción Slack end process: {e}")
        return False

# ------------------------------------------------------------------------
# 5. DB (shelve)
# ------------------------------------------------------------------------
def get_db():
    return shelve.open("conversation_states")

def get_conversation_state(wa_id):
    with get_db() as db:
        state = db.get(wa_id, None)
        if state:
            updated = False
            if not hasattr(state, 'onboarding_notified'):
                state.onboarding_notified = False
                updated = True
            if not hasattr(state, 'new_store_notified'):
                state.new_store_notified = False
                updated = True
            if not hasattr(state, 'start_time'):
                state.start_time = datetime.now()
                updated = True
            if not hasattr(state, 'end_notified'):
                state.end_notified = False
                updated = True
            if not hasattr(state, 'conversation_id'):
                state.conversation_id = f"conv_{uuid.uuid4()}"
                updated = True
            if updated:
                db[wa_id] = state
        return state

def store_conversation_state(wa_id, state):
    with get_db() as db:
        if not hasattr(state, 'conversation_id'):
            state.conversation_id = f"conv_{uuid.uuid4()}"
        db[wa_id] = state

# ------------------------------------------------------------------------
# 6. CONVERSATION STATE
# ------------------------------------------------------------------------
class ConversationState:
    def __init__(self, wa_id, name, channel=None, current_step="ONBOARDING", step_index=0):
        self.wa_id = wa_id
        self.name = name
        self.channel = channel
        self.current_step = current_step
        self.step_index = step_index
        self.data = {}  # Datos adicionales: store_name, store_address, store_location, etc.
        self.photo_counts = {}
        self.onboarding_notified = False
        self.new_store_notified = False
        self.start_time = datetime.now()
        self.end_notified = False
        self.conversation_id = f"conv_{uuid.uuid4()}"

    def to_dict(self):
        return {
            'wa_id': self.wa_id,
            'name': self.name,
            'channel': self.channel,
            'current_step': self.current_step,
            'step_index': self.step_index,
            'data': self.data,
            'photo_counts': self.photo_counts,
            'onboarding_notified': self.onboarding_notified,
            'new_store_notified': self.new_store_notified,
            'start_time': self.start_time.isoformat(),
            'end_notified': self.end_notified,
            'conversation_id': self.conversation_id
        }

    @classmethod
    def from_dict(cls, d):
        obj = cls(
            d['wa_id'],
            d['name'],
            channel=d.get('channel'),
            current_step=d.get('current_step', 'ONBOARDING'),
            step_index=d.get('step_index', 0)
        )
        obj.data = d.get('data', {})
        obj.photo_counts = d.get('photo_counts', {})
        obj.onboarding_notified = d.get('onboarding_notified', False)
        obj.new_store_notified = d.get('new_store_notified', False)
        if d.get('start_time'):
            obj.start_time = datetime.fromisoformat(d['start_time'])
        else:
            obj.start_time = datetime.now()
        obj.end_notified = d.get('end_notified', False)
        obj.conversation_id = d.get('conversation_id', f"conv_{uuid.uuid4()}")
        return obj

    def get_current_script(self):
        return SCRIPT_CONTENT.get(self.current_step, [])

    def get_current_message(self):
        script = self.get_current_script()
        if self.step_index < len(script):
            return script[self.step_index].format(name=self.name)
        return None

    def notify_end_of_flow(self):
        end_time = datetime.now()
        total_time = end_time - self.start_time
        total_time_str = str(total_time).split('.')[0]
        post_to_slack_end_process(self.name, self.wa_id, total_time_str)
        self.end_notified = True

    def advance_step(self):
        script = self.get_current_script()
        if self.current_step == "ONBOARDING" and self.step_index == 1:
            user_response = self.data.get('onboarding_response', '').lower()
            if "supermercados" in user_response:
                self.channel = "CANAL_MODERNO"
            else:
                self.channel = "CANAL_TRADICIONAL"
            self.current_step = self.channel
            self.step_index = 0
            self.photo_counts = {}
            return
        if self.step_index < len(script) - 1:
            self.step_index += 1
            self.photo_counts = {}
            if self.step_index == len(script) - 1 and not self.end_notified:
                self.notify_end_of_flow()
        else:
            if not self.end_notified:
                self.notify_end_of_flow()

    def process_message(self, message_type, content=None):
        # ---------------------------
        # ONBOARDING
        # ---------------------------
        if self.current_step == "ONBOARDING":
            if self.step_index == 0:
                if message_type == "image" and content:
                    self._upload_onboarding_image(content)
                    self.advance_step()
                    return True
            elif self.step_index == 1:
                if message_type == "text":
                    self.data['onboarding_response'] = content
                    if not self.new_store_notified:
                        self._maybe_notify_new_store(content)
                    self.advance_step()
                    return True

        # ---------------------------
        # CANAL TRADICIONAL
        # ---------------------------
        elif self.current_step == "CANAL_TRADICIONAL":
            if self.step_index == 0:
                self.advance_step()
                return True
            elif self.step_index == 1:
                if message_type == "text":
                    self.data['store_name'] = content.strip()
                    self._upload_conversation_json()
                    self.advance_step()
                    return True
            elif self.step_index == 2:
                if message_type == "text":
                    self.data['store_address'] = content.strip()
                    self._upload_conversation_json()
                    self.advance_step()
                    return True
            elif self.step_index == 3:
                if message_type in ("location", "text"):
                    loc = {}
                    if isinstance(content, dict):
                        loc = content
                    else:
                        try:
                            loc = json.loads(content)
                        except Exception:
                            loc = {}
                    lat = loc.get("latitude")
                    lng = loc.get("longitude")
                    if lat is not None and lng is not None:
                        self.data['store_location'] = {"latitude": lat, "longitude": lng}
                        self._upload_conversation_json()
                        self.advance_step()
                        return True
                    else:
                        logger.info("No se detectó latitud/longitud. Por favor, envía la ubicación de WhatsApp.")
                        return False
            elif self.step_index >= 4:
                sections = [
                    'fachada', 'bebidas_alcoholicas', 'bebidas_no_alcoholicas',
                    'snacks', 'huevos', 'cigarrillos', 'cuidado_personal', 'audio'
                ]
                idx = self.step_index - 4
                if idx < len(sections):
                    section = sections[idx]
                    if message_type == ("audio" if section == "audio" else "image"):
                        if section != "audio" and content:
                            if section == "fachada":
                                self._upload_fachada_image(content)
                                self.photo_counts[section] = self.photo_counts.get(section, 0) + 1
                                if self.photo_counts[section] >= 1:
                                    self.advance_step()
                                    return True
                            else:
                                self._upload_product_image(content, section)
                                self.photo_counts[section] = self.photo_counts.get(section, 0) + 1
                                if self.photo_counts[section] >= 3:
                                    self.advance_step()
                                    return True
                            return False
                        else:
                            self.advance_step()
                            return True
                return False

        # ---------------------------
        # CANAL MODERNO
        # ---------------------------
        elif self.current_step == "CANAL_MODERNO":
            if self.step_index == 0:
                self.advance_step()
                return True
            elif self.step_index == 1:
                if message_type == "text":
                    self.data['store_name'] = content.strip()
                    self._upload_conversation_json()
                    self.advance_step()
                    return True
            elif self.step_index == 2:
                if message_type == "text":
                    self.data['store_address'] = content.strip()
                    self._upload_conversation_json()
                    self.advance_step()
                    return True
            elif self.step_index == 3:
                if message_type in ("location", "text"):
                    logger.info(f"Ubicación recibida: {content}")
                    loc = {}
                    if isinstance(content, dict):
                        loc = content
                    else:
                        try:
                            loc = json.loads(content)
                        except Exception:
                            loc = {}
                    lat = loc.get("latitude")
                    lng = loc.get("longitude")
                    if lat is None or lng is None:
                        logger.info("No se detectaron latitud y/o longitud. Envía la ubicación real de WhatsApp.")
                        return False
                    if not loc.get("name") or not loc.get("address"):
                        logger.info("Falta nombre y/o dirección en la ubicación. Por favor, envía un mensaje de texto con 'Nombre: X, Dirección: Y'.")
                        return False
                    self.data['store_location'] = {
                        "latitude": lat,
                        "longitude": lng,
                        "name": loc.get("name"),
                        "address": loc.get("address")
                    }
                    self._upload_conversation_json()
                    self.advance_step()
                    return True
            elif self.step_index >= 4:
                sections = [
                    'bebidas_alcoholicas', 'bebidas_no_alcoholicas',
                    'snacks', 'huevos', 'cigarrillos', 'cuidado_personal', 'audio'
                ]
                idx = self.step_index - 4
                if idx < len(sections):
                    section = sections[idx]
                    if message_type == ("audio" if section == "audio" else "image"):
                        if section != "audio" and content:
                            self._upload_product_image(content, section)
                            self.photo_counts[section] = self.photo_counts.get(section, 0) + 1
                            if self.photo_counts[section] >= 3:
                                self.advance_step()
                                return True
                            return False
                        else:
                            self.advance_step()
                            return True
                return False

        return False

    def _maybe_notify_new_store(self, content):
        cliente = "No especificado"
        visita = "No especificado"
        if "cliente" in content.lower() and "trabajo" in content.lower():
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "cliente" in line.lower() and i + 1 < len(lines):
                    cliente = lines[i+1].strip()
                    break
        if "supermercados" in content.lower():
            visita = "Principalmente supermercados"
        elif "tienda" in content.lower():
            visita = "Principalmente tiendas de barrio"
        post_to_slack_new_store(self.name, self.wa_id, cliente, visita)
        self.new_store_notified = True

    def _upload_onboarding_image(self, image_url):
        img_bytes = download_image_bytes(image_url)
        if not img_bytes:
            logger.error(f"Imagen vacía al descargar desde {image_url}")
            return
        file_name = f"onboarding/{self.conversation_id}_cedula.jpg"
        upload_bytes_to_gcs(file_name, img_bytes)
        json_name = f"onboarding/{self.conversation_id}_conversation.json"
        upload_json_to_gcs(json_name, self.to_dict())

    def _upload_fachada_image(self, image_url):
        img_bytes = download_image_bytes(image_url)
        if not img_bytes:
            logger.error(f"Imagen vacía al descargar desde {image_url}")
            return
        store_name = self.data.get('store_address', 'no_name').replace(' ', '_')
        store_id = f"store_{uuid.uuid4()}"
        file_name = f"stores/{store_name}_{store_id}/{self.conversation_id}_fachada.jpg"
        upload_bytes_to_gcs(file_name, img_bytes)
        json_name = f"stores/{store_name}_{store_id}/{self.conversation_id}_conversation.json"
        upload_json_to_gcs(json_name, self.to_dict())

    def _upload_product_image(self, image_url, section):
        img_bytes = download_image_bytes(image_url)
        if not img_bytes:
            logger.error(f"Imagen vacía al descargar desde {image_url}")
            return
        random_id = uuid.uuid4()
        file_name = f"products/{section}/{self.conversation_id}_{random_id}.jpg"
        upload_bytes_to_gcs(file_name, img_bytes)
        json_name = f"products/{section}/{self.conversation_id}_conversation.json"
        upload_json_to_gcs(json_name, self.to_dict())

    def _upload_conversation_json(self):
        json_name = f"onboarding/{self.conversation_id}_conversation.json"
        upload_json_to_gcs(json_name, self.to_dict())
        logger.info(f"Conversación actualizada en {json_name}")

# ------------------------------------------------------------------------
# 7. LÓGICA PRINCIPAL DE RESPUESTA
# ------------------------------------------------------------------------
def generate_response(wa_id, name, message_type, message_content=None):
    try:
        state = get_conversation_state(wa_id)
        if not state:
            state = ConversationState(wa_id, name)
            logger.info(f"Enviando notificación ONBOARDING para {name} ({wa_id})")
            post_to_slack_onboarding(name, wa_id)
            state.onboarding_notified = True
            store_conversation_state(wa_id, state)

        state.process_message(message_type, message_content)

        response_data = {
            'text_response': state.get_current_message(),
            'force_script': True
        }

        store_conversation_state(wa_id, state)
        return response_data

    except Exception as e:
        logger.error(f"Error crítico en generate_response: {e}")
        error_response = f"Hola {name}, estamos experimentando problemas técnicos. Por favor, intenta más tarde."
        message_handler.add_message(wa_id, error_response, is_bot=True)
        return {
            'text_response': error_response,
            'force_script': True
        }
