import os
import logging
from flask import Flask, send_from_directory
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

def create_app(test_config=None):
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear y configurar la aplicación
    app = Flask(__name__, static_folder='static')
    
    # Asegurarse de que el directorio de imágenes existe
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    whatsapp_images_dir = os.path.join(static_dir, 'whatsapp_images')
    
    for directory in [static_dir, whatsapp_images_dir]:
        os.makedirs(directory, exist_ok=True)
    
    # Cargar valores de .env para debugging
    logging.info(f"PHONE_NUMBER_ID: {os.getenv('PHONE_NUMBER_ID', 'No configurado')}")
    logging.info(f"VERSION: {os.getenv('VERSION', 'No configurado')}")
    
    # Configurar desde variables de entorno
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        ACCESS_TOKEN=os.environ.get('ACCESS_TOKEN', ''),
        VERSION=os.environ.get('VERSION', 'v17.0'),
        PHONE_NUMBER_ID=os.environ.get('PHONE_NUMBER_ID', ''),
        VERIFY_TOKEN=os.environ.get('VERIFY_TOKEN', 'Harmony2025'),
        OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY', ''),
        OPENAI_ASSISTANT_ID=os.environ.get('OPENAI_ASSISTANT_ID', ''),
    )

    if test_config is None:
        # Cargar la configuración desde archivo, si existe
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Cargar la configuración de prueba
        app.config.from_mapping(test_config)

    # Imprimir valores de configuración críticos para debugging
    logging.info(f"PHONE_NUMBER_ID en app.config: {app.config.get('PHONE_NUMBER_ID', 'No configurado')}")
    logging.info(f"VERSION en app.config: {app.config.get('VERSION', 'No configurado')}")

    # Ruta para acceder a las imágenes de WhatsApp
    @app.route('/static/whatsapp_images/<path:filename>')
    def whatsapp_images(filename):
        return send_from_directory(whatsapp_images_dir, filename)

    # Registrar blueprint para webhook
    from app.services import webhook
    app.register_blueprint(webhook.bp)

    # Ruta principal para verificar que la aplicación está funcionando
    @app.route('/')
    def index():
        return "WhatsApp Bot API está en funcionamiento"

    return app