import streamlit as st
import pandas as pd
import time
import json
import os
import sqlite3
from datetime import datetime
import base64
import requests
from PIL import Image
from io import BytesIO
import logging
from dotenv import load_dotenv
import re
# 1. PRIMERO: Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2. SEGUNDO: Cargar variables de entorno
load_dotenv()
WHATSAPP_ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v22.0")

# 3. TERCERO: Verificar que las variables necesarias estén disponibles
if WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
    logger.info("Configuración de WhatsApp cargada correctamente")
else:
    logger.warning("Faltan variables de entorno para WhatsApp. Verificar archivo .env")
    missing = []
    if not WHATSAPP_ACCESS_TOKEN:
        missing.append("ACCESS_TOKEN")
    if not WHATSAPP_PHONE_NUMBER_ID:
        missing.append("PHONE_NUMBER_ID")
    logger.warning(f"Variables faltantes: {', '.join(missing)}")

# Asegurarse de que los directorios necesarios existen
app_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(app_dir, "static")
whatsapp_images_dir = os.path.join(static_dir, "whatsapp_images")

for directory in [static_dir, whatsapp_images_dir]:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"Directorio asegurado: {directory}")

# Configuración de la página
st.set_page_config(
    page_title="WhatsApp Bot Dashboard",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None,
)

# Estilo CSS personalizado con colores más suaves
st.markdown("""
<style>
    /* Variables de colores suaves */
    :root {
        --harmony-primary: #8C9EFF;    /* Azul lavanda suave */
        --harmony-secondary: #B0BEC5;  /* Gris azulado */
        --harmony-accent: #78909C;     /* Gris azul medio */
        --harmony-gradient: linear-gradient(135deg, #8C9EFF, #90CAF9, #A5D6A7);
        --harmony-light: #F8F9FA;      /* Gris muy claro */
        --harmony-dark: #546E7A;       /* Gris azulado oscuro */
        --harmony-success: #81C784;    /* Verde menta */
        --harmony-warning: #FFD54F;    /* Amarillo suave */
        --harmony-error: #EF9A9A;      /* Rojo suave */
        --harmony-text-dark: #37474F;  /* Texto gris oscuro */
        --harmony-text-light: #FFFFFF; /* Texto claro */
        --harmony-card-bg: #FFFFFF;    /* Fondo de tarjetas */
        --harmony-bg: #F5F7FA;         /* Fondo general suave */
    }
    
    /* Estilos generales y de página */
    .main-header {
        font-size: 2.5rem;
        color: var(--harmony-primary);
        text-align: center;
        margin-bottom: 25px;
        font-weight: 700;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Logo de Harmony */
    .harmony-logo {
        display: block;
        text-align: center;
        margin: 10px auto 20px auto;
    }
    
    .harmony-logo-image {
        height: 55px;
        filter: drop-shadow(0px 1px 2px rgba(0,0,0,0.1));
    }
    
    /* Fondo general */
    .stApp {
        background-color: var(--harmony-bg);
    }
    
    /* Panel lateral y controles */
    .stSelectbox label, .stButton, .stForm {
        margin-bottom: 15px;
    }
    
    .stSelectbox > div > div {
        background-color: var(--harmony-light);
        border-radius: 12px;
        border: 1px solid var(--harmony-secondary);
    }
    
    /* Contenedor de chat mejorado */
    .chat-container {
        border: none;
        border-radius: 16px;
        padding: 18px;
        height: auto;
        max-height: 450px;
        min-height: 300px;
        overflow-y: auto;
        background-color: var(--harmony-light);
        margin-bottom: 18px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.07);
        scrollbar-width: thin;
    }
    
    .chat-container::-webkit-scrollbar {
        width: 5px;
    }
    
    .chat-container::-webkit-scrollbar-thumb {
        background-color: var(--harmony-secondary);
        border-radius: 10px;
    }
    
    /* Estilos de mensajes mejorados */
    .user-message {
        background-color: #BBDEFB; /* Azul muy suave */
        color: var(--harmony-text-dark);
        padding: 12px 16px;
        border-radius: 16px 0px 16px 16px;
        margin: 12px 0;
        max-width: 85%;
        align-self: flex-end;
        margin-left: auto;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        word-wrap: break-word;
        display: block;
        animation: fadeIn 0.3s ease;
        border-top: 1px solid rgba(255, 255, 255, 0.5);
    }
    
    .bot-message {
        background-color: white;
        color: var(--harmony-text-dark);
        padding: 12px 16px;
        border-radius: 0px 16px 16px 16px;
        margin: 12px 0;
        max-width: 85%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        word-wrap: break-word;
        display: block;
        animation: fadeIn 0.3s ease;
        border-left: 3px solid #8C9EFF;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .time-stamp {
        font-size: 0.7rem;
        color: rgba(84,110,122,0.6);
        display: block;
        margin-top: 5px;
        text-align: right;
    }
    
    /* Estados */
    .status-active {
        color: var(--harmony-success);
        font-weight: 600;
        background-color: rgba(129, 199, 132, 0.12);
        padding: 6px 12px;
        border-radius: 30px;
        display: inline-block;
    }
    
    .status-inactive {
        color: var(--harmony-text-dark);
        font-weight: 600;
        background-color: rgba(176, 190, 197, 0.15);
        padding: 6px 12px;
        border-radius: 30px;
        display: inline-block;
    }
    
    .sender-name {
        font-weight: 600;
        margin-bottom: 5px;
        color: var(--harmony-dark);
        font-size: 0.85rem;
    }
    
    /* Botones mejorados con colores suaves */
    .stButton>button {
        background-color: #BBDEFB; /* Azul muy suave */
        color: var(--harmony-dark);
        font-weight: 600;
        border: none;
        padding: 10px 18px;
        border-radius: 30px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .stButton>button:hover {
        background-color: #90CAF9; /* Azul suave al hover */
        box-shadow: 0 3px 8px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    
    .stButton>button:active {
        transform: translateY(1px);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Contenedores de mensajes */
    .user-message-container {
        display: flex;
        justify-content: flex-end;
        width: 100%;
        padding: 2px 0;
    }
    
    .bot-message-container {
        display: flex;
        justify-content: flex-start;
        width: 100%;
        padding: 2px 0;
    }
    
    /* Área de texto mejorada */
    .stTextArea textarea {
        background-color: white;
        color: var(--harmony-text-dark);
        border: 1px solid #CFD8DC;
        border-radius: 12px;
        padding: 12px;
        transition: all 0.2s ease;
        font-size: 15px;
    }
    
    .stTextArea textarea:focus {
        border-color: var(--harmony-primary);
        box-shadow: 0 0 0 2px rgba(140, 158, 255, 0.15);
    }
    
    /* Imágenes en chat */
    .chat-image {
        max-width: 250px;
        max-height: 250px;
        border-radius: 10px;
        margin-top: 10px;
        margin-bottom: 10px;
        display: block;
        box-shadow: 0 2px 5px rgba(0,0,0,0.08);
        transition: transform 0.2s ease;
        border: 2px solid white;
    }
    
    .chat-image:hover {
        transform: scale(1.03);
    }
    
    .image-container {
        width: 100%;
        text-align: center;
        margin: 12px 0;
        background-color: white;
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 1px 5px rgba(0,0,0,0.05);
        border: 1px solid #E0E0E0;
    }
    
    /* Paneles y tarjetas */
    .card {
        background-color: var(--harmony-card-bg);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-bottom: 20px;
        transition: all 0.2s ease;
        border-top: 3px solid var(--harmony-primary);
    }
    
    .card:hover {
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    
    .card h3 {
        color: var(--harmony-dark);
        border-bottom: 1px solid rgba(207, 216, 220, 0.5);
        padding-bottom: 8px;
        margin-bottom: 12px;
        font-weight: 600;
    }
    
    /* Separadores */
    hr {
        border: 0;
        height: 1px;
        background-color: #E0E0E0;
        margin: 25px 0;
    }
    
    /* Pie de página */
    .footer-note {
        font-size: 0.85rem;
        color: var(--harmony-text-dark);
        background-color: rgba(140, 158, 255, 0.08);
        padding: 12px 16px;
        border-radius: 12px;
        border-left: 3px solid var(--harmony-primary);
        margin-top: 20px;
    }
    
    /* Encabezados de sección */
    .section-header {
        color: var(--harmony-dark);
        font-size: 1.3rem;
        margin-bottom: 16px;
        font-weight: 600;
    }
    
    /* Insignias y decoraciones */
    .harmony-badge {
        display: inline-block;
        background-color: rgba(140, 158, 255, 0.15);
        color: var(--harmony-primary);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-left: 8px;
        vertical-align: middle;
    }
    
    /* Eliminar espacios vacíos */
    div:empty {
        display: none;
    }
    
    /* Estilo para tabla de depuración */
    .debug-table {
        font-size: 0.85rem;
        border-collapse: collapse;
        width: 100%;
    }
    
    .debug-table th {
        background-color: rgba(140, 158, 255, 0.1);
        padding: 8px;
        text-align: left;
        border-bottom: 2px solid rgba(140, 158, 255, 0.2);
    }
    
    .debug-table td {
        padding: 6px 8px;
        border-bottom: 1px solid #E0E0E0;
    }
    
    .debug-table tr:hover {
        background-color: rgba(240, 240, 240, 0.5);
    }
    
    /* Mejorar apariencia de dataframes */
    .dataframe {
        font-size: 0.85rem !important;
    }
    
    .dataframe th {
        background-color: rgba(140, 158, 255, 0.1) !important;
        color: var(--harmony-dark) !important;
    }
    
    .dataframe td {
        background-color: white !important;
    }
            /* Estilo para reproductor de audio */
    .audio-container {
        width: 100%;
        padding: 10px;
        margin: 10px 0;
        background-color: rgba(240, 240, 240, 0.5);
        border-radius: 8px;
        border: 1px solid #E0E0E0;
        text-align: center;
    }

    .audio-player {
        width: 100%;
        max-width: 300px;
        height: 40px;
        border-radius: 20px;
        background-color: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }

    .audio-player:focus {
        outline: none;
        box-shadow: 0 0 0 2px rgba(140, 158, 255, 0.3);
    }   
</style>
""", unsafe_allow_html=True)

# Clase para gestionar la base de datos
class DatabaseManager:
    def __init__(self, db_path="whatsapp_conversations.db"):
        self.db_path = db_path
        self.init_db()
    
    def add_message_with_media(self, phone_number, message, is_bot=True, media_url=None, media_type=None):
        """Añade un mensaje con referencia a archivo multimedia (imagen o audio)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Verificar si existe la columna media_type
        c.execute("PRAGMA table_info(conversations)")
        columns = [info[1] for info in c.fetchall()]
        
        if 'media_type' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN media_type TEXT")
            
        c.execute(
            "INSERT INTO conversations (phone_number, message, timestamp, is_bot, media_url, media_type) VALUES (?, ?, ?, ?, ?, ?)",
            (phone_number, message, datetime.now().isoformat(), is_bot, media_url, media_type)
        )
        conn.commit()
        conn.close()

        
    def init_db(self):
        # Verificar si la base de datos existe
        db_exists = os.path.exists(self.db_path)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Tabla para conversaciones
        c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT,
            message TEXT,
            timestamp TEXT,
            is_bot BOOLEAN,
            is_read BOOLEAN DEFAULT FALSE,
            media_url TEXT
        )
        ''')
        
        # Tabla para estado del bot
        c.execute('''
        CREATE TABLE IF NOT EXISTS bot_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            is_active BOOLEAN,
            last_updated TEXT
        )
        ''')
        
        # Verificar si existe un registro en bot_status
        c.execute("SELECT COUNT(*) FROM bot_status")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO bot_status VALUES (1, 1, ?)", (datetime.now().isoformat(),))
        
        # Añadir columna media_url si no existe
        c.execute("PRAGMA table_info(conversations)")
        columns = [info[1] for info in c.fetchall()]
        if 'media_url' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN media_url TEXT")
        
        conn.commit()
        conn.close()
    
    def add_message(self, phone_number, message, is_bot=True, media_url=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO conversations (phone_number, message, timestamp, is_bot, media_url) VALUES (?, ?, ?, ?, ?)",
            (phone_number, message, datetime.now().isoformat(), is_bot, media_url)
        )
        conn.commit()
        conn.close()
    
    def get_conversations(self, phone_number=None, limit=100):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if phone_number:
            c.execute(
                "SELECT * FROM conversations WHERE phone_number = ? ORDER BY timestamp ASC LIMIT ?",
                (phone_number, limit)
            )
        else:
            c.execute(
                "SELECT * FROM conversations ORDER BY timestamp ASC LIMIT ?",
                (limit,)
            )
        
        result = [dict(row) for row in c.fetchall()]
        conn.close()
        return result
    
    def get_unique_numbers(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT DISTINCT phone_number FROM conversations")
        result = [row[0] for row in c.fetchall()]
        conn.close()
        return result
    
    def toggle_bot_status(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT is_active FROM bot_status WHERE id = 1")
        current_status = c.fetchone()[0]
        new_status = not current_status
        c.execute("UPDATE bot_status SET is_active = ?, last_updated = ? WHERE id = 1", (new_status, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return new_status
    
    def get_bot_status(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT is_active, last_updated FROM bot_status WHERE id = 1")
        result = c.fetchone()
        conn.close()
        return {"is_active": result[0], "last_updated": result[1]}
    
    def send_message(self, phone_number, message):
        """Envía un mensaje a WhatsApp y lo registra en la base de datos"""
        
        # Intentar enviar el mensaje a WhatsApp
        success, response = send_whatsapp_message(phone_number, message)
        
        # Registrar el mensaje en la base de datos local
        self.add_message(phone_number, message, is_bot=False)
        
        # Registrar el resultado para depuración
        if success:
            logger.info(f"Mensaje enviado con éxito a {phone_number}")
        else:
            logger.warning(f"No se pudo enviar el mensaje a WhatsApp: {response}")
        
        return success

# Funciones para manejar imágenes
def is_data_url(url):
    """Verifica si la URL es un data URL (base64)"""
    return url and isinstance(url, str) and url.startswith('data:')

def is_lookaside_url(url):
    """Verifica si la URL es de lookaside.fbsbx.com"""
    return url and isinstance(url, str) and 'lookaside.fbsbx.com' in url

def is_gcs_url(url):
    """Verifica si la URL es de Google Cloud Storage"""
    return url and isinstance(url, str) and ('storage.googleapis.com' in url or 'storage.cloud.google.com' in url)

# Añadir esta función al archivo de dashboard para manejar los audios
def is_audio_url(url):
    """Verifica si la URL es de un archivo de audio"""
    return url and isinstance(url, str) and (url.endswith('.mp3') or url.endswith('.ogg') or url.endswith('.wav') or 'audio' in url.lower())

def create_audio_tag(url):
    """Crear tag HTML para mostrar un reproductor de audio"""
    if not url:
        return ""
        
    if is_gcs_url(url):
        # Es una URL de GCS, debería ser accesible directamente
        return f'''
        <div class="audio-container">
            <audio controls class="audio-player">
                <source src="{url}" type="audio/mpeg">
                Tu navegador no soporta el elemento de audio.
            </audio>
        </div>
        '''
    elif is_lookaside_url(url):
        # Es una URL de WhatsApp, mostrar un placeholder con enlace
        logger.info(f"URL de audio de WhatsApp detectada: {url}")
        return f'''
        <div class="audio-container">
            <p>Audio de WhatsApp (haz clic para escuchar)</p>
            <a href="{url}" target="_blank" rel="noopener noreferrer">
                <img src="https://www.freepnglogos.com/uploads/whatsapp-logo-light-green-png-0.png" 
                     width="100" height="100" alt="Escuchar audio de WhatsApp" />
            </a>
        </div>
        '''
    else:
        # URL estándar, intentar reproducirla directamente
        return f'''
        <div class="audio-container">
            <audio controls class="audio-player">
                <source src="{url}" type="audio/mpeg">
                Tu navegador no soporta el elemento de audio.
            </audio>
        </div>
        '''
    
def create_image_tag(url):
    """Crear tag HTML para mostrar una imagen"""
    if not url:
        return ""
        
    if is_data_url(url):
        # Es un data URL, usarlo directamente
        return f'<img src="{url}" class="chat-image" alt="Imagen" />'
    elif is_gcs_url(url):
        # Es una URL de GCS, debería ser accesible directamente
        return f'<img src="{url}" class="chat-image" alt="Imagen de GCS" />'
    elif is_lookaside_url(url):
        # Es una URL de WhatsApp, mostrar un placeholder con enlace
        logger.info(f"URL de WhatsApp detectada: {url}")
        return f'''
        <div class="image-container">
            <p>Imagen de WhatsApp (haz clic para ver)</p>
            <a href="{url}" target="_blank" rel="noopener noreferrer">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/WhatsApp.svg/512px-WhatsApp.svg.png" 
                     width="100" height="100" alt="Ver imagen de WhatsApp" />
            </a>
        </div>
        '''
    else:
        # URL estándar, intentar mostrarla directamente
        return f'<img src="{url}" class="chat-image" alt="Imagen" />'

# Inicialización del administrador de base de datos
db_manager = DatabaseManager()

# Agregar un botón de actualización manual
if st.button("Actualizar"):
    st.rerun()

# Logo de Harmony (cambiado a uno más suave)
st.markdown("""
<div class="harmony-logo">
    <svg class="harmony-logo-image" viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="harmonygradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#8C9EFF"/>
                <stop offset="50%" stop-color="#90CAF9"/>
                <stop offset="100%" stop-color="#A5D6A7"/>
            </linearGradient>
        </defs>
        <text x="10" y="40" fill="#8C9EFF" font-family="Arial, sans-serif" font-weight="bold" font-size="30">HARMONY</text>
        <path d="M15,15 Q20,5 25,15 T35,15" stroke="#8C9EFF" stroke-width="2" fill="none"/>
        <path d="M160,15 Q165,5 170,15 T180,15" stroke="#8C9EFF" stroke-width="2" fill="none"/>
        <g transform="translate(185, 30)">
            <circle cx="0" cy="0" r="7" fill="#90CAF9"/>
        </g>
    </svg>
</div>
""", unsafe_allow_html=True)

# Título principal
st.markdown("<h1 class='main-header'>WhatsApp Bot Dashboard</h1>", unsafe_allow_html=True)

# Columnas para el diseño
col1, col2 = st.columns([1, 3])

# Panel de control en la columna 1
with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3 class="section-header">Panel de Control</h3>', unsafe_allow_html=True)
    
    # Estado del bot
    bot_status = db_manager.get_bot_status()
    status_text = "Activo" if bot_status["is_active"] else "Inactivo"
    status_class = "status-active" if bot_status["is_active"] else "status-inactive"
    
    st.markdown(f"**Estado actual:** <span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)
    
    try:
        # Parsear la fecha ISO
        update_time = datetime.fromisoformat(bot_status["last_updated"])
        formatted_time = update_time.strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"**Última actualización:** {formatted_time}")
    except:
        st.markdown(f"**Última actualización:** {bot_status['last_updated']}")
    
    # Botón para cambiar el estado
    if st.button("Activar/Desactivar Bot"):
        new_status = db_manager.toggle_bot_status()
        new_status_text = "Activo" if new_status else "Inactivo"
        st.success(f"Bot ahora está: {new_status_text}")
        time.sleep(1)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Lista de números de teléfono
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3 class="section-header">Conversaciones</h3>', unsafe_allow_html=True)
    phone_numbers = db_manager.get_unique_numbers()
    
    if not phone_numbers:
        st.info("No se encontraron conversaciones en la base de datos.")
    
    selected_number = st.selectbox(
        "Selecciona un número", 
        phone_numbers if phone_numbers else ["No hay conversaciones"]
    )
    
    if selected_number != "No hay conversaciones":
        st.markdown(f"<div style='text-align:center;margin-top:15px;'><span class='harmony-badge'>{len(db_manager.get_conversations(selected_number))} mensajes</span></div>", unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)

# Visualización de la conversación seleccionada en la columna 2
with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    # Corregir el encabezado cuando no hay conversaciones
    if selected_number != "No hay conversaciones":
        st.markdown(f'<h3 class="section-header">Chat con {selected_number}</h3>', unsafe_allow_html=True)
    else:
        st.markdown('<h3 class="section-header">Inicie una Conversación</h3>', unsafe_allow_html=True)
    
    # Contenedor para la conversación
    if selected_number != "No hay conversaciones":
        conversations = db_manager.get_conversations(selected_number)
        
        if not conversations:
            st.info(f"No se encontraron mensajes para el número {selected_number}")
        else:
            # Solo mostrar el contenedor de chat cuando hay conversaciones
            st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
            
            for conv in conversations:  # Mostrar en orden ascendente
                time_str = conv['timestamp']
                try:
                    # Intentar convertir la cadena ISO a un objeto datetime y luego formatear
                    dt = datetime.fromisoformat(time_str)
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    # Si hay un error, mantener el formato original
                    pass
                
                message_class = "bot-message" if conv['is_bot'] else "user-message"
                container_class = "bot-message-container" if conv['is_bot'] else "user-message-container"
                sender = "Harmony" if conv['is_bot'] else "Usuario"
                
                # Verificar si el mensaje contiene una imagen
                message_content = conv['message']
                media_url = conv.get('media_url')
                media_type = conv.get('media_type')
                image_html = ""
                audio_html = ""
                
                # Extraer URL de audio del contenido del mensaje si existe
                audio_url = None
                if "[🎤 Audio recibido" in message_content:
                    # Intentar extraer la URL del audio del mensaje
                    audio_match = re.search(r'\[🎤 Audio recibido - (.*?)\]', message_content)
                    if audio_match:
                        audio_url = audio_match.group(1)

                # Verificar si hay una URL de imagen
                if media_url:
                    image_html = create_image_tag(media_url)
                
                # Si el mensaje contiene "[IMAGEN]" o similar pero no tiene URL
                elif "[IMAGEN]" in message_content or "[IMAGEN ENVIADA]" in message_content:
                    image_html = '''
                    <div class="image-container">
                        <p>[Imagen no disponible]</p>
                    </div>
                    '''
                
                st.markdown(
                    f"<div class='{container_class}'>"
                    f"<div class='{message_class}'>"
                    f"<div class='sender-name'>{sender}</div>"
                    f"{message_content}"
                    f"{image_html}"
                    f"<div class='time-stamp'>{time_str}</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Mensaje informativo cuando no hay conversaciones
        st.warning("Por favor selecciona un número de teléfono para ver la conversación")
    
    # Formulario para enviar mensajes - solo mostrar si hay un número seleccionado
    if selected_number != "No hay conversaciones":
        with st.form(key='message_form'):
            user_message = st.text_area("Escribe un mensaje:", height=100)
            col1_form, col2_form = st.columns([3, 1])
            with col2_form:
                submit_button = st.form_submit_button("Enviar")
            
            if submit_button and user_message:
                with st.spinner("Enviando mensaje..."):
                    # Enviar mensaje
                    success = db_manager.send_message(selected_number, user_message)
                    
                    if success:
                        st.success("✅ Mensaje enviado correctamente a WhatsApp")
                    else:
                        st.warning("⚠️ El mensaje se guardó localmente pero no se pudo enviar a WhatsApp. Revisar logs para más detalles.")
                    
                    time.sleep(1)
                    st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Configurar actualización automática
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = time.time()

# Comprobar si ha pasado suficiente tiempo desde la última actualización
current_time = time.time()
if current_time - st.session_state.last_update_time > 15:  # 15 segundos
    st.session_state.last_update_time = current_time
    # No usamos st.rerun() aquí para evitar actualizaciones infinitas

# Notas de pie de página
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<div class='footer-note'>**Nota:** Los mensajes enviados desde esta interfaz aparecerán como enviados por un operador humano.</div>", unsafe_allow_html=True)
st.markdown("<div class='footer-note'>**Nota 2:** La página se actualiza automáticamente cada 15 segundos. También puedes usar el botón 'Actualizar' para ver nuevos mensajes inmediatamente.</div>", unsafe_allow_html=True)

# Verificación de configuración WhatsApp (solo visible en el expander)
with st.expander("Estado de integración con WhatsApp", expanded=False):
    st.subheader("Estado de la configuración de WhatsApp")
    
    # Verificar variables de entorno
    env_status = []
    if WHATSAPP_ACCESS_TOKEN:
        env_status.append("✅ Token de acceso: Configurado")
    else:
        env_status.append("❌ Token de acceso: No configurado")
    
    if WHATSAPP_PHONE_NUMBER_ID:
        env_status.append(f"✅ ID de número: Configurado ({WHATSAPP_PHONE_NUMBER_ID})")
    else:
        env_status.append("❌ ID de número: No configurado")
    
    # Mostrar estado
    for status in env_status:
        st.markdown(status)

    
    # Añadir botón para probar la conexión
    if st.button("Probar conexión WhatsApp"):
        try:
            if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
                st.error("❌ No se puede probar: Faltan variables de configuración")
            else:
                # URL para verificar estado de la API
                test_url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}"
                headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
                
                with st.spinner("Verificando conexión..."):
                    response = requests.get(test_url, headers=headers)
                    
                if response.status_code == 200:
                    st.success("✅ Conexión exitosa con la API de WhatsApp")
                    st.json(response.json())
                else:
                    st.error(f"❌ Error en la conexión: {response.status_code}")
                    st.json(response.json())
        except Exception as e:
            st.error(f"❌ Error al probar la conexión: {str(e)}")

# Información de conversaciones (versión simplificada usando componentes nativos)
with st.expander("Información de conversaciones", expanded=False):
    try:
        # Conexión a la base de datos
        conn = sqlite3.connect(db_manager.db_path)
        
        # Realizar la consulta directamente con pandas
        df = pd.read_sql(
            "SELECT id, phone_number, message, timestamp, is_bot FROM conversations ORDER BY timestamp DESC LIMIT 50",
            conn
        )
        
        if df.empty:
            st.info("No hay mensajes registrados en la base de datos.")
        else:
            st.subheader("Últimos 50 mensajes en la base de datos:")
            
            # Modificar el DataFrame para mejor visualización
            df.columns = ['ID', 'Número de teléfono', 'Mensaje', 'Fecha y hora', 'Es Bot']
            
            # Truncar mensajes largos
            df['Mensaje'] = df['Mensaje'].apply(lambda x: x[:50] + '...' if len(str(x)) > 50 else x)
            
            # Convertir valores booleanos a texto legible
            df['Es Bot'] = df['Es Bot'].apply(lambda x: "Bot" if x == 1 else "Usuario")
            
            # Usar el componente nativo de tabla sin HTML personalizado
            st.table(df)
            
            # Botón para descargar CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Descargar datos como CSV",
                data=csv,
                file_name='conversaciones_harmony.csv',
                mime='text/csv',
            )
    except Exception as e:
        st.error(f"Error al cargar los datos: {str(e)}")
    finally:
        try:
            conn.close()
        except:
            pass

# Añadir esta función para enviar mensajes a WhatsApp
def send_whatsapp_message(phone_number, message):
    """Envía un mensaje a WhatsApp usando la API de WhatsApp Cloud"""
    
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("No se pueden enviar mensajes: Faltan credenciales de WhatsApp")
        return False, {"error": "Configuración de WhatsApp incompleta"}
    
    # Formatear número de teléfono (eliminar '+' si existe)
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    # URL de la API
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    # Encabezados
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"
    }
    
    # Datos del mensaje
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    try:
        # Registrar información de depuración
        logger.info(f"Enviando mensaje a WhatsApp: {phone_number}")
        logger.debug(f"URL de API: {url}")
        logger.debug(f"Payload: {json.dumps(payload)}")
        
        # Enviar solicitud a la API
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response_data = response.json()
        
        # Registrar la respuesta
        if response.status_code == 200:
            logger.info(f"Mensaje enviado correctamente a WhatsApp: {response_data}")
            return True, response_data
        else:
            logger.error(f"Error al enviar mensaje a WhatsApp. Código: {response.status_code}, Respuesta: {response_data}")
            return False, response_data
    
    except Exception as e:
        logger.error(f"Excepción al enviar mensaje a WhatsApp: {str(e)}")
        return False, {"error": str(e)}