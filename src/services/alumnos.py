from db.database import get_connection

def registrar_alumno(datos: dict):
    """
    Registra un nuevo alumno.
    datos: {nombre, apellido, dni, fecha_nacimiento, telefono, telefono_tutor, direccion, id_grupo}
    """
    conn = get_connection()
    if not conn: return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Alumnos (nombre, apellido, dni, fecha_nacimiento, telefono, telefono_tutor, direccion, id_grupo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datos['nombre'], datos['apellido'], datos['dni'], datos['fecha_nacimiento'],
            datos.get('telefono'), datos.get('telefono_tutor'), datos.get('direccion'), datos['id_grupo']
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar alumno: {e}")
        return False
    finally:
        conn.close()

def listar_alumnos(filtro_estado='activo', busqueda=''):
    """
    Lista alumnos con filtros opcionales.
    busqueda: texto para buscar en nombre, apellido o DNI.
    """
    conn = get_connection()
    if not conn: return []
    
    query = """
        SELECT a.*, g.nombre_grupo 
        FROM Alumnos a
        JOIN Grupos g ON a.id_grupo = g.id_grupo
        WHERE a.estado = ?
    """
    params = [filtro_estado]
    
    if busqueda:
        query += " AND (a.nombre LIKE ? OR a.apellido LIKE ? OR a.dni LIKE ?)"
        term = f"%{busqueda}%"
        params.extend([term, term, term])
        
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def editar_alumno(id_alumno, datos: dict):
    """Actualiza datos de un alumno."""
    conn = get_connection()
    if not conn: return False
    
    try:
        cursor = conn.cursor()
        keys = datos.keys()
        sql = f"UPDATE Alumnos SET {', '.join([f'{k} = ?' for k in keys])} WHERE id_alumno = ?"
        params = list(datos.values()) + [id_alumno]
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error al editar alumno: {e}")
        return False
    finally:
        conn.close()

def baja_logica_alumno(id_alumno, nuevo_estado='inactivo'):
    """Cambia el estado de un alumno (activar/desactivar)."""
    return editar_alumno(id_alumno, {'estado': nuevo_estado})

def obtener_grupos():
    """Retorna los grupos disponibles para inscripción (solo activos)."""
    conn = get_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Grupos WHERE estado = 'activo' ORDER BY nombre_grupo")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
