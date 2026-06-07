import re
from db.database import get_connection
from services.auditoria import registrar as registrar_auditoria


def registrar_alumno(datos: dict):
    """
    Registra un nuevo alumno y lo vincula a un grupo.
    datos: {nombre, apellido, dni, fecha_nacimiento, telefono, telefono_tutor, direccion, id_grupo}

    Reglas:
      - nombre, apellido, dni, fecha_nacimiento e id_grupo son obligatorios.
      - dni: solo dígitos, 7 u 8, y único.
      - el grupo debe existir y estar activo.
      - se audita el alta (entidad 'Alumnos').

    Retorna (exito: bool, mensaje: str).
    """
    nombre = (datos.get('nombre') or "").strip()
    apellido = (datos.get('apellido') or "").strip()
    dni = (datos.get('dni') or "").strip()
    fecha_nac = (datos.get('fecha_nacimiento') or "").strip()
    id_grupo = datos.get('id_grupo')

    # Validaciones de obligatorios
    if not nombre:
        return False, "El nombre es obligatorio."
    if not apellido:
        return False, "El apellido es obligatorio."
    if not dni:
        return False, "El DNI es obligatorio."
    if not (dni.isdigit() and len(dni) in (7, 8)):
        return False, "El DNI debe tener 7 u 8 dígitos numéricos."
    if not fecha_nac:
        return False, "La fecha de nacimiento es obligatoria."
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha_nac):
        return False, "La fecha debe tener formato AAAA-MM-DD."
    if not id_grupo:
        return False, "Debe seleccionar un grupo."

    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()

        # DNI único
        cursor.execute("SELECT 1 FROM Alumnos WHERE dni = ?", (dni,))
        if cursor.fetchone():
            return False, "Ya existe un alumno con ese DNI."

        # El grupo debe existir y estar activo
        cursor.execute("SELECT estado FROM Grupos WHERE id_grupo = ?", (id_grupo,))
        grupo = cursor.fetchone()
        if not grupo:
            return False, "El grupo seleccionado no existe."
        if grupo["estado"] != "activo":
            return False, "El grupo seleccionado no está activo."

        cursor.execute("""
            INSERT INTO Alumnos (nombre, apellido, dni, fecha_nacimiento, telefono, telefono_tutor, direccion, id_grupo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nombre, apellido, dni, fecha_nac,
            (datos.get('telefono') or "").strip() or None,
            (datos.get('telefono_tutor') or "").strip() or None,
            (datos.get('direccion') or "").strip() or None,
            id_grupo,
        ))
        id_alumno = cursor.lastrowid

        registrar_auditoria(
            accion="INSERT", entidad="Alumnos", id_entidad=id_alumno,
            datos={"nombre": nombre, "apellido": apellido, "dni": dni, "id_grupo": id_grupo},
            usuario=datos.get("usuario"), conn=conn,
        )

        conn.commit()
        return True, "Alumno registrado correctamente."
    except Exception as e:
        print(f"Error al registrar alumno: {e}")
        return False, "Ocurrió un error al registrar el alumno."
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
