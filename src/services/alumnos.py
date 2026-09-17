"""
Flamingo Sys — Servicio de Alumnos
Lógica de negocio del ABM de la entidad transaccional Alumno (HU01–HU04).
"""

import re
from db.database import get_connection
from services.auditoria import registrar as registrar_auditoria

# ── Mensajes canónicos de validación ────────────────────────────────
MSG_NOMBRE_OBLIGATORIO = "El nombre es obligatorio."
MSG_APELLIDO_OBLIGATORIO = "El apellido es obligatorio."
MSG_DNI_OBLIGATORIO = "El DNI es obligatorio."
MSG_DNI_FORMATO = "El DNI debe tener 7 u 8 dígitos numéricos."
MSG_DNI_DUPLICADO = "Ya existe un alumno con ese DNI."
MSG_FECHA_OBLIGATORIA = "La fecha de nacimiento es obligatoria."
MSG_FECHA_FORMATO = "La fecha debe tener formato AAAA-MM-DD."
MSG_GRUPO_OBLIGATORIO = "Debe seleccionar un grupo."
MSG_GRUPO_INEXISTENTE = "El grupo seleccionado no existe."
MSG_GRUPO_INACTIVO = "El grupo seleccionado no está activo."

# Campos que el alta y la edición manipulan, en el orden de la tabla.
_CAMPOS = ('nombre', 'apellido', 'dni', 'fecha_nacimiento',
           'telefono', 'telefono_tutor', 'direccion', 'id_grupo')


def _normalizar_y_validar(datos: dict):
    """
    Normaliza (trim) y valida los campos de un alumno.
    Regla única compartida por el alta (HU01) y la edición (HU02).

    Retorna (valores: dict | None, error: str | None).
    """
    nombre = (datos.get('nombre') or "").strip()
    apellido = (datos.get('apellido') or "").strip()
    dni = (datos.get('dni') or "").strip()
    fecha_nac = (datos.get('fecha_nacimiento') or "").strip()
    id_grupo = datos.get('id_grupo')

    if not nombre:
        return None, MSG_NOMBRE_OBLIGATORIO
    if not apellido:
        return None, MSG_APELLIDO_OBLIGATORIO
    if not dni:
        return None, MSG_DNI_OBLIGATORIO
    if not (dni.isdigit() and len(dni) in (7, 8)):
        return None, MSG_DNI_FORMATO
    if not fecha_nac:
        return None, MSG_FECHA_OBLIGATORIA
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha_nac):
        return None, MSG_FECHA_FORMATO
    if not id_grupo:
        return None, MSG_GRUPO_OBLIGATORIO

    return {
        'nombre': nombre,
        'apellido': apellido,
        'dni': dni,
        'fecha_nacimiento': fecha_nac,
        'telefono': (datos.get('telefono') or "").strip() or None,
        'telefono_tutor': (datos.get('telefono_tutor') or "").strip() or None,
        'direccion': (datos.get('direccion') or "").strip() or None,
        'id_grupo': int(id_grupo),
    }, None


def _dni_duplicado(cursor, dni, excluir_id=None):
    """
    True si ya existe otro alumno con ese DNI.
    `excluir_id` ignora el propio registro (necesario en la edición).
    """
    if excluir_id is None:
        cursor.execute("SELECT 1 FROM Alumnos WHERE dni = ?", (dni,))
    else:
        cursor.execute("SELECT 1 FROM Alumnos WHERE dni = ? AND id_alumno != ?",
                       (dni, excluir_id))
    return cursor.fetchone() is not None


def _estado_grupo(cursor, id_grupo):
    """Retorna el estado del grupo, o None si no existe."""
    cursor.execute("SELECT estado FROM Grupos WHERE id_grupo = ?", (id_grupo,))
    fila = cursor.fetchone()
    return fila["estado"] if fila else None


def registrar_alumno(datos: dict):
    """
    Registra un nuevo alumno y lo vincula a un grupo (HU01).
    datos: {nombre, apellido, dni, fecha_nacimiento, telefono, telefono_tutor,
            direccion, id_grupo, usuario}

    Reglas:
      - nombre, apellido, dni, fecha_nacimiento e id_grupo son obligatorios.
      - dni: solo dígitos, 7 u 8, y único.
      - el grupo debe existir y estar activo.
      - se audita el alta (entidad 'Alumnos') en la misma transacción.

    Retorna (exito: bool, mensaje: str).
    """
    valores, error = _normalizar_y_validar(datos)
    if error:
        return False, error

    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()

        if _dni_duplicado(cursor, valores['dni']):
            return False, MSG_DNI_DUPLICADO

        estado_grupo = _estado_grupo(cursor, valores['id_grupo'])
        if estado_grupo is None:
            return False, MSG_GRUPO_INEXISTENTE
        if estado_grupo != 'activo':
            return False, MSG_GRUPO_INACTIVO

        cursor.execute(f"""
            INSERT INTO Alumnos ({', '.join(_CAMPOS)})
            VALUES ({', '.join('?' * len(_CAMPOS))})
        """, [valores[campo] for campo in _CAMPOS])
        id_alumno = cursor.lastrowid

        registrar_auditoria(
            accion="INSERT", entidad="Alumnos", id_entidad=id_alumno,
            datos={"nombre": valores['nombre'], "apellido": valores['apellido'],
                   "dni": valores['dni'], "id_grupo": valores['id_grupo']},
            usuario=datos.get("usuario"), conn=conn,
        )

        conn.commit()
        return True, "Alumno registrado correctamente."
    except Exception as e:
        print(f"Error al registrar alumno: {e}")
        return False, "Ocurrió un error al registrar el alumno."
    finally:
        conn.close()


def listar_alumnos(filtro_estado=None, busqueda=''):
    """
    Lista alumnos junto al nombre de su grupo, con filtros opcionales (HU03).

    filtro_estado : 'activo' | 'inactivo' | None  (None = todos los estados)
    busqueda      : texto a buscar en nombre, apellido, nombre completo o DNI.

    Retorna una lista de dicts ordenada por apellido y nombre.
    """
    conn = get_connection()
    if not conn:
        return []

    query = """
        SELECT a.*, g.nombre_grupo
        FROM Alumnos a
        JOIN Grupos g ON a.id_grupo = g.id_grupo
    """
    condiciones = []
    params = []

    if filtro_estado in ('activo', 'inactivo'):
        condiciones.append("a.estado = ?")
        params.append(filtro_estado)

    busqueda = (busqueda or "").strip()
    if busqueda:
        condiciones.append(
            "(a.nombre LIKE ? OR a.apellido LIKE ? OR a.dni LIKE ?"
            " OR (a.nombre || ' ' || a.apellido) LIKE ?)"
        )
        term = f"%{busqueda}%"
        params.extend([term, term, term, term])

    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " ORDER BY a.apellido, a.nombre"

    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def obtener_alumno(id_alumno):
    """Retorna un alumno con el nombre de su grupo, o None si no existe."""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, g.nombre_grupo, g.estado AS estado_grupo
            FROM Alumnos a
            JOIN Grupos g ON a.id_grupo = g.id_grupo
            WHERE a.id_alumno = ?
        """, (id_alumno,))
        fila = cursor.fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def editar_alumno(id_alumno, datos: dict, usuario=None):
    """
    Modifica los datos de un alumno existente (HU02).

    Reglas de negocio:
      - mismas validaciones de formato que el alta.
      - el DNI debe ser único EXCLUYENDO el propio registro.
      - solo se puede mover el alumno a un grupo activo; si el grupo no
        cambia se acepta aunque esté inactivo, para no bloquear la edición
        del resto de los datos cuando el grupo fue dado de baja.
      - dirty checking: solo se actualizan los campos que cambiaron; si no
        hubo cambios, no se escribe ni se audita.
      - se auditan los campos modificados con su valor anterior y nuevo.

    Retorna (exito: bool, mensaje: str).
    """
    valores, error = _normalizar_y_validar(datos)
    if error:
        return False, error

    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT {', '.join(_CAMPOS)} FROM Alumnos WHERE id_alumno = ?",
            (id_alumno,))
        actual = cursor.fetchone()
        if not actual:
            return False, "El alumno no existe."
        actual = dict(actual)

        if _dni_duplicado(cursor, valores['dni'], excluir_id=id_alumno):
            return False, MSG_DNI_DUPLICADO

        # El grupo solo se valida si realmente cambia (ver docstring).
        if valores['id_grupo'] != actual['id_grupo']:
            estado_grupo = _estado_grupo(cursor, valores['id_grupo'])
            if estado_grupo is None:
                return False, MSG_GRUPO_INEXISTENTE
            if estado_grupo != 'activo':
                return False, MSG_GRUPO_INACTIVO

        # Dirty checking: detectar solo los campos que cambiaron
        cambios = {
            campo: {"anterior": actual[campo], "nuevo": valores[campo]}
            for campo in _CAMPOS
            if (actual[campo] or None) != (valores[campo] or None)
        }
        if not cambios:
            return True, "No se realizaron cambios."

        set_clause = ", ".join(f"{campo} = ?" for campo in cambios)
        params = [valores[campo] for campo in cambios] + [id_alumno]
        cursor.execute(f"UPDATE Alumnos SET {set_clause} WHERE id_alumno = ?", params)

        registrar_auditoria(
            accion="UPDATE", entidad="Alumnos", id_entidad=id_alumno,
            datos={"cambios": cambios}, usuario=usuario, conn=conn,
        )

        conn.commit()
        return True, "Cambios guardados correctamente."
    except Exception as e:
        print(f"Error al editar alumno: {e}")
        return False, "Ocurrió un error al guardar los cambios."
    finally:
        conn.close()


def baja_logica_alumno(id_alumno, nuevo_estado='inactivo', usuario=None):
    """
    Cambia el estado de un alumno entre 'activo' e 'inactivo' (HU04).

    Es una baja lógica: no borra el registro ni su historial de asistencias
    y pagos. La operación se audita dentro de la misma transacción.

    Retorna (exito: bool, mensaje: str).
    """
    if nuevo_estado not in ('activo', 'inactivo'):
        return False, "Estado inválido."

    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nombre, apellido, estado FROM Alumnos WHERE id_alumno = ?",
            (id_alumno,))
        alumno = cursor.fetchone()
        if not alumno:
            return False, "El alumno no existe."

        estado_anterior = alumno["estado"]
        if estado_anterior == nuevo_estado:
            return True, f"El alumno ya se encuentra {nuevo_estado}."

        cursor.execute("UPDATE Alumnos SET estado = ? WHERE id_alumno = ?",
                       (nuevo_estado, id_alumno))

        registrar_auditoria(
            accion="UPDATE", entidad="Alumnos", id_entidad=id_alumno,
            datos={"cambios": {"estado": {"anterior": estado_anterior,
                                          "nuevo": nuevo_estado}}},
            usuario=usuario, conn=conn,
        )

        conn.commit()
        accion = "desactivado" if nuevo_estado == "inactivo" else "reactivado"
        return True, f"Alumno {alumno['nombre']} {alumno['apellido']} {accion} correctamente."
    except Exception as e:
        print(f"Error al cambiar el estado del alumno: {e}")
        return False, "Ocurrió un error al cambiar el estado del alumno."
    finally:
        conn.close()


def obtener_grupos(incluir=None):
    """
    Retorna los grupos disponibles para inscripción (solo activos).

    `incluir`: id de un grupo adicional a incluir aunque esté inactivo. Se usa
    al editar un alumno cuyo grupo fue dado de baja, para que el combo muestre
    su grupo actual en lugar de reasignarlo en silencio.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        if incluir is None:
            cursor.execute(
                "SELECT * FROM Grupos WHERE estado = 'activo' ORDER BY nombre_grupo")
        else:
            cursor.execute(
                "SELECT * FROM Grupos WHERE estado = 'activo' OR id_grupo = ? "
                "ORDER BY nombre_grupo", (incluir,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
