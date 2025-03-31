import subprocess
import os
import sys
import time

if __name__ == "__main__":
    # Asegurarse de que existe el directorio para imágenes
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    whatsapp_images_dir = os.path.join(static_dir, "whatsapp_images")
    
    # Crear los directorios si no existen
    try:
        os.makedirs(static_dir, exist_ok=True)
        os.makedirs(whatsapp_images_dir, exist_ok=True)
        print(f"Directorio para imágenes configurado: {whatsapp_images_dir}")
    except Exception as e:
        print(f"Advertencia: No se pudo crear el directorio para imágenes: {e}")
    
    # Mostrar mensaje informativo
    print("Iniciando el dashboard de WhatsApp Bot...")
    print("Esto puede tardar unos segundos...")
    
    # Ejecutar el dashboard de Streamlit
    streamlit_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.py")
    
    try:
        # Imprimir URLs de acceso
        print("\n" + "=" * 60)
        print("Dashboard disponible en:")
        print("- URL Local: http://localhost:8501")
        print("=" * 60)
        print("\nPresiona Ctrl+C para detener el dashboard\n")
        

        
        # Ejecutar Streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", streamlit_path, "--server.port=8501"])
    except KeyboardInterrupt:
        print("\nDeteniendo el dashboard...")
        time.sleep(1)
        print("Dashboard detenido.")
    except Exception as e:
        print(f"\nError al ejecutar Streamlit: {e}")
        print("Asegúrate de tener Streamlit instalado:")
        print("pip install streamlit pandas")
        sys.exit(1)