import logging
from flask import current_app, jsonify
import json
import requests
import re
from app.services.openai_service import generate_response

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
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"
    
    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logging.error(f"Error sending message: {e}")
        return None

def process_text_for_whatsapp(text):
    """Formatear texto para WhatsApp"""
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)  # Convertir **texto** a *texto*
    text = re.sub(r"【.*?】", "", text)  # Eliminar texto entre 【】
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
    elif message_type == "image":
        message_content = "[Image sent]"
        if "caption" in message["image"]:
            message_content += f" Caption: {message['image']['caption']}"
    elif message_type == "audio":
        message_content = "[Audio message sent]"
    elif message_type == "location":
        message_content = "[Location shared]"
    else:
        message_content = "[Unsupported message type]"
    
    # Obtener respuesta basada en el script
    response = generate_response(wa_id, name, message_type, message_content)
    
    # Enviar respuesta de texto
    if "text_response" in response and response["text_response"]:
        text_response = process_text_for_whatsapp(response["text_response"])
        data = get_text_message_input(wa_id, text_response)
        send_message(data)
    
    # Enviar imagen de ejemplo si es necesario
    if "image_url" in response:
        image_data = get_image_message_input(wa_id, response["image_url"])
        send_message(image_data)
    
    return jsonify({"status": "success"}), 200