import logging
from flask import Blueprint, request, jsonify, current_app
from app.utils.whatsapp_utils import process_whatsapp_message

bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

@bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    Endpoint para recibir webhooks de WhatsApp.
    
    GET: Se usa para la verificación del webhook.
    POST: Se usa para recibir mensajes.
    """
    if request.method == 'GET':
        # Manejar verificación del webhook
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        # Obtener el token de verificación de la configuración
        verify_token = current_app.config.get('VERIFY_TOKEN', 'Harmony2025')
        
        logger.info(f"Verificación de webhook: mode={mode}, token={token}")
        
        if mode and token:
            if mode == 'subscribe' and token == verify_token:
                logger.info('Verificación de webhook exitosa')
                return challenge, 200
            else:
                logger.warning(f'Verificación de webhook fallida: token esperado={verify_token}, recibido={token}')
                return "Token o modo incorrecto", 403
        
        return "OK", 200
    
    elif request.method == 'POST':
        # Manejar mensajes entrantes
        try:
            body = request.json
            logger.info(f"Webhook recibido: {body}")
            
            # Si es un webhook de status update, solo devolver OK
            if body.get("object") == "whatsapp_business_account" and not body.get("entry")[0].get("changes")[0].get("value").get("messages"):
                logger.info("Status update recibido, sin mensajes para procesar")
                return jsonify({"status": "success"}), 200
            
            # Procesar mensaje de WhatsApp
            return process_whatsapp_message(body)
            
        except Exception as e:
            logger.error(f'Error al procesar webhook: {e}')
            return jsonify({"status": "error", "message": str(e)}), 500
    
    return jsonify({"status": "error", "message": "Método no soportado"}), 405