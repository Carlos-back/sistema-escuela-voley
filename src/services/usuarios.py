from db.database import get_connection
from services.auth import hash_password

def crear_usuario(usuario, contrasena, rol, nombre=None, apellido=None, email=None):
    """Crea un nuevo usuario en la base de datos."""
    conn = get_connection()
    if not conn: return False
    
    try:
        hashed = hash_password(contrasena)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Usuarios (usuario, contrasena, rol, nombre, apellido, email) VALUES (?, ?, ?, ?, ?, ?)",
            (usuario, hashed, rol, nombre, apellido, email)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear usuario: {e}")
        return None
    finally:
        conn.close()

def listar_usuarios():
    """Retorna una lista de todos los usuarios (sin incluir contraseñas)."""
    conn = get_connection()
    if not conn: return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT *, usuario AS dni FROM Usuarios")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def editar_usuario(id_usuario, usuario=None, rol=None, contrasena=None, nombre=None, apellido=None, email=None):
    """Actualiza datos de un usuario."""
    conn = get_connection()
    if not conn: return False
    
    updates = []
    params = []
    
    if usuario is not None:
        updates.append("usuario = ?")
        params.append(usuario)
    if rol is not None:
        updates.append("rol = ?")
        params.append(rol)
    if contrasena is not None:
        updates.append("contrasena = ?")
        params.append(hash_password(contrasena))
    if nombre is not None:
        updates.append("nombre = ?")
        params.append(nombre)
    if apellido is not None:
        updates.append("apellido = ?")
        params.append(apellido)
    if email is not None:
        updates.append("email = ?")
        params.append(email)
        
    if not updates: return False
    
    params.append(id_usuario)
    sql = f"UPDATE Usuarios SET {', '.join(updates)} WHERE id_usuario = ?"
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error al editar usuario: {e}")
        return False
    finally:
        conn.close()

def baja_logica_usuario(id_usuario, activo=0):
    """Realiza una baja lógica del usuario."""
    conn = get_connection()
    if not conn: return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Usuarios SET activo = ? WHERE id_usuario = ?", (activo, id_usuario))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error en baja lógica de usuario: {e}")
        return False
    finally:
        conn.close()
