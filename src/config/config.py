import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Config:
    """
    Configuración centralizada de la aplicación.
    Lee variables de entorno y define rutas comunes.
    """
    # Base de Datos SQLite
    DB_NAME = os.getenv("DB_NAME", "flamingo_sys.db")
    DB_PATH = os.path.join(os.getcwd(), "data", DB_NAME)
    
    # MongoDB Atlas
    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "flamingo_cloud")
    
    # Email (Smtplib)
    EMAIL_USER = os.getenv("EMAIL_USER", "")
    EMAIL_PASS = os.getenv("EMAIL_PASS", "")  # Usar App Password si es Gmail
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    
    # Asegurar que el directorio data existe
    @staticmethod
    def init_app():
        data_dir = os.path.join(os.getcwd(), "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

# Inicializar entorno
Config.init_app()
