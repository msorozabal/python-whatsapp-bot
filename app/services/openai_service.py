import shelve
import logging
import requests
import json
import os
import time
import sys
import re
import random
import uuid
from datetime import datetime
from google.cloud import documentai_v1 as documentai
from google.cloud import storage
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
# CONFIGURACIÓN INICIAL
# ------------------------------------------------------------------------
# Verificar que las API keys existen
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us")  # Default: us
DOCAI_PROCESSOR_ID = os.getenv("GCP_DOCAI_PROCESSOR_ID", "")

creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

client = storage.Client.from_service_account_json(creds_path)
GCS_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME", "kapta-bucket")

print(creds_path)

if not all([OPENAI_API_KEY, GCP_PROJECT_ID, DOCAI_PROCESSOR_ID, GCS_BUCKET_NAME]):
    logger.error("ERROR CRÍTICO: Faltan variables de entorno esenciales")

# Inicializar clientes
try:
    # OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    # Don't call models.list() here - it's causing problems in your initialization
    logger.info(f"Cliente OpenAI inicializado correctamente")
    
    # Set up explicit credentials for Google Cloud
    import os
    from google.oauth2 import service_account
    
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS no está configurado")
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is required")
    
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    
    # Google Document AI with explicit project and credentials
    docai_client = documentai.DocumentProcessorServiceClient(credentials=credentials)
    logger.info(f"Cliente Document AI inicializado correctamente")
    
    # Google Cloud Storage with explicit project and credentials
    storage_client = storage.Client(
        project=GCP_PROJECT_ID,
        credentials=credentials
    )
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    logger.info(f"Cliente Cloud Storage inicializado correctamente para bucket {GCS_BUCKET_NAME}")
    
except Exception as e:
    logger.error(f"ERROR inicializando clientes: {e}", exc_info=True)
    # Set clients to None so you can check for this later
    docai_client = None
    storage_client = None
    bucket = None
    
# ------------------------------------------------------------------------
# GESTIÓN DE CONVERSACIONES
# ------------------------------------------------------------------------
def get_conversation_history(wa_id):
    """Obtiene el historial de conversación para un usuario de WhatsApp"""
    with shelve.open("conversation_history") as history_shelf:
        return history_shelf.get(wa_id, [])

def store_conversation_history(wa_id, history):
    """Almacena el historial de conversación para un usuario de WhatsApp"""
    with shelve.open("conversation_history", writeback=True) as history_shelf:
        history_shelf[wa_id] = history

def get_user_data(wa_id):
    """Obtiene los datos del usuario"""
    with shelve.open("user_data") as data_shelf:
        return data_shelf.get(wa_id, {})

def store_user_data(wa_id, data):
    """Almacena los datos del usuario"""
    with shelve.open("user_data", writeback=True) as data_shelf:
        data_shelf[wa_id] = data

# ------------------------------------------------------------------------
# PROCESAMIENTO DE DOCUMENTOS CON DOCUMENT AI
# ------------------------------------------------------------------------
def process_document_with_docai(image_bytes, mime_type="image/jpeg"):
    """
    Procesa un documento usando Document AI para extraer texto y datos estructurados
    
    Args:
        image_bytes: Bytes de la imagen/documento a procesar
        mime_type: Tipo MIME del documento (default: image/jpeg)
        
    Returns:
        Dict con los datos extraídos y el texto completo
    """
    if not docai_client:
        logger.error("El cliente Document AI no está inicializado")
        return {
            "success": False,
            "error": "Cliente Document AI no inicializado"
        }
        
    try:
        # Configurar el request para Document AI
        name = f"projects/{GCP_PROJECT_ID}/locations/{GCP_LOCATION}/processors/{DOCAI_PROCESSOR_ID}"
        
        # Create the raw document
        raw_document = documentai.RawDocument(
            content=image_bytes,
            mime_type=mime_type
        )
        
        # Create the request
        request = documentai.ProcessRequest(
            name=name,
            raw_document=raw_document
        )
        
        # Log que estamos procesando el documento
        logger.info(f"Procesando documento con Document AI (mime_type: {mime_type}, bytes: {len(image_bytes)})")
        
        # Procesar el documento
        result = docai_client.process_document(request=request)
        document = result.document
        
        # Extraer texto
        text = document.text
        logger.info(f"Documento procesado con éxito. Texto extraído: {len(text)} caracteres")
        
        # Extraer entidades (campos específicos)
        entities = {}
        for entity in document.entities:
            entities[entity.type_] = entity.mention_text
            
        return {
            "success": True,
            "text": text,
            "entities": entities,
            "full_document": {
                "text": document.text,
                "pages": [{
                    "page_number": page.page_number,
                    "dimensions": {
                        "width": page.dimension.width,
                        "height": page.dimension.height
                    },
                    "layout": {
                        "text": page.layout.text,
                        "confidence": page.layout.confidence
                    }
                } for page in document.pages],
                "entities": [{
                    "type": entity.type_,
                    "mention_text": entity.mention_text,
                    "confidence": entity.confidence
                } for entity in document.entities]
            }
        }
    except Exception as e:
        logger.error(f"Error procesando documento con Document AI: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
# ------------------------------------------------------------------------
# INTEGRACIÓN CON CLOUD STORAGE
# ------------------------------------------------------------------------
def upload_to_gcs(data, destination_blob_name, content_type="application/json"):
    """
    Sube datos a Google Cloud Storage
    
    Args:
        data: Datos a subir (pueden ser bytes o string)
        destination_blob_name: Nombre del archivo en GCS (incluye path)
        content_type: Tipo MIME del contenido
        
    Returns:
        URL pública del archivo subido o None si falla
    """
    try:
        blob = bucket.blob(destination_blob_name)
        if isinstance(data, str):
            data = data.encode('utf-8')
        blob.upload_from_string(data, content_type=content_type)
        # Hacer el blob públicamente accesible (opcional)
        blob.make_public()
        logger.info(f"Archivo {destination_blob_name} subido exitosamente a GCS")
        return blob.public_url
    except Exception as e:
        logger.error(f"Error subiendo a GCS: {e}")
        return None

def save_conversation_to_cloud(wa_id, conversation_id):
    """
    Guarda toda la información de la conversación en Cloud Storage
    
    Args:
        wa_id: ID de WhatsApp del usuario
        conversation_id: ID único de la conversación
        
    Returns:
        Dict con las URLs de los archivos guardados
    """
    try:
        # Obtener datos del usuario y el historial de conversación
        user_data = get_user_data(wa_id)
        conversation_history = get_conversation_history(wa_id)
        
        if not user_data:
            logger.warning(f"No hay datos de usuario para {wa_id}")
            return None
            
        # Crear estructura de datos completa
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_str = datetime.now().strftime("%Y%m%d")
        
        save_data = {
            "metadata": {
                "wa_id": wa_id,
                "conversation_id": conversation_id,
                "timestamp": timestamp,
                "date": datetime.now().isoformat()
            },
            "user_data": user_data,
            "conversation_history": conversation_history
        }
        
        # Construir el path usando el número de teléfono y la combinación de conversation_id + fecha
        base_path = f"{wa_id}/{conversation_id}_{date_str}"
        
        # 1. Guardar JSON principal con los datos estructurados
        json_data = json.dumps(save_data, indent=2, ensure_ascii=False)
        json_path = f"{base_path}/data.json"
        json_url = upload_to_gcs(json_data, json_path)
        
        # 2. Guardar imágenes (si existen)
        image_urls = []
        if "images" in user_data:
            for idx, image_info in enumerate(user_data["images"]):
                image_bytes = download_image_bytes(image_info["url"])
                if image_bytes:
                    image_path = f"{base_path}/images/image_{idx}.jpg"
                    image_url = upload_to_gcs(image_bytes, image_path, "image/jpeg")
                    if image_url:
                        image_urls.append(image_url)
                        # Actualizar URL en el user_data para referencia futura
                        user_data["images"][idx]["gcs_url"] = image_url
        
        # 3. Guardar audios (si existen)
        audio_urls = []
        if "audio_messages" in user_data:
            for idx, audio_info in enumerate(user_data["audio_messages"]):
                if "url" in audio_info:
                    audio_bytes = download_image_bytes(audio_info["url"])
                    if audio_bytes:
                        # Asegurarse que el directorio de audios existe en Cloud Storage
                        audio_path = f"{base_path}/audios/audio_{idx}.mp3"
                        audio_url = upload_to_gcs(audio_bytes, audio_path, "audio/mpeg")
                        if audio_url:
                            audio_urls.append(audio_url)
                            # Actualizar URL en el user_data para referencia futura
                            user_data["audio_messages"][idx]["gcs_url"] = audio_url
                            
                            # Guardar la entrada en la base de datos para mostrar en el dashboard
                            with shelve.open("conversation_history", writeback=True) as history_shelf:
                                # Buscar el mensaje correspondiente y actualizarlo con la URL de audio
                                if wa_id in history_shelf:
                                    for msg in history_shelf[wa_id]:
                                        if msg.get("role") == "user" and "[🎤 Audio recibido]" in msg.get("content", ""):
                                            # Actualizar el mensaje con referencia a la URL de GCS
                                            msg["audio_url"] = audio_url
                                    # Guardar la historia actualizada
                                    history_shelf[wa_id] = history_shelf[wa_id]
        
        # Actualizar user_data con las URLs de GCS
        store_user_data(wa_id, user_data)
        
        return {
            "json_url": json_url,
            "image_urls": image_urls,
            "audio_urls": audio_urls,
            "gcs_path": f"gs://{GCS_BUCKET_NAME}/{base_path}"
        }
    except Exception as e:
        logger.error(f"Error guardando conversación en cloud: {e}")
        return None
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
# PROMPT DE SISTEMA
# ------------------------------------------------------------------------
SYSTEM_PROMPT = """Eres un asistente que permite a los usuarios capturar datos en Tiendas de Barrio o Supermercados. 
Agrega emojis para hacer más divertida la conversación de WhatsApp.

1. Lo primero que haces es un Registro de Onboarding Preguntando al usuario si ya está registrado en Kapta o no. 

1.1 Si el usuario responde que no, se le solicita la Cédula Frontal, Parte detrás, Ciudad, y Cliente en un mensaje. Agrega el estilo de un mensaje copado de WhatsApp, escribe los datos en un JSON local. 

Se le indica al usuario que cuando finalice envíe Listo como para confirmar, validar que está listo por detrás, es decir que el usuario envió la información total solicitada. 

Si se envió la información completa se avanza en el flujo, sino se le pide lo que falte al usuario. 

1.2 Si el usuario dice que ya está registrado avanzamos a: 

Para empezar, envíame el nombre de la tienda que vamos a capturar.

📝 Ejemplos: Éxito La Felicidad o Supermercado Doña Luz

Dependiendo de si el Usuario dice algo parecido a: 
Tiendas que son consideradas canal moderno:
D1
Ara
Éxito
Carulla
Alkosto
Olimpica
Sao
Jumbo
Metro
Makro
Farmatodo
Locatel

Ahí asignamos Canal Moderno y seguimos el siguiente flujo:

📍 Continuemos con la ubicación de la tienda.

Para enviarnos tu ubicación:
 1. Abre el chat.
 2. Pulsa el ícono de adjuntar "📎".
 3. Selecciona "Ubicación" y elige "Enviar mi ubicación actual".

Luego de que el usuario WhatsApp envíe la ubicación le pedimos:

📸 ¡Momento de capturar las fotos!

🔍 Lo más importante es que podamos identificar la mayor cantidad de productos posibles de forma clara.

📌 Para lograrlo, ten en cuenta:
✅ Toma la foto de frente y a la altura de los ojos.
✅ Asegúrate de que haya buena iluminación.
✅ Si hay neveras, ábrela antes de tomar la foto para evitar reflejos en el vidrio.
✅ Si hay publicidad o elementos que cubran los productos, trata de capturarlos de una forma en la que sean visibles.
✅ Si hay muchos productos, divide la sección en varias fotos para que todo quede bien registrado.

Cada detalle cuenta, empezaremos con tu categoría y agrega Listo luego de haber tomado las fotos. ¡Gracias por el esfuerzo! 🚀📷

Finalmente luego de que el usuario capturó las fotos y mandó Listo como confirmación
Enviamos el siguiente Mensaje: 

🎤 Por último, envíame un audio contándome cómo ves el desempeño de tu marca y de la competencia en esta tienda dentro de la categoría.

💡 Queremos conocer qué marcas están mejor posicionadas, cuáles tienen más visibilidad, si hay promociones atractivas o algo que pueda mejorar tu marca en esta tienda versus la competencia. ¡Tu opinión es clave para ayudar a mejorar! Envía Listo cuando hayas terminado. 

Luego de que el usuario envíe Listo, finalmente lo despedimos y guardamos un JSON que tenga toda la información del chat capturada.

# Output Format
- Responder en español conversacional con muchos emojis adecuados
- NUNCA incluir estructuras JSON o bloques de código en la respuesta visible
- Mantener mensajes concisos pero amigables y atractivos
- Usar emojis para resaltar información importante y hacer la conversación divertida

# Notas importantes
- Asegurar que cada mensaje del usuario sea reconocido con una respuesta amigable
- Validar que la información esté completa antes de pasar al siguiente paso
- Mantener interacciones amigables y atractivas durante todo el proceso
- NUNCA mostrar detalles técnicos o datos JSON al usuario
- Reemplazar {name} con el nombre del usuario y {agent_name} con "Kapta Assistant" cuando uses esas plantillas"""

# ------------------------------------------------------------------------
# LLAMAR A LA API DE OPENAI
# ------------------------------------------------------------------------
def call_openai(messages, user_name):
    """
    Llama a la API de OpenAI usando el modelo gpt-4-turbo-preview
    
    Args:
        messages: Lista de mensajes en formato de la API de OpenAI
        user_name: Nombre del usuario para personalizar respuestas
        
    Returns:
        Respuesta del asistente y datos JSON extraídos (si hay)
    """
    try:
        # Añadir información sobre el usuario al sistema prompt
        personalized_prompt = SYSTEM_PROMPT.replace("{name}", user_name).replace("{agent_name}", "Kapta Assistant")
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": personalized_prompt
                }
            ] + messages,
            temperature=0.7,
        )
        
        # Extraer respuesta
        assistant_response = response.choices[0].message.content
        
        # Verificar si hay JSON en la respuesta y extraerlo silenciosamente
        json_data = {}
        json_match = re.search(r'```json\s*(.*?)\s*```', assistant_response, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(1)
                json_data = json.loads(json_str)
                # Eliminar el JSON de la respuesta que se mostrará al usuario
                assistant_response = re.sub(r'```json\s*.*?\s*```', '', assistant_response, flags=re.DOTALL)
                logger.info("JSON extraído de la respuesta y eliminado del texto visible")
            except:
                logger.warning("Se encontró formato de JSON pero no se pudo parsear")
        
        # Limpiar cualquier otro bloque de código que pudiera haberse colado
        assistant_response = re.sub(r'```.*?```', '', assistant_response, flags=re.DOTALL)
        
        # Asegurarse de que no haya mensajes técnicos o debugging
        assistant_response = re.sub(r'\[DEBUG:.*?\]', '', assistant_response)
        assistant_response = re.sub(r'\[INTERNAL:.*?\]', '', assistant_response)
        
        # Añadir emojis si no hay suficientes
        if assistant_response.count('😊🙂😀😄😁😃🤗👋👍✅🎉🏪🛒📸📱📍🗺️🎤🔊') < 2:
            common_emojis = ['😊', '👋', '📸', '📍', '🎤', '✅', '🎉', '👍', '💯', '⭐']
            emoji_count = sum(1 for char in assistant_response if ord(char) > 127)
            if emoji_count < 2:
                if not any(ord(char) > 127 for char in assistant_response[:10]):
                    assistant_response = f"{random.choice(common_emojis)} {assistant_response}"
                if not any(ord(char) > 127 for char in assistant_response[-10:]):
                    assistant_response = f"{assistant_response} {random.choice(common_emojis)}"
        
        return assistant_response, json_data
    except Exception as e:
        logger.error(f"Error llamando a OpenAI: {e}", exc_info=True)
        return "😕 Lo siento, ocurrió un error al procesar tu solicitud. Por favor, inténtalo de nuevo más tarde. 🙏", {}

# ------------------------------------------------------------------------
# GENERAR RESPUESTA
# ------------------------------------------------------------------------
def generate_response(wa_id, name, message_type, message_content=None):
    """
    Procesa un mensaje de WhatsApp y genera una respuesta usando el modelo o1.
    Ahora incluye procesamiento de documentos y guardado en Cloud Storage.
    """
    try:
        if not OPENAI_API_KEY:
            error_msg = "😕 Error de configuración: No se puede conectar con el asistente."
            logger.error(f"No hay API key configurada para usuario {name} ({wa_id})")
            return {"text_response": error_msg, "force_script": True}
        
        # Obtener historial y datos del usuario
        conversation_history = get_conversation_history(wa_id)
        user_data = get_user_data(wa_id)
        
        # Crear un ID único para la conversación si es nueva
        if "conversation_id" not in user_data:
            user_data["conversation_id"] = str(uuid.uuid4())
            store_user_data(wa_id, user_data)
        
        if not conversation_history:
            logger.info(f"Nueva conversación para {name} ({wa_id})")
            conversation_history.append({
                "role": "system", 
                "content": f"Nueva conversación con {name}. Esta es la primera interacción del usuario."
            })
        
        user_message = ""
        docai_results = None
        
        # Procesamiento según el tipo de mensaje
        if message_type == "text":
            user_message = message_content
            logger.info(f"Mensaje de texto a procesar: {message_content[:50]}...")
            if "listo" in user_message.lower() or "terminado" in user_message.lower():
                user_data["conversation_complete"] = True
                store_user_data(wa_id, user_data)
                
        elif message_type == "image":
            image_bytes = download_image_bytes(message_content)
            if image_bytes:
                image_size = len(image_bytes) / 1024  # KB
                # Procesar con Document AI si es parte del onboarding de documento
                if user_data.get("onboarding_phase") == "document_upload":
                    docai_results = process_document_with_docai(image_bytes)
                    if docai_results["success"]:
                        user_message = "[📸 Documento de identidad procesado]"
                        if "documents" not in user_data:
                            user_data["documents"] = []
                        user_data["documents"].append({
                            "type": "identification",
                            "text": docai_results["text"],
                            "entities": docai_results["entities"],
                            "timestamp": time.time()
                        })
                        user_data["onboarding_phase"] = "document_processed"
                    else:
                        user_message = "[📸 Error al procesar documento. Por favor, inténtalo de nuevo]"
                else:
                    user_message = f"[📸 Imagen recibida ({image_size:.1f}KB)]"
                
                if "images" not in user_data:
                    user_data["images"] = []
                user_data["images"].append({
                    "timestamp": time.time(),
                    "size_kb": round(image_size, 1),
                    "url": message_content,
                    "docai_processed": bool(docai_results and docai_results["success"])
                })
                store_user_data(wa_id, user_data)
            else:
                user_message = "[📷 Error al recibir imagen]"
                logger.warning("No se pudo descargar la imagen")
                
        # En la sección de procesamiento de mensajes de audio en generate_response
        elif message_type == "audio":
            user_message = "[🎤 Audio recibido]"
            if "audio_messages" not in user_data:
                user_data["audio_messages"] = []
            
            audio_info = {
                "timestamp": time.time(),
                "url": message_content,
                "processed": False
            }
            user_data["audio_messages"].append(audio_info)
            store_user_data(wa_id, user_data)
            
            # Si ya se guardó el audio en GCS en conversaciones anteriores, usar esa URL
            audio_gcs_url = None
            for audio in user_data.get("audio_messages", []):
                if audio.get("url") == message_content and "gcs_url" in audio:
                    audio_gcs_url = audio.get("gcs_url")
                    break
            
            # Si tenemos URL de GCS, añadirla al mensaje del usuario
            if audio_gcs_url:
                user_message = f"[🎤 Audio recibido - {audio_gcs_url}]"
            
            logger.info(f"Audio recibido y referencia almacenada: {message_content}")
            
        elif message_type == "location":
            try:
                loc = json.loads(message_content) if isinstance(message_content, str) else message_content
                user_message = f"""[📍 Ubicación recibida]
Latitud: {loc.get('latitude')}
Longitud: {loc.get('longitude')}
Nombre: {loc.get('name', 'No disponible')}
Dirección: {loc.get('address', 'No disponible')}
"""
                user_data["location"] = {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                    "name": loc.get("name"),
                    "address": loc.get("address"),
                    "timestamp": time.time()
                }
                store_user_data(wa_id, user_data)
                logger.info("Ubicación almacenada")
            except Exception as e:
                logger.error(f"Error procesando ubicación: {e}")
                user_message = "[🗺️ Ubicación recibida (error al procesar detalles)]"
                
        else:
            user_message = f"[Tipo de mensaje recibido: {message_type}]"
            logger.info(f"Mensaje de tipo no estándar recibido: {message_type}")
        
        conversation_history.append({"role": "user", "content": user_message})
        
        assistant_response, json_data = call_openai(conversation_history, name)
        conversation_history.append({"role": "assistant", "content": assistant_response})
        store_conversation_history(wa_id, conversation_history)
        
        if json_data:
            if "captures" not in user_data:
                user_data["captures"] = []
            json_data["timestamp"] = time.time()
            user_data["captures"].append(json_data)
            for key, value in json_data.items():
                if key not in ["captures", "timestamp"]:
                    user_data[key] = value
            store_user_data(wa_id, user_data)
        
        # Guardar en Cloud Storage si la conversación está completa
        if user_data.get("conversation_complete"):
            conversation_id = user_data["conversation_id"]
            save_results = save_conversation_to_cloud(wa_id, conversation_id)
            if save_results:
                logger.info(f"Conversación guardada en GCS: {save_results['gcs_path']}")
                # Opcional: aquí se puede limpiar la información local si fuera necesario
        
        if len(assistant_response) > 0 and sum(1 for c in assistant_response if ord(c) > 127) < 2:
            emojis = ["😊", "👍", "👋", "🎉", "✅"]
            assistant_response = f"{random.choice(emojis)} {assistant_response}"
        
        return {
            "text_response": assistant_response,
            "force_script": True
        }
        
    except Exception as e:
        logger.error(f"Error en generate_response: {e}", exc_info=True)
        return {
            "text_response": f"😕 Lo siento {name}, ocurrió un problema. Por favor, inténtalo de nuevo más tarde. 🙏",
            "force_script": True
        }
