# Archivo: whatsapp_handler.py
import logging
from flask import current_app, jsonify
import json
import requests
import re
import os
import uuid
import time
from app.services.openai_service import generate_response

# Importar MessageHandler para registrar mensajes en el dashboard
from app.utils.message_handler import MessageHandler
from app.utils.image_proxy import ImageProxy

# Inicializar el MessageHandler y el ImageProxy
message_handler = MessageHandler()
image_proxy = ImageProxy()

def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")

def get_text_message_input(recipient, text):
    return json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text}
    })

def get_image_message_input(recipient, image_url):
    return json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "image",
        "image": {"link": image_url}
    })

def send_message(data):
    """
    Envía un mensaje a WhatsApp.
    Verifica que los parámetros necesarios estén configurados.
    """
    phone_number_id = current_app.config.get('PHONE_NUMBER_ID')
    version = current_app.config.get('VERSION')
    access_token = current_app.config.get('ACCESS_TOKEN')
    
    # Verificar que tenemos todos los parámetros necesarios
    if not phone_number_id:
        logging.error("Error: PHONE_NUMBER_ID no está configurado")
        return None
    
    if not version:
        version = 'v17.0'  # Valor por defecto
    
    if not access_token:
        logging.error("Error: ACCESS_TOKEN no está configurado")
        return None
    
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    
    url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
    
    try:
        logging.info(f"Enviando mensaje a: {url}")
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logging.error(f"Error sending message: {e}")
        return None

def process_text_for_whatsapp(text):
    """Formatear texto para WhatsApp"""
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    text = re.sub(r"【.*?】", "", text)
    return text.strip()

def determine_message_type(message):
    """Determinar tipo de mensaje recibido"""
    if "text" in message:
        return "text"
    elif "image" in message:
        return "image"
    elif "audio" in message:
        return "audio"
    elif "location" in message:
        return "location"
    else:
        return "unknown"

def is_valid_whatsapp_message(body):
    """Validar estructura del mensaje"""
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )

def get_media_url(media_id):
    """
    Obtener la URL real de la imagen a partir del media_id
    usando la API de Facebook/WhatsApp.
    """
    phone_number_id = current_app.config.get('PHONE_NUMBER_ID')
    version = current_app.config.get('VERSION', 'v17.0')
    access_token = current_app.config.get('ACCESS_TOKEN')
    
    # Verificar que tenemos los parámetros necesarios
    if not access_token:
        logging.error("Error: ACCESS_TOKEN no está configurado")
        return None
    
    url = f"https://graph.facebook.com/{version}/{media_id}"
    params = {'access_token': access_token}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Respuesta de Graph API para media_id={media_id}: {data}")
        
        # La URL directa del medio está en el campo 'url'
        return data.get('url')
    except Exception as e:
        logging.error(f"Error fetching media URL: {e}")
        return None

def process_whatsapp_message(body):
    """Procesar mensaje entrante de WhatsApp"""
    if not is_valid_whatsapp_message(body):
        return jsonify({"status": "error", "message": "Invalid WhatsApp message"}), 400

    # Extraer información básica del mensaje
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_type = determine_message_type(message)
    
    # Construir contenido del mensaje según el tipo
    message_content = None
    
    if message_type == "text":
        message_content = message["text"]["body"]
        # Registrar mensaje en el dashboard - CORREGIDO: usar phone_number en lugar de wa_id
        message_handler.add_message(phone_number=wa_id, message=message_content, is_bot=False)

    elif message_type == "image":
        media_id = message["image"].get("id")
        logging.info(f"ID de imagen recibido: {media_id}")
        
        # Obtener URL de la imagen
        original_media_url = get_media_url(media_id) if media_id else None
        
        if original_media_url:
            logging.info(f"URL de imagen obtenida: {original_media_url}")
            
            # Usar el ImageProxy para procesar la imagen
            image_results = image_proxy.process_whatsapp_image(
                url=original_media_url,
                access_token=current_app.config.get('ACCESS_TOKEN')
            )
            
            # Determinar la mejor URL para guardar
            best_url = image_results.get('data_url') or original_media_url
            
            # Registrar mensaje con la URL procesada - CORREGIDO: usar phone_number en lugar de wa_id
            message_handler.add_message(
                phone_number=wa_id, 
                message="[IMAGEN]", 
                is_bot=False, 
                media_url=best_url
            )
            message_content = original_media_url
            
            # Log info about the processed image
            logging.info(f"Imagen procesada: Local path: {image_results.get('local_path')}")
        else:
            logging.error("No se pudo obtener la URL de la imagen")
            message_content = "[Image sent]"
            # Registrar mensaje sin URL - CORREGIDO: usar phone_number en lugar de wa_id
            message_handler.add_message(phone_number=wa_id, message="[IMAGEN - URL no disponible]", is_bot=False)
            
        if "caption" in message["image"]:
            caption = message["image"]["caption"]
            logging.info(f"Image caption: {caption}")
            # Registrar el caption en el dashboard si existe - CORREGIDO
            message_handler.add_message(phone_number=wa_id, message=f"[CAPTION] {caption}", is_bot=False)

    elif message_type == "audio":
        message_content = "[Audio message sent]"
        # Registrar mensaje en el dashboard - CORREGIDO
        message_handler.add_message(phone_number=wa_id, message="[AUDIO]", is_bot=False)

    elif message_type == "location":
        # Extraer los datos de ubicación del mensaje
        loc = message.get("location", {})
        message_content = {
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "name": loc.get("name", ""),
            "address": loc.get("address", "")
        }
        # Registrar mensaje en el dashboard - CORREGIDO
        location_str = f"[UBICACIÓN: Lat {loc.get('latitude')}, Lng {loc.get('longitude')}]"
        message_handler.add_message(phone_number=wa_id, message=location_str, is_bot=False)
    else:
        message_content = "[Unsupported message type]"
        # Registrar mensaje en el dashboard - CORREGIDO
        message_handler.add_message(phone_number=wa_id, message="[MENSAJE NO SOPORTADO]", is_bot=False)
    
    # Verificar si el bot debe responder
    if not message_handler.should_bot_respond(wa_id):
        logging.info(f"Bot desactivado para {wa_id}. No se procesará el mensaje.")
        return jsonify({"status": "success", "message": "Bot is inactive"}), 200
    
    # Obtener respuesta basada en el script/servicio
    response = generate_response(wa_id, name, message_type, message_content)
    
    # Enviar respuesta de texto (si existe)
    if "text_response" in response and response["text_response"]:
        text_response = process_text_for_whatsapp(response["text_response"])
        data = get_text_message_input(wa_id, text_response)
        send_message(data)
        # Registrar respuesta en el dashboard - CORREGIDO
        message_handler.add_message(phone_number=wa_id, message=text_response, is_bot=True)
    
    # Enviar imagen de ejemplo si es necesario
    if "image_url" in response:
        image_url = response["image_url"]
        image_data = get_image_message_input(wa_id, image_url)
        send_message(image_data)
        # Registrar envío de imagen en el dashboard - CORREGIDO
        message_handler.add_message(phone_number=wa_id, message="[IMAGEN ENVIADA]", is_bot=True, media_url=image_url)
    
    return jsonify({"status": "success"}), 200