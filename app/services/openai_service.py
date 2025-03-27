import shelve
from flask import current_app
import logging
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os 

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


# Script content exacto del PDF
SCRIPT_CONTENT = {
    "ONBOARDING": [
        "Para comenzar con el proceso de registro necesitamos validar tus datos. Por favor me puedes enviar una foto de tu cédula (frente y reverso).",
        "Gracias, me ayudas a contestar estas preguntas porfa?\n¿Para qué cliente de Eficacia trabajas?\n¿Visitas principalmente supermercados o tiendas de barrio?"
    ],
    "CANAL_TRADICIONAL": [
        "👋Hola, {name}! Soy Pastor de Kapta. Necesito tu apoyo para tomar algunas fotos en las tiendas que visitas, deseas continuar?. 📸",
        "Para empezar, ¿me puedes por favor compartir la dirección y el nombre de la tienda donde iniciarás el registro?\n\nEjemplo:\n📌 Surtifruver Lucey\n📌 Carrera 78F #58 sur - 48, Bosa",
        "Se por Eficacia que visitas tiendas de barrio, dime con solo el número en que tipo de tienda estas: ✏️\n\n1️⃣ Tienda de barrio\nNegocio con mostrador, donde los productos no están al alcance del cliente.\n2️⃣ Supermercado de barrio\nTienda con góndolas y estanterías donde los productos están al alcance, con al menos una caja de pago.\n3️⃣ Licorera/Estanco\nEspecializada en licores, también vende gaseosas como mezclador.\n4️⃣ Panadería\nVende pan, pasteles y productos recién horneados.\n5️⃣ Farmacia\nVenta de medicamentos y productos de cuidado personal.",
        "¡Ahora ayúdame con la primera foto!📸\nToma una foto de la fachada de la tienda. Es importante que se vea el nombre y la entrada.",
        "🥃 Ahora, toma 3 fotos de la sección de bebidas alcohólicas.\nTen en cuenta que se vea bebidas como:\n✅Vodka\n✅Ginebra\n✅Whisky\n✅Tequila\n✅Ron\n✅Cerveza\n✅Aguardiente",
        "🥤 ¡Hagámoslo con las bebidas sin alcohol!\nAbre la neveras y toma 3 fotos donde se vea:\n✅Gaseosas\n✅Aguas\n✅Jugos\n✅Té helado\n✅Bebidas energéticas\n✅Bebidas hidratantes",
        "🍪Sigamos con 3 fotos de la sección de snacks.\nIncluye todos los productos disponibles en la tienda:\n✅Papas fritas\n✅Galletas\n✅Ponqués\n✅Gomas de mascar\n✅Chocolates",
        "🥚 Ahora, toma 3 fotos de la sección de huevos.\nAsegúrate de capturar toda la variedad disponible en la tienda, incluyendo:\n✅Huevos blancos y rojos\n✅Diferentes presentaciones (bandejas, por unidad, etc.)",
        "🚬 Vamos con la sección de cigarrillos y vapes.\nToma 3 fotos asegurándote de incluir:\n✅Cigarrillos de diferentes marcas\n✅Vapes y cigarrillos electrónicos (si hay disponibles)",
        "🧴 Ahora, toma 3 fotos de la sección de cuidado personal.\nIncluye productos como:\n✅Shampoo\n✅Tinte para el cabello\n✅Pañales\n✅Cuchillas de afeitar\n✅Cepillos de dientes\n✅Enjuague bucal",
        "🎤 Por último, enviame un audio respondiendo estas preguntas o algo adicional que quieras comentarme sobre el punto de venta.\n\n¿Hay espacios vacíos en los estantes?\n¿Faltan ciertas marcas o productos?\n¿Las promociones están bien visibles?\n¿Los productos están bien organizados?",
        "✅ ¡Gracias {name} por compartir toda la información! Avisame cuando ya estes en la otra tienda."
    ],
    "CANAL_MODERNO": [
        "👋Hola, {name}! Soy Pastor de Kapta. Necesito tu apoyo para tomar algunas fotos en las tiendas que visitas. 📸",
        "Para empezar, enviame la ubicación de la tienda donde iniciarás el registro. 📍\nAdemás, compártenos el nombre de la tienda.\n\nEjemplo:\n📌Éxito la felicidad\n\nPara enviarnos tu ubicación:\n1️⃣ Abre el chat.\n2️⃣ Pulsa el ícono de adjuntar 📎.\n3️⃣ Selecciona \"Ubicación\" y elige \"Enviar mi ubicación actual\".",
        "🥃 Ahora, toma 3 fotos de la sección de bebidas alcohólicas.\nTen en cuenta que se vea bebidas como:\n✅Vodka\n✅Ginebra\n✅Whisky\n✅Tequila\n✅Ron\n✅Cerveza\n✅Aguardiente",
        "🥤 ¡Hagámoslo con las bebidas sin alcohol!\nToma 3 fotos de esta sección y muestra todos los productos que existan de:\n✅Gaseosas\n✅Aguas\n✅Jugos\n✅Té helado\n✅Bebidas energéticas",
        "🍪Sigamos con 3 fotos de la sección de snacks.\nIncluye todos los productos disponibles en la tienda:\n✅Papas fritas\n✅Galletas\n✅Ponqués\n✅Gomas de mascar\n✅Chocolates",
        "🥚 Ahora, toma 3 fotos de la sección de huevos.\nAsegúrate de capturar toda la variedad disponible en la tienda, incluyendo:\n✅Huevos blancos y rojos\n✅Diferentes presentaciones (bandejas, por unidad, etc.)",
        "🚬 Vamos con la sección de cigarrillos y vapes.\nToma 3 fotos asegurándote de incluir:\n✅Cigarrillos de diferentes marcas\n✅Vapes y cigarrillos electrónicos (si hay disponibles)",
        "🧴 Ahora, toma 3 fotos de la sección de cuidado personal.\nIncluye productos como:\n✅Shampoo\n✅Tinte para el cabello\n✅Pañales\n✅Cuchillas de afeitar\n✅Cepillos de dientes\n✅Enjuague bucal",
        "🎤 Por último, enviame un audio respondiendo estas preguntas o algo adicional que quieras comentarme.\n\n¿Hay espacios vacíos en los estantes?\n¿Faltan ciertas marcas o productos?\n¿Las promociones están bien visibles?\n¿Los productos están bien organizados?",
        "✅ ¡Gracias {name} por compartir toda la información! Avísame cuando ya estés en la otra tienda."
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

# ------------------------------------------------------------------------
# CONFIGURACIÓN DE SLACK
# ------------------------------------------------------------------------
SLACK_WEBHOOK_URL = os.getenv("WEBHOOK_SLACK")

def post_to_slack_onboarding(username, phone_number, webhook_url=SLACK_WEBHOOK_URL):
    """
    Envía una notificación a Slack cuando un usuario comienza el onboarding.
    """
    try:
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        data = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 NUEVO USUARIO EN ONBOARDING 🚀",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Se ha iniciado un nuevo proceso de onboarding para un promotor de Eficacia*"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Usuario:* 👤 `{username}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Teléfono:* 📱 `{phone_number}`"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⏱️ *Estado:* Iniciando proceso de validación"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📅 Fecha y hora: {current_time}"
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            webhook_url,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            logger.error(f"Error al enviar mensaje a Slack: {response.status_code}, respuesta = {response.text}")
            return False
        
        logger.info(f"Notificación de onboarding enviada a Slack para usuario {username}")
        return True
    
    except Exception as e:
        logger.error(f"Excepción al enviar notificación de onboarding a Slack: {str(e)}")
        return False

def post_to_slack_new_store(username, phone_number, client_info, store_type, webhook_url=SLACK_WEBHOOK_URL):
    """
    Envía una notificación a Slack cuando un usuario comienza a registrar una nueva tienda.
    """
    try:
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        # Determinar el tipo de canal basado en la respuesta
        canal = "Canal Moderno" if "supermercados" in store_type.lower() else "Canal Tradicional"
        
        data = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 ¡NUEVA TIENDA EN PROCESO! 🚨",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✨ *El usuario {username} de Eficacia ha comenzado a registrar una nueva tienda* ✨"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Usuario:* 👤 `{username}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Teléfono:* 📱 `{phone_number}`"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Cliente:* 🏢 `{client_info}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Canal:* 🏪 `{canal}`"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⏱️ *Estado:* En proceso de registro"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📅 Fecha y hora: {current_time}"
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            webhook_url,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            logger.error(f"Error al enviar mensaje a Slack: {response.status_code}, respuesta = {response.text}")
            return False
        
        logger.info(f"Notificación de nueva tienda enviada a Slack para usuario {username}")
        return True
    
    except Exception as e:
        logger.error(f"Excepción al enviar notificación de nueva tienda a Slack: {str(e)}")
        return False

def post_to_slack_end_process(username, phone_number, total_time_str, webhook_url=SLACK_WEBHOOK_URL):
    """
    Envía una notificación a Slack cuando un usuario finaliza por completo el flujo.
    """
    try:
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        data = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ FIN DEL PROCESO ✅",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*El usuario {username} ha completado todo el proceso.*"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Usuario:* 👤 `{username}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Teléfono:* 📱 `{phone_number}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Tiempo total:* ⏳ `{total_time_str}`"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⏱️ *Estado:* Finalizado"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📅 Fecha y hora: {current_time}"
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            webhook_url,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            logger.error(f"Error al enviar mensaje a Slack (fin de proceso): {response.status_code}, respuesta = {response.text}")
            return False
        
        logger.info(f"Notificación de fin de proceso enviada a Slack para usuario {username}")
        return True
    
    except Exception as e:
        logger.error(f"Excepción al enviar notificación de fin de proceso a Slack: {str(e)}")
        return False

# ------------------------------------------------------------------------
# DB (shelve)
# ------------------------------------------------------------------------
def get_db():
    """Obtener la conexión a la base de datos"""
    return shelve.open("conversation_states")

def get_conversation_state(wa_id):
    """Obtener el estado de la conversación y asegurar que tenga todos los atributos necesarios"""
    with get_db() as db:
        state = db.get(wa_id, None)
        
        if state:
            updated = False
            
            # Asegurar atributos
            if not hasattr(state, 'onboarding_notified'):
                state.onboarding_notified = True
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

            if updated:
                db[wa_id] = state
                logger.info(f"Estado actualizado para {wa_id} con nuevos atributos")
                
        return state

def store_conversation_state(wa_id, state):
    """Guardar el estado de la conversación"""
    with get_db() as db:
        if not hasattr(state, 'onboarding_notified'):
            state.onboarding_notified = True
        if not hasattr(state, 'new_store_notified'):
            state.new_store_notified = False
        if not hasattr(state, 'start_time'):
            state.start_time = datetime.now()
        if not hasattr(state, 'end_notified'):
            state.end_notified = False
            
        db[wa_id] = state

def get_example_image_url(section):
    """Obtener URL de imagen de ejemplo"""
    return EXAMPLE_IMAGES.get(section, "https://example.com/images/default.jpg")

# ------------------------------------------------------------------------
# CLASE DE ESTADO
# ------------------------------------------------------------------------
class ConversationState:
    def __init__(self, wa_id, name, channel=None, current_step="ONBOARDING", step_index=0):
        self.wa_id = wa_id
        self.name = name
        self.channel = channel
        self.current_step = current_step
        self.step_index = step_index
        
        self.data = {}
        self.photo_counts = {}
        
        self.onboarding_notified = False
        self.new_store_notified = False
        
        # Para medir el tiempo total
        self.start_time = datetime.now()
        self.end_notified = False

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
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_notified': self.end_notified
        }

    @classmethod
    def from_dict(cls, data):
        state = cls(
            wa_id=data['wa_id'],
            name=data['name'],
            channel=data.get('channel'),
            current_step=data.get('current_step', 'ONBOARDING'),
            step_index=data.get('step_index', 0)
        )
        state.data = data.get('data', {})
        state.photo_counts = data.get('photo_counts', {})
        state.onboarding_notified = data.get('onboarding_notified', False)
        state.new_store_notified = data.get('new_store_notified', False)
        
        if data.get('start_time'):
            state.start_time = datetime.fromisoformat(data['start_time'])
        else:
            state.start_time = datetime.now()
        
        state.end_notified = data.get('end_notified', False)
        return state

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
        total_time_str = str(total_time).split('.')[0]  # remover microsegundos
        post_to_slack_end_process(self.name, self.wa_id, total_time_str)
        self.end_notified = True

    def advance_step(self):
        """
        Avanza al siguiente paso del script.
        Aquí forzamos la notificación final en cuanto se llega
        al último mensaje del canal (sin requerir otro mensaje del usuario).
        """
        script = self.get_current_script()
        
        # ONBOARDING completo -> cambiar a canal
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
        
        # Si aún no estamos en el último step de este script
        if self.step_index < len(script) - 1:
            self.step_index += 1
            self.photo_counts = {}
            
            # Revisar si ACABAMOS de llegar al paso final
            if self.current_step in ["CANAL_TRADICIONAL", "CANAL_MODERNO"]:
                if self.step_index == len(script) - 1 and not self.end_notified:
                    # Este es el último step => disparamos la alerta de fin
                    self.notify_end_of_flow()
        
        else:
            # Si YA estábamos en el último (por si el usuario insiste en mandar más)
            if self.current_step in ["CANAL_TRADICIONAL", "CANAL_MODERNO"]:
                if not self.end_notified:
                    self.notify_end_of_flow()

    def process_message(self, message_type, content=None):
        """
        Procesar un mensaje del usuario y ver si avanzamos en el script.
        """
        # ONBOARDING - Paso 1 (imagen de cédula)
        if self.current_step == "ONBOARDING" and self.step_index == 0:
            if message_type == "image":
                self.advance_step()
                return True
        
        # ONBOARDING - Paso 2 (texto con preguntas)
        elif self.current_step == "ONBOARDING" and self.step_index == 1:
            if message_type == "text":
                self.data['onboarding_response'] = content
                
                # Notificar nueva tienda
                if not self.new_store_notified:
                    cliente = "No especificado"
                    visita = "No especificado"
                    
                    # Extraer si se menciona "cliente"
                    if "cliente" in content.lower() and "trabajo" in content.lower():
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if "cliente" in line.lower() and (i+1) < len(lines):
                                cliente = lines[i+1].strip()
                                break

                    if "supermercados" in content.lower():
                        visita = "Principalmente supermercados"
                    elif "tiendas de barrio" in content.lower() or "tienda" in content.lower():
                        visita = "Principalmente tiendas de barrio"
                    
                    logger.info(f"Notificando NUEVA TIENDA EN PROCESO para {self.name} ({self.wa_id})")
                    post_to_slack_new_store(self.name, self.wa_id, cliente, visita)
                    self.new_store_notified = True
                
                self.advance_step()
                return True

        # CANAL TRADICIONAL
        elif self.current_step == "CANAL_TRADICIONAL":
            if self.step_index == 0:
                self.advance_step()
                return True
            elif self.step_index == 1 and message_type == "text":
                self.data['store_address'] = content
                self.advance_step()
                return True
            elif self.step_index == 2 and message_type == "text" and content.strip() in ["1","2","3","4","5"]:
                self.data['store_type'] = content.strip()
                self.advance_step()
                return True
            elif 3 <= self.step_index <= 10:
                sections = [
                    'fachada','bebidas_alcoholicas','bebidas_no_alcoholicas',
                    'snacks','huevos','cigarrillos','cuidado_personal','audio'
                ]
                section = sections[self.step_index - 3]
                
                if message_type == ("audio" if section=="audio" else "image"):
                    if section != "audio":
                        self.photo_counts[section] = self.photo_counts.get(section, 0) + 1
                        required = 1 if section == "fachada" else 3
                        
                        if self.photo_counts[section] >= required:
                            self.advance_step()
                            return True
                        return False
                    else:
                        # audio
                        self.advance_step()
                        return True

        # CANAL MODERNO
        elif self.current_step == "CANAL_MODERNO":
            if self.step_index == 0:
                self.advance_step()
                return True
            elif self.step_index == 1:
                if message_type in ("location","text"):
                    self.data['store_location'] = True
                    self.advance_step()
                    return True
            elif 2 <= self.step_index <= 8:
                sections = [
                    'bebidas_alcoholicas','bebidas_no_alcoholicas',
                    'snacks','huevos','cigarrillos','cuidado_personal','audio'
                ]
                section = sections[self.step_index - 2]
                
                if message_type == ("audio" if section=="audio" else "image"):
                    if section != "audio":
                        self.photo_counts[section] = self.photo_counts.get(section, 0) + 1
                        # Pedimos 3 fotos en canal moderno
                        if self.photo_counts[section] >= 3:
                            self.advance_step()
                            return True
                        return False
                    else:
                        # audio
                        self.advance_step()
                        return True

        return False

# ------------------------------------------------------------------------
# LÓGICA PRINCIPAL DE RESPUESTA
# ------------------------------------------------------------------------
def generate_response(wa_id, name, message_type, message_content=None):
    """
    Genera la respuesta en función del estado actual,
    y si llega al final del script (CANAL_TRADICIONAL/MODERNO),
    lanza la alerta final en el método 'advance_step()'.
    """
    try:
        # 1) Obtener o crear el estado
        state = get_conversation_state(wa_id)
        if not state:
            state = ConversationState(wa_id, name)
            logger.info(f"Enviando notificación de inicio de ONBOARDING para {name} ({wa_id})")
            post_to_slack_onboarding(name, wa_id)
            state.onboarding_notified = True
            store_conversation_state(wa_id, state)
        
        # 2) Procesar el mensaje
        try:
            state.process_message(message_type, message_content)
        except Exception as e:
            logger.error(f"Error al procesar mensaje: {e}")
        
        # 3) Obtener el texto actual del script
        response_data = {
            'text_response': state.get_current_message(),
            'force_script': True
        }
        
        # 4) Determinar si mandamos imagen de ejemplo
        if state.current_step in ["CANAL_TRADICIONAL", "CANAL_MODERNO"]:
            trad_sections = [
                'fachada','bebidas_alcoholicas','bebidas_no_alcoholicas',
                'snacks','huevos','cigarrillos','cuidado_personal'
            ]
            mod_sections = [
                'bebidas_alcoholicas','bebidas_no_alcoholicas',
                'snacks','huevos','cigarrillos','cuidado_personal'
            ]
            
            if state.current_step == "CANAL_TRADICIONAL" and 3 <= state.step_index <= 9:
                section = trad_sections[state.step_index - 3]
                response_data['image_url'] = get_example_image_url(section)
            
            elif state.current_step == "CANAL_MODERNO" and 2 <= state.step_index <= 7:
                section = mod_sections[state.step_index - 2]
                response_data['image_url'] = get_example_image_url(section)

        # 5) Guardar estado
        store_conversation_state(wa_id, state)
        
        return response_data
    
    except Exception as e:
        logger.error(f"Error crítico en generate_response: {str(e)}")
        return {
            'text_response': f"Hola {name}, estamos experimentando problemas técnicos. Por favor, intenta más tarde.",
            'force_script': True
        }
