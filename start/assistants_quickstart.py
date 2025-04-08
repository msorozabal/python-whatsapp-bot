import shelve
import logging
import requests
import json
import os
import time
import sys
from openai import OpenAI
from flask import current_app
from dotenv import load_dotenv
from app.utils.message_handler import MessageHandler

# Cargar variables de entorno
load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Inicializar handler de mensajes
message_handler = MessageHandler()

# ------------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------------
# Verificar que la API key existe y no está vacía
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    logger.error("ERROR CRÍTICO: No se encontró OPENAI_API_KEY en las variables de entorno")
    # No establecer un valor por defecto en producción - esto es para indicar claramente el error

OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID", "asst_IPnFuxycd1wjp9N5qyNYJE18")
logger.info(f"Usando Assistant ID: {OPENAI_ASSISTANT_ID}")

# Inicializar cliente OpenAI con verificación
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    # Hacer una pequeña prueba para verificar que la API key funciona
    models = client.models.list()
    logger.info(f"Cliente OpenAI inicializado correctamente. API key válida: {OPENAI_API_KEY[:4]}{'*' * 20}")
except Exception as e:
    logger.error(f"ERROR inicializando cliente OpenAI: {e}")
    # En un entorno de producción podrías querer continuar con funcionalidad limitada
    # en lugar de detener la aplicación completamente

# ------------------------------------------------------------------------
# GESTIÓN DE THREADS
# ------------------------------------------------------------------------
def check_if_thread_exists(wa_id):
    """Verifica si existe un thread para el usuario de WhatsApp"""
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)

def store_thread(wa_id, thread_id):
    """Almacena un thread para el usuario de WhatsApp"""
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id

# ------------------------------------------------------------------------
# FUNCIONALIDAD PARA DESCARGAR IMÁGENES
# ------------------------------------------------------------------------
def download_image_bytes(image_url):
    """Descarga una imagen desde una URL y retorna sus bytes"""
    headers = {}
    try:
        token = current_app.config.get("ACCESS_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass

    try:
        logger.info(f"[download_image_bytes] Descargando: {image_url}")
        resp = requests.get(image_url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.error(f"No se pudo descargar la imagen {image_url}: {e}")
        return b""

# ------------------------------------------------------------------------
# EJECUTAR ASISTENTE
# ------------------------------------------------------------------------
def run_assistant(thread_id):
    """Ejecuta el asistente y retorna su respuesta"""
    try:
        # Verificar que tenemos API key y thread_id
        if not OPENAI_API_KEY:
            logger.error("No se puede ejecutar el asistente sin API key")
            return "Error de configuración: No se puede conectar con el asistente."
            
        if not thread_id:
            logger.error("No se puede ejecutar el asistente sin thread_id")
            return "Error de procesamiento: No se puede continuar la conversación."
            
        # Crear y ejecutar la corrida
        logger.info(f"Ejecutando asistente en thread: {thread_id}")
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=OPENAI_ASSISTANT_ID
        )
        
        # Esperar a que termine
        status = "waiting"
        attempt = 0
        max_attempts = 30  # Aproximadamente 15 segundos máximo
        
        while status not in ["completed", "failed", "cancelled", "expired"] and attempt < max_attempts:
            time.sleep(0.5)
            attempt += 1
            try:
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                status = run.status
                logger.info(f"Run status: {status} (intento {attempt})")
            except Exception as e:
                logger.error(f"Error verificando estado del run: {e}")
                if attempt >= max_attempts // 2:  # Si ya llevamos la mitad de los intentos, salir
                    break
        
        # Verificar errores
        if status != "completed":
            logger.error(f"La ejecución falló con estado final: {status}")
            return "Lo siento, ocurrió un problema procesando tu solicitud."
        
        # Obtener los mensajes
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        
        # Buscar el mensaje más reciente del asistente
        if not messages.data:
            logger.error("No se encontraron mensajes en el thread")
            return "No se pudo obtener una respuesta del asistente."
            
        for msg in messages.data:
            if msg.role == "assistant":
                if hasattr(msg, 'content') and len(msg.content) > 0:
                    for content_part in msg.content:
                        if hasattr(content_part, 'text') and hasattr(content_part.text, 'value'):
                            new_message = content_part.text.value
                            logger.info(f"Mensaje generado ({len(new_message)} caracteres)")
                            return new_message
        
        return "No se pudo obtener respuesta del asistente."
        
    except Exception as e:
        logger.error(f"Error en run_assistant: {e}", exc_info=True)
        return "Lo siento, ocurrió un error al procesar tu solicitud."

# ------------------------------------------------------------------------
# GENERAR RESPUESTA
# ------------------------------------------------------------------------
def generate_response(wa_id, name, message_type, message_content=None):
    """
    Procesa un mensaje de WhatsApp y genera una respuesta usando el asistente.
    
    Args:
        wa_id: ID de WhatsApp del usuario
        name: Nombre del usuario
        message_type: Tipo de mensaje (text, image, audio, location, etc)
        message_content: Contenido del mensaje
        
    Returns:
        Diccionario con la respuesta del asistente
    """
    try:
        # Verificar que tenemos API key
        if not OPENAI_API_KEY:
            error_msg = "Error de configuración: No se puede conectar con el asistente."
            logger.error(f"No hay API key configurada para usuario {name} ({wa_id})")
            return {"text_response": error_msg, "force_script": True}
        
        # Verificar o crear thread para este usuario
        thread_id = check_if_thread_exists(wa_id)
        
        # Si no existe thread, crear uno nuevo
        if thread_id is None:
            logger.info(f"Creando nuevo thread para {name} con wa_id {wa_id}")
            try:
                thread = client.beta.threads.create()
                thread_id = thread.id
                store_thread(wa_id, thread_id)
                logger.info(f"Thread creado con éxito: {thread_id}")
            except Exception as e:
                logger.error(f"Error creando thread: {e}", exc_info=True)
                error_msg = f"Lo siento {name}, no se pudo iniciar tu conversación. Por favor, inténtalo de nuevo más tarde."
                return {"text_response": error_msg, "force_script": True}
            
            # Mensaje inicial con contexto del usuario
            initial_context = f"""
Nuevo usuario: {name}
ID de WhatsApp: {wa_id}
Fecha y hora de inicio: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            try:
                client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=initial_context
                )
                logger.info(f"Mensaje inicial enviado para {name}")
            except Exception as e:
                logger.error(f"Error enviando mensaje inicial: {e}", exc_info=True)
        else:
            logger.info(f"Usando thread existente para {name}: {thread_id}")
        
        # Preparar contenido según tipo de mensaje
        content_to_send = ""
        
        # Texto: enviar directamente
        if message_type == "text":
            content_to_send = message_content
            logger.info(f"Mensaje de texto a procesar: {message_content[:50]}...")
            
        # Imagen: informar al asistente
        elif message_type == "image":
            # Descargar la imagen para procesarla
            image_bytes = download_image_bytes(message_content)
            if image_bytes:
                image_size = len(image_bytes) / 1024  # KB
                content_to_send = f"[El usuario ha enviado una imagen de aproximadamente {image_size:.1f}KB]"
                logger.info(f"Imagen recibida: {image_size:.1f}KB")
            else:
                content_to_send = "[El usuario ha enviado una imagen que no se pudo descargar]"
                logger.warning("No se pudo descargar la imagen")
                
        # Audio: informar al asistente
        elif message_type == "audio":
            content_to_send = "[El usuario ha enviado un mensaje de audio]"
            logger.info("Audio recibido")
            
        # Ubicación: extraer coordenadas y enviar
        elif message_type == "location":
            try:
                loc = json.loads(message_content) if isinstance(message_content, str) else message_content
                lat = loc.get("latitude")
                lng = loc.get("longitude")
                name_loc = loc.get("name", "No disponible")
                address = loc.get("address", "No disponible")
                
                content_to_send = f"""[El usuario ha enviado su ubicación]
Latitud: {lat}
Longitud: {lng}
Nombre: {name_loc}
Dirección: {address}
"""
                logger.info(f"Ubicación recibida: {lat}, {lng}")
            except Exception as e:
                logger.error(f"Error procesando ubicación: {e}", exc_info=True)
                content_to_send = "[El usuario ha enviado una ubicación que no se pudo procesar]"
        
        # Otro tipo de mensaje
        else:
            content_to_send = f"[El usuario ha enviado un mensaje de tipo '{message_type}']"
            logger.info(f"Mensaje de tipo '{message_type}' recibido")
        
        # Enviar mensaje al thread
        if content_to_send:
            try:
                client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=content_to_send
                )
                logger.info(f"Mensaje enviado al thread para {name}")
            except Exception as e:
                logger.error(f"Error enviando mensaje al thread: {e}", exc_info=True)
                error_msg = f"Lo siento {name}, hubo un problema al procesar tu mensaje. Por favor, inténtalo de nuevo."
                return {"text_response": error_msg, "force_script": True}
        
        # Ejecutar el asistente
        logger.info(f"Ejecutando asistente para {name}...")
        response = run_assistant(thread_id)
        logger.info(f"Respuesta obtenida para {name}")
        
        return {
            "text_response": response,
            "force_script": True
        }
        
    except Exception as e:
        logger.error(f"Error en generate_response: {e}", exc_info=True)
        return {
            "text_response": f"Lo siento {name}, ocurrió un problema. Por favor, inténtalo de nuevo más tarde.",
            "force_script": True
        }