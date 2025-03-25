import shelve
from flask import current_app
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Script content exacto del PDF
SCRIPT_CONTENT = {
    "ONBOARDING": [
        "Hola, {name} te saludamos de Eficacia. Para comenzar con el proceso de registro necesitamos validar tus datos. Por favor me puedes enviar una foto de tu cédula (frente y reverso).",
        "Gracias, me ayudas a contestar estas preguntas porfa?\n¿Para qué cliente de Eficacia trabajas?\n¿Visitas principalmente supermercados o tiendas de barrio?"
    ],
    "CANAL_TRADICIONAL": [
        "👋Hola, {name}! Soy Pastor de Kapta. Necesito tu apoyo para tomar algunas fotos en las tiendas que visitas. 📸",
        "Para empezar, ¿me puedes por favor compartir la dirección y el nombre de la tienda donde iniciarás el registro?\n\nEjemplo:\n📌 Surtifruver Lucey\n📌 Carrera 78F #58 sur - 48, Bosa",
        "Se por Eficacia que visitas tiendas de barrio, dime con solo el número en que tipo de tienda estas: ✏️\n\n1️⃣ Tienda de barrio\nNegocio con mostrador, donde los productos no están al alcance del cliente.\n2️⃣ Supermercado de barrio\nTienda con góndolas y estanterías donde los productos están al alcance, con al menos una caja de pago.\n3️⃣ Licorera/Estanco\nEspecializada en licores, también vende gaseosas como mezclador.\n4️⃣ Panadería\nVende pan, pasteles y productos recién horneados.\n5️⃣ Farmacia\nVenta de medicamentos y productos de cuidado personal.",
        "¡Ahora ayúdame con la primera foto!📸\nToma una foto de la fachada de la tienda. Es importante que se vea el nombre y la entrada.",
        "🥃 Ahora, toma 3 fotos de la sección de bebidas alcohólicas.\nTen en cuenta que se vea bebidas como:\n✅Vodka\n✅Ginebra\n✅Whisky\n✅Tequila\n✅Ron\n✅Cerveza\n✅Aguardiente",
        "🥤 ¡Hagámoslo con las bebidas sin alcohol!\nAbre la neveras y toma 3 fotos donde se vea:\n✅Gaseosas\n✅Aguas\n✅Jugos\n✅Té helado\n✅Bebidas energéticas\n✅Bebidas hidratantes",
        "🍪Sigamos con 3 fotos de la sección de snacks.\nIncluye todos los productos disponibles en la tienda:\n✅Papas fritas\n✅Galletas\n✅Ponqués\n✅Gomas de mascar\n✅Chocolates",
        "🥚 Ahora, toma 3 fotos de la sección de huevos.\nAsegúrate de capturar toda la variedad disponible en la tienda, incluyendo:\n✅Huevos blancos y rojos\n✅Diferentes presentaciones (bandejas, por unidad, etc.)",
        "🚬 Vamos con la sección de cigarrillos y vapes.\nToma 3 fotos asegurándote de incluir:\n✅Cigarrillos de diferentes marcas\n✅Vapes y cigarrillos electrónicos (si hay disponibles),
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

def get_db():
    """Obtener la conexión a la base de datos"""
    return shelve.open("conversation_states")

def get_conversation_state(wa_id):
    """Obtener el estado de la conversación"""
    with get_db() as db:
        return db.get(wa_id, None)

def store_conversation_state(wa_id, state):
    """Guardar el estado de la conversación"""
    with get_db() as db:
        db[wa_id] = state

def get_example_image_url(section):
    """Obtener URL de imagen de ejemplo"""
    return EXAMPLE_IMAGES.get(section, "https://example.com/images/default.jpg")

class ConversationState:
    def __init__(self, wa_id, name, channel=None, current_step="ONBOARDING", step_index=0):
        self.wa_id = wa_id
        self.name = name
        self.channel = channel
        self.current_step = current_step
        self.step_index = step_index
        self.data = {}  # Datos recolectados
        self.photo_counts = {}  # Conteo de fotos por sección

    def to_dict(self):
        """Convertir a diccionario para almacenamiento"""
        return {
            'wa_id': self.wa_id,
            'name': self.name,
            'channel': self.channel,
            'current_step': self.current_step,
            'step_index': self.step_index,
            'data': self.data,
            'photo_counts': self.photo_counts
        }

    @classmethod
    def from_dict(cls, data):
        """Crear desde diccionario"""
        return cls(
            wa_id=data['wa_id'],
            name=data['name'],
            channel=data.get('channel'),
            current_step=data.get('current_step', 'ONBOARDING'),
            step_index=data.get('step_index', 0)
        )

    def get_current_script(self):
        """Obtener el script actual"""
        return SCRIPT_CONTENT.get(self.current_step, [])

    def get_current_message(self):
        """Obtener el mensaje actual del script"""
        script = self.get_current_script()
        if self.step_index < len(script):
            return script[self.step_index].format(name=self.name)
        return None

    def advance_step(self):
        """Avanzar al siguiente paso del script"""
        script = self.get_current_script()
        
        # ONBOARDING completo -> determinar canal
        if self.current_step == "ONBOARDING" and self.step_index == 1:
            user_response = self.data.get('onboarding_response', '').lower()
            self.channel = "CANAL_MODERNO" if "supermercados" in user_response else "CANAL_TRADICIONAL"
            self.current_step = self.channel
            self.step_index = 0
            self.photo_counts = {}
        # Avanzar normalmente
        elif self.step_index < len(script) - 1:
            self.step_index += 1
            self.photo_counts = {}  # Resetear contador de fotos

    def process_message(self, message_type, content=None):
        """Procesar un nuevo mensaje del usuario"""
        # ONBOARDING: Paso 1 - Foto de cédula
        if self.current_step == "ONBOARDING" and self.step_index == 0:
            if message_type == "image":
                self.advance_step()
                return True
        
        # ONBOARDING: Paso 2 - Preguntas
        elif self.current_step == "ONBOARDING" and self.step_index == 1:
            if message_type == "text":
                self.data['onboarding_response'] = content
                self.advance_step()
                return True
        
        # CANAL TRADICIONAL
        elif self.current_step == "CANAL_TRADICIONAL":
            # Paso 1: Presentación (no necesita respuesta)
            if self.step_index == 0:
                self.advance_step()
                return True
            
            # Paso 2: Dirección y nombre
            elif self.step_index == 1 and message_type == "text":
                self.data['store_address'] = content
                self.advance_step()
                return True
            
            # Paso 3: Tipo de tienda
            elif self.step_index == 2 and message_type == "text" and content.strip() in ["1", "2", "3", "4", "5"]:
                self.data['store_type'] = content.strip()
                self.advance_step()
                return True
            
            # Pasos 4-10: Fotos (4-9) y audio (10)
            elif 3 <= self.step_index <= 10:
                section = [
                    'fachada', 'bebidas_alcoholicas', 'bebidas_no_alcoholicas',
                    'snacks', 'huevos', 'cigarrillos', 'cuidado_personal', 'audio'
                ][self.step_index - 3]
                
                if message_type == ("audio" if section == "audio" else "image"):
                    if section != "audio":
                        self.photo_counts[section] = self.photo_counts.get(section, 0) + 1
                        required = 1 if section == "fachada" else 3
                        if self.photo_counts[section] >= required:
                            self.advance_step()
                            return True
                        return False
                    else:
                        self.advance_step()
                        return True
        
        # CANAL MODERNO
        elif self.current_step == "CANAL_MODERNO":
            # Paso 1: Presentación (no necesita respuesta)
            if self.step_index == 0:
                self.advance_step()
                return True
            
            # Paso 2: Ubicación
            elif self.step_index == 1 and message_type == "location":
                self.data['store_location'] = True
                self.advance_step()
                return True
            
            # Pasos 3-9: Fotos (3-8) y audio (9)
            elif 2 <= self.step_index <= 8:
                section = [
                    'bebidas_alcoholicas', 'bebidas_no_alcoholicas',
                    'snacks', 'huevos', 'cigarrillos', 'cuidado_personal', 'audio'
                ][self.step_index - 2]
                
                if message_type == ("audio" if section == "audio" else "image"):
                    if section != "audio":
                        self.photo_counts[section] = self.photo_counts.get(section, 0) + 1
                        if self.photo_counts[section] >= 3:
                            self.advance_step()
                            return True
                        return False
                    else:
                        self.advance_step()
                        return True
        
        return False

def generate_response(wa_id, name, message_type, message_content=None):
    """Generar respuesta basada en el estado actual"""
    state = get_conversation_state(wa_id)
    
    # Si no existe estado, crear uno nuevo
    if not state:
        state = ConversationState(wa_id, name)
        store_conversation_state(wa_id, state)
    
    # Procesar el mensaje del usuario
    should_advance = state.process_message(message_type, message_content)
    
    # Obtener respuesta del script
    response = {
        'text_response': state.get_current_message(),
        'force_script': True
    }
    
    # Determinar si necesitamos enviar imagen de ejemplo
    if state.current_step in ["CANAL_TRADICIONAL", "CANAL_MODERNO"]:
        trad_sections = ['fachada', 'bebidas_alcoholicas', 'bebidas_no_alcoholicas', 
                        'snacks', 'huevos', 'cigarrillos', 'cuidado_personal']
        mod_sections = ['bebidas_alcoholicas', 'bebidas_no_alcoholicas', 
                       'snacks', 'huevos', 'cigarrillos', 'cuidado_personal']
        
        if (state.current_step == "CANAL_TRADICIONAL" and 3 <= state.step_index <= 9) or \
           (state.current_step == "CANAL_MODERNO" and 2 <= state.step_index <= 7):
            section = trad_sections[state.step_index - 3] if state.current_step == "CANAL_TRADICIONAL" else mod_sections[state.step_index - 2]
            response['image_url'] = get_example_image_url(section)
    
    # Guardar estado actualizado
    store_conversation_state(wa_id, state)
    
    return response