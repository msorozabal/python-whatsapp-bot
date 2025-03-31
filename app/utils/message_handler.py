import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MessageHandler:
    """
    Manejador de mensajes para la integración entre el bot de WhatsApp y la interfaz Streamlit.
    Proporciona métodos para registrar mensajes y controlar el estado del bot.
    """
    def __init__(self, db_path="whatsapp_conversations.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Inicializa la base de datos si no existe."""
        try:
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
            logger.info("Base de datos para Streamlit inicializada correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos para Streamlit: {e}")
    
    def add_message(self, phone_number, message, is_bot=True, media_url=None):
        """Registra un mensaje en la base de datos para Streamlit."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "INSERT INTO conversations (phone_number, message, timestamp, is_bot, media_url) VALUES (?, ?, ?, ?, ?)",
                (phone_number, message, datetime.now().isoformat(), is_bot, media_url)
            )
            conn.commit()
            conn.close()
            logger.info(f"Mensaje registrado para Streamlit de {'bot' if is_bot else 'usuario'} para {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Error al registrar mensaje para Streamlit: {e}")
            return False
    
    def should_bot_respond(self, phone_number):
        """Determina si el bot debe responder según su estado actual en Streamlit."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT is_active FROM bot_status WHERE id = 1")
            is_active = c.fetchone()[0]
            conn.close()
            return bool(is_active)
        except Exception as e:
            logger.error(f"Error al verificar estado del bot en Streamlit: {e}")
            # En caso de error, asumimos que el bot debe responder
            return True
    
    def mark_as_read(self, message_id):
        """Marca un mensaje como leído."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("UPDATE conversations SET is_read = TRUE WHERE id = ?", (message_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error al marcar mensaje como leído: {e}")
            return False
    
    def get_unread_count(self, phone_number=None):
        """Obtiene el conteo de mensajes no leídos."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            if phone_number:
                c.execute("SELECT COUNT(*) FROM conversations WHERE phone_number = ? AND is_read = FALSE", (phone_number,))
            else:
                c.execute("SELECT COUNT(*) FROM conversations WHERE is_read = FALSE")
            
            count = c.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error al obtener conteo de mensajes no leídos: {e}")
            return 0