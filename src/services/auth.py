import bcrypt
import smtplib
from email.mime.text import MIMEText
from db.database import get_connection
from config.config import Config

class Session:
    """Singleton para manejar la sesión del usuario logueado."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Session, cls).__new__(cls)
            cls._instance.user = None
        return cls._instance

session = Session()

def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña coincide con su hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def login(usuario, contrasena):
    """
    Busca al usuario en la BD y verifica su contraseña.
    Retorna el dict del usuario si es exitoso, None si no.
    """
    conn = get_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Usuarios WHERE usuario = ? AND activo = 1", (usuario,))
        user_row = cursor.fetchone()
        
        if user_row:
            user = dict(user_row)
            if check_password(contrasena, user['contrasena']):
                session.user = user
                return user
        return None
    finally:
        conn.close()

def logout():
    """Limpia la sesión actual."""
    session.user = None

def recuperar_contrasena(email, usuario_dni):
    """
    Envía un email con una contraseña temporal.
    TODO: Implementar lógica de generación de password temporal y actualización en BD.
    """
    if not Config.EMAIL_USER or not Config.EMAIL_PASS:
        return False, "Configuración de email incompleta."
        
    nueva_pass = "Tmp12345" # Password temporal simplificada para la demo
    hashed = hash_password(nueva_pass)
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Buscar usuario por email
        cursor.execute("UPDATE Usuarios SET contrasena = ? WHERE email = ?", (hashed, email))
        if cursor.rowcount == 0:
            return False, "Ese email no está registrado."
            
        conn.commit()
        
        # Enviar email
        msg = MIMEText(f"Tu nueva contraseña temporal es: {nueva_pass}\nPor favor, cámbiala al ingresar.")
        msg['Subject'] = 'Recuperación de Contraseña - Flamingo Sys'
        msg['From'] = Config.EMAIL_USER
        msg['To'] = email
        
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.EMAIL_USER, Config.EMAIL_PASS)
            server.send_message(msg)
            
        return True, "Email enviado con éxito."
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()
