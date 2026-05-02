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

PREGUNTAS_SEGURIDAD = [
    "¿Cuál es el apodo que te puso tu familia?",
    "¿Cómo se llamaba tu mejor amigo de la infancia?",
    "¿Cuál es el nombre de tu abuela materna?",
    "¿Cuál es tu película favorita?",
    "¿Cuál es tu canción favorita?",
    "¿Cuál es tu equipo de fútbol?",
    "¿Cuál fue el primer deporte que practicaste?",
    "¿Cuál fue el primer equipo en el que jugaste?",
    "¿Cómo se llamaba tu primer profesor/a?",
    "¿Cuál fue el primer trabajo que tuviste?",
]

def guardar_preguntas_seguridad(id_usuario, preguntas_respuestas):
    """Guarda o actualiza las preguntas de seguridad de un usuario."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        
        # Validar si ya existen
        cursor.execute("SELECT id FROM PreguntasSeguridad WHERE id_usuario = ?", (id_usuario,))
        existe = cursor.fetchone()
        
        # Procesar y hashear respuestas
        p1, r1 = preguntas_respuestas[0]["pregunta"], hash_password(preguntas_respuestas[0]["respuesta"].lower().strip())
        p2, r2 = preguntas_respuestas[1]["pregunta"], hash_password(preguntas_respuestas[1]["respuesta"].lower().strip())
        p3, r3 = preguntas_respuestas[2]["pregunta"], hash_password(preguntas_respuestas[2]["respuesta"].lower().strip())
        
        if existe:
            cursor.execute("""
                UPDATE PreguntasSeguridad 
                SET pregunta_1 = ?, respuesta_1 = ?, pregunta_2 = ?, respuesta_2 = ?, pregunta_3 = ?, respuesta_3 = ?
                WHERE id_usuario = ?
            """, (p1, r1, p2, r2, p3, r3, id_usuario))
        else:
            cursor.execute("""
                INSERT INTO PreguntasSeguridad (id_usuario, pregunta_1, respuesta_1, pregunta_2, respuesta_2, pregunta_3, respuesta_3)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (id_usuario, p1, r1, p2, r2, p3, r3))
            
        conn.commit()
        return True
    finally:
        conn.close()

def obtener_preguntas(dni):
    """Retorna las preguntas configuradas por el usuario."""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ps.pregunta_1, ps.pregunta_2, ps.pregunta_3 
            FROM PreguntasSeguridad ps
            JOIN Usuarios u ON ps.id_usuario = u.id_usuario
            WHERE u.usuario = ?
        """, (dni,))
        row = cursor.fetchone()
        if row:
            return [row['pregunta_1'], row['pregunta_2'], row['pregunta_3']]
        return None
    finally:
        conn.close()

def verificar_respuestas(dni, respuestas):
    """Verifica si las 3 respuestas ingresadas coinciden con los hashes en DB."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ps.respuesta_1, ps.respuesta_2, ps.respuesta_3 
            FROM PreguntasSeguridad ps
            JOIN Usuarios u ON ps.id_usuario = u.id_usuario
            WHERE u.usuario = ?
        """, (dni,))
        row = cursor.fetchone()
        if not row:
            return False
            
        return (
            check_password(respuestas[0].lower().strip(), row['respuesta_1']) and
            check_password(respuestas[1].lower().strip(), row['respuesta_2']) and
            check_password(respuestas[2].lower().strip(), row['respuesta_3'])
        )
    finally:
        conn.close()

def resetear_contrasena(dni, nueva_contrasena):
    """Actualiza la contraseña del usuario en la BD."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        hashed = hash_password(nueva_contrasena)
        cursor.execute("UPDATE Usuarios SET contrasena = ? WHERE usuario = ?", (hashed, dni))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
