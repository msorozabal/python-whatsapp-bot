import requests
import os
import logging
import base64
from io import BytesIO
from PIL import Image
import tempfile
import uuid
import time

logger = logging.getLogger(__name__)

class ImageProxy:
    """
    Clase para gestionar la descarga y almacenamiento de imágenes de WhatsApp.
    Permite guardar imágenes localmente para acceder a ellas desde el dashboard.
    """
    
    def __init__(self, images_dir="whatsapp_images", bucket_name=None):
        """
        Inicializa el proxy de imágenes.
        
        Args:
            images_dir: Directorio local donde se guardarán las imágenes
            bucket_name: Nombre del bucket de GCS (opcional)
        """
        self.images_dir = images_dir
        self.bucket_name = bucket_name
        os.makedirs(self.images_dir, exist_ok=True)
        logger.info(f"Directorio de imágenes configurado: {os.path.abspath(self.images_dir)}")
        
        # Inicializar cliente de GCS con manejo de errores
        self.storage_client = None
        self.bucket = None
        
        # Solo intentar configurar GCS si se proporcionó un bucket_name
        if bucket_name:
            try:
                from google.cloud import storage
                # Intentar obtener credenciales del entorno
                creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./kapta-service-account.json")
                if os.path.exists(creds_path):
                    self.storage_client = storage.Client.from_service_account_json(creds_path)
                    self.bucket = self.storage_client.bucket(bucket_name)
                    logger.info(f"Cliente GCS inicializado con bucket: {bucket_name}")
                else:
                    logger.warning(f"Archivo de credenciales GCS no encontrado: {creds_path}")
            except ImportError:
                logger.warning("Biblioteca google-cloud-storage no instalada. No se usará almacenamiento en GCS.")
            except Exception as e:
                logger.error(f"Error al inicializar cliente GCS: {e}")
    
    def download_and_save(self, url, access_token=None, filename=None):
        """
        Descarga una imagen desde una URL y la guarda localmente.
        
        Args:
            url: URL de la imagen
            access_token: Token de acceso para la API de WhatsApp (opcional)
            filename: Nombre personalizado para el archivo (opcional)
            
        Returns:
            Ruta local al archivo guardado o None si hay un error
        """
        try:
            # Configurar headers con token de acceso si está disponible
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            # Intentar descargar la imagen
            logger.info(f"Descargando imagen desde: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error al descargar imagen - Status: {response.status_code}")
                return None
            
            # Generar nombre de archivo si no se proporciona uno
            if not filename:
                # Usar la última parte de la URL o un timestamp si no es adecuada
                parts = url.split('/')
                if len(parts) > 0 and len(parts[-1]) > 0:
                    filename = parts[-1].split('?')[0]  # Eliminar parámetros de consulta
                    # Asegurarse de que tiene una extensión válida
                    if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        filename += '.jpg'
                else:
                    filename = f"whatsapp_image_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
            
            # Ruta completa al archivo local
            file_path = os.path.join(self.images_dir, filename)
            
            # Guardar la imagen localmente
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Imagen guardada localmente en: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Error al descargar y guardar imagen: {e}")
            return None
    
    def get_image_data_url(self, url, access_token=None):
        """
        Convierte una imagen en un data URL que puede ser incrustado directamente en HTML.
        
        Args:
            url: URL de la imagen
            access_token: Token de acceso para la API de WhatsApp (opcional)
            
        Returns:
            Data URL (base64) de la imagen o None si hay un error
        """
        try:
            # Configurar headers con token de acceso si está disponible
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            # Intentar descargar la imagen
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Error al descargar imagen para data URL - Status: {response.status_code}")
                return None
            
            # Determinar el tipo MIME basado en los headers de respuesta
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            
            # Codificar la imagen en base64
            encoded = base64.b64encode(response.content).decode('utf-8')
            
            # Crear el data URL
            data_url = f"data:{content_type};base64,{encoded}"
            
            return data_url
        
        except Exception as e:
            logger.error(f"Error al crear data URL para imagen: {e}")
            return None
    
    def process_whatsapp_image(self, url, access_token=None):
        """
        Procesa una URL de imagen de WhatsApp y devuelve varias opciones para mostrarla.
        
        Args:
            url: URL de la imagen de WhatsApp
            access_token: Token de acceso para la API de WhatsApp (opcional)
            
        Returns:
            Dictionary con local_path, data_url, original_url (algunos pueden ser None)
        """
        results = {
            "original_url": url,
            "local_path": None,
            "data_url": None
        }
        
        # Generar un nombre único para la imagen
        filename = f"whatsapp_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
        
        # Paso 1: Intentar descargar y guardar la imagen localmente
        local_path = self.download_and_save(
            url=url, 
            access_token=access_token,
            filename=filename
        )
        
        results["local_path"] = local_path
        
        # Paso 2: Intentar crear un data URL (siempre como respaldo)
        data_url = self.get_image_data_url(
            url=url,
            access_token=access_token
        )
        results["data_url"] = data_url
        
        return results