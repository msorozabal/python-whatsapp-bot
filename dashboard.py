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

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

# Estilo CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #25D366;
        text-align: center;
        margin-bottom: 30px;
    }
    .chat-container {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        height: 450px;
        overflow-y: auto;
        background-color: #121212;
        margin-bottom: 20px;
    }
    .user-message {
        background-color: #005C4B;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 10px 0;
        max-width: 85%;
        align-self: flex-end;
        margin-left: auto;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        word-wrap: break-word;
        display: block;
    }
    .bot-message {
        background-color: #1F2C34;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 10px 0;
        max-width: 85%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        word-wrap: break-word;
        display: block;
    }
    .time-stamp {
        font-size: 0.7rem;
        color: rgba(255,255,255,0.6);
        display: block;
        margin-top: 5px;
        text-align: right;
    }
    .status-active {
        color: #25D366;
        font-weight: bold;
    }
    .status-inactive {
        color: #FF0000;
        font-weight: bold;
    }
    .sender-name {
        font-weight: bold;
        margin-bottom: 5px;
    }
    .stButton>button {
        background-color: #25D366;
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px 15px;
        border-radius: 5px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #128C7E;
    }
    .user-message-container {
        display: flex;
        justify-content: flex-end;
        width: 100%;
    }
    .bot-message-container {
        display: flex;
        justify-content: flex-start;
        width: 100%;
    }
    .stTextArea textarea {
        background-color: #2A2F32;
        color: white;
        border: 1px solid #128C7E;
        border-radius: 5px;
    }
    .chat-image {
        max-width: 250px;
        max-height: 250px;
        border-radius: 5px;
        margin-top: 10px;
        margin-bottom: 10px;
        display: block;
    }
    .image-container {
        width: 100%;
        text-align: center;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Clase para gestionar la base de datos
class DatabaseManager:
    def __init__(self, db_path="whatsapp_conversations.db"):
        self.db_path = db_path
        self.init_db()
    
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
        # Esta función simula el envío de un mensaje a WhatsApp
        # En una implementación real, aquí invocarías a la API de WhatsApp
        self.add_message(phone_number, message, is_bot=False)
        return True

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

# Título principal
st.markdown("<h1 class='main-header'>WhatsApp Bot Dashboard</h1>", unsafe_allow_html=True)

# Columnas para el diseño
col1, col2 = st.columns([1, 3])

# Panel de control en la columna 1
with col1:
    st.subheader("Panel de Control")
    
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
    
    # Lista de números de teléfono
    st.subheader("Conversaciones")
    phone_numbers = db_manager.get_unique_numbers()
    
    if not phone_numbers:
        st.info("No se encontraron conversaciones en la base de datos.")
    
    selected_number = st.selectbox(
        "Selecciona un número", 
        phone_numbers if phone_numbers else ["No hay conversaciones"]
    )

# Visualización de la conversación seleccionada en la columna 2
with col2:
    st.subheader(f"Chat con {selected_number}")
    
    # Contenedor para la conversación
    chat_container = st.container()
    
    # Mostrar la conversación
    if selected_number != "No hay conversaciones":
        conversations = db_manager.get_conversations(selected_number)
        
        if not conversations:
            st.warning(f"No se encontraron mensajes para el número {selected_number}")
        
        with chat_container:
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
                sender = "Bot" if conv['is_bot'] else "Humano"
                
                # Verificar si el mensaje contiene una imagen
                message_content = conv['message']
                media_url = conv.get('media_url')
                image_html = ""
                
                # Verificar si hay una URL de imagen
                if media_url:
                    logger.info(f"URL de imagen encontrada: {media_url}")
                    image_html = create_image_tag(media_url)
                
                # Si el mensaje contiene "[IMAGEN]" o similar pero no tiene URL, intentar mostrar un placeholder
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
    
    # Formulario para enviar mensajes
    with st.form(key='message_form'):
        user_message = st.text_area("Escribe un mensaje:", height=100)
        submit_button = st.form_submit_button("Enviar")
        
        if submit_button and user_message and selected_number != "No hay conversaciones":
            # Enviar mensaje
            if db_manager.send_message(selected_number, user_message):
                st.success("Mensaje enviado correctamente")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Error al enviar el mensaje")

# Configurar actualización automática
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = time.time()

# Comprobar si ha pasado suficiente tiempo desde la última actualización
current_time = time.time()
if current_time - st.session_state.last_update_time > 15:  # 15 segundos
    st.session_state.last_update_time = current_time
    # No usamos st.rerun() aquí para evitar actualizaciones infinitas

# Notas de pie de página
st.markdown("---")
st.markdown("**Nota:** Los mensajes enviados desde esta interfaz aparecerán como enviados por un operador humano.")
st.markdown("**Nota 2:** La página se actualiza automáticamente cada 15 segundos. También puedes usar el botón 'Actualizar' para ver nuevos mensajes inmediatamente.")

# Información de depuración (oculta por defecto)
with st.expander("Información de depuración", expanded=False):
    st.write("Base de datos:", db_manager.db_path)
    st.write("Ruta de archivo:", os.path.abspath(db_manager.db_path))
    
    # Información sobre Google Cloud Storage
    bucket_name = os.getenv("GCP_BUCKET_NAME", "kapta-bucket")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./kapta-service-account.json")
    
    st.write(f"Bucket GCS configurado: {bucket_name}")
    st.write(f"Ruta de credenciales GCS: {creds_path}")
    
    # Intentar obtener información sobre el bucket
    try:
        from google.cloud import storage
        storage_client = storage.Client.from_service_account_json(creds_path)
        bucket = storage_client.bucket(bucket_name)
        st.write(f"Bucket existe: {bucket.exists()}")
        if bucket.exists():
            blobs = list(bucket.list_blobs(prefix="whatsapp_images/"))
            st.write(f"Imágenes en GCS: {len(blobs)}")
            if len(blobs) > 0:
                st.write("Últimas 5 imágenes en GCS:")
                for blob in blobs[:5]:
                    st.write(f"- {blob.name} ({blob.public_url})")
    except Exception as e:
        st.write(f"Error al conectar con GCS: {e}")
    
    # Mostrar todas las URLs de imágenes en la base de datos
    conn = sqlite3.connect(db_manager.db_path)
    df_images = pd.read_sql_query(
        "SELECT id, phone_number, message, timestamp, media_url FROM conversations WHERE media_url IS NOT NULL", 
        conn
    )
    conn.close()
    
    if not df_images.empty:
        st.write(f"Encontradas {len(df_images)} imágenes en la base de datos:")
        st.dataframe(df_images)
        
        # Mostrar un ejemplo de la primera imagen
        if len(df_images) > 0:
            example_url = df_images.iloc[0]['media_url']
            st.write(f"Ejemplo de URL de imagen: {example_url}")
            if is_data_url(example_url):
                st.write("Es un data URL (base64)")
                st.markdown(create_image_tag(example_url), unsafe_allow_html=True)
            elif is_gcs_url(example_url):
                st.write("Es una URL de Google Cloud Storage")
                st.markdown(f"<img src='{example_url}' style='max-width:300px'>", unsafe_allow_html=True)
            elif is_lookaside_url(example_url):
                st.write("Es una URL de WhatsApp Business")
                st.markdown(f"<a href='{example_url}' target='_blank'>Abrir enlace</a>", unsafe_allow_html=True)
            else:
                st.write("Es una URL normal")
                st.markdown(f"<img src='{example_url}' style='max-width:300px'>", unsafe_allow_html=True)
    
    # Mostrar el contenido completo de la tabla de conversaciones
    conn = sqlite3.connect(db_manager.db_path)
    df = pd.read_sql_query("SELECT * FROM conversations ORDER BY timestamp DESC LIMIT 50", conn)
    conn.close()
    
    st.write("Últimos 50 mensajes en la base de datos:")
    st.dataframe(df)