"""
Flamingo Sys — Servicio de Grupos
Lógica de negocio para el alta y consulta de grupos (HU01).
"""

from db.database import get_connection
from services.auditoria import registrar as registrar_auditoria

# ── Mensajes canónicos de validación (HU06 — reglas sistémicas) ──────
MSG_NOMBRE_OBLIGATORIO = "El nombre es obligatorio"
MSG_HORARIO_OBLIGATORIO = "El horario es obligatorio"
MSG_NOMBRE_DUPLICADO = "El nombre del grupo ya existe entre los grupos activos"
MSG_CUPO_OBLIGATORIO = "El cupo máximo es obligatorio"
MSG_CUPO_FORMATO = "El cupo máximo debe ser un número entero entre 1 y 100"
MSG_CUPO_MENOR = "El cupo no puede ser menor a los {vigentes} inscriptos vigentes del período {periodo}"
CUPO_MAXIMO_PERMITIDO = 100


def _validar_cupo(cupo):
    """Retorna (cupo: int | None, error: str | None)."""
    texto = str(cupo if cupo is not None else "").strip()
    if not texto:
        return None, MSG_CUPO_OBLIGATORIO
    if not texto.isdigit() or not 1 <= int(texto) <= CUPO_MAXIMO_PERMITIDO:
        return None, MSG_CUPO_FORMATO
    return int(texto), None


def _vigentes_maximos(cursor, id_grupo):
    """(vigentes, periodo) del período con más inscripciones vigentes del grupo."""
    cursor.execute(
        "SELECT periodo, COUNT(*) AS n FROM Inscripciones "
        "WHERE id_grupo = ? AND estado = 'vigente' "
        "GROUP BY periodo ORDER BY n DESC LIMIT 1", (id_grupo,))
    fila = cursor.fetchone()
    return (fila["n"], fila["periodo"]) if fila else (0, None)


def _normalizar_y_validar(nombre, horario, descripcion):
    """
    Normaliza (trim) y valida los campos obligatorios de un grupo (HU06).
    Regla sistémica única usada por el alta y la edición.
    Retorna (valores: dict | None, error: str | None).
    """
    nombre = (nombre or "").strip()
    horario = (horario or "").strip()
    descripcion = (descripcion or "").strip() or None

    if not nombre:
        return None, MSG_NOMBRE_OBLIGATORIO
    if not horario:
        return None, MSG_HORARIO_OBLIGATORIO

    return {"nombre": nombre, "horario": horario, "descripcion": descripcion}, None


def _nombre_duplicado_activo(cursor, nombre, excluir_id=None):
    """
    True si ya existe un grupo ACTIVO con ese nombre (case-insensitive).
    `excluir_id` permite ignorar el propio registro (edición/reactivación).
    """
    if excluir_id is None:
        cursor.execute(
            "SELECT 1 FROM Grupos WHERE LOWER(nombre_grupo) = LOWER(?) AND estado = 'activo'",
            (nombre,),
        )
    else:
        cursor.execute(
            "SELECT 1 FROM Grupos "
            "WHERE LOWER(nombre_grupo) = LOWER(?) AND estado = 'activo' AND id_grupo != ?",
            (nombre, excluir_id),
        )
    return cursor.fetchone() is not None


def crear_grupo(nombre, horario, descripcion=None, usuario=None, cupo_maximo=20):
    """
    Crea un nuevo grupo (KAN-25).

    Reglas de negocio:
      - nombre y horario son obligatorios.
      - el nombre debe ser único entre los grupos activos (case-insensitive).
      - se inserta con estado 'activo' por defecto.
      - se registra la operación en Auditoria (misma transacción).

    Retorna una tupla (exito: bool, mensaje: str).
    """
    valores, error = _normalizar_y_validar(nombre, horario, descripcion)
    if error:
        return False, error
    nombre, horario, descripcion = valores["nombre"], valores["horario"], valores["descripcion"]
    cupo_maximo, error = _validar_cupo(cupo_maximo)
    if error:
        return False, error

    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()

        # Unicidad entre grupos activos (regla sistémica HU06)
        if _nombre_duplicado_activo(cursor, nombre):
            return False, MSG_NOMBRE_DUPLICADO

        cursor.execute(
            """
            INSERT INTO Grupos (nombre_grupo, horario, descripcion, cupo_maximo, estado)
            VALUES (?, ?, ?, ?, 'activo')
            """,
            (nombre, horario, descripcion, cupo_maximo),
        )
        id_grupo = cursor.lastrowid

        # Auditoría dentro de la misma transacción
        registrar_auditoria(
            accion="INSERT",
            entidad="Grupos",
            id_entidad=id_grupo,
            datos={"nombre_grupo": nombre, "horario": horario, "descripcion": descripcion,
                   "cupo_maximo": cupo_maximo},
            usuario=usuario,
            conn=conn,
        )

        conn.commit()
        return True, "Grupo creado correctamente."
    except Exception as e:
        print(f"Error al crear grupo: {e}")
        return False, "Ocurrió un error al crear el grupo."
    finally:
        conn.close()


def editar_grupo(id_grupo, nombre, horario, descripcion=None, usuario=None, cupo_maximo=None):
    """
    Modifica un grupo existente (KAN-28).

    Reglas de negocio:
      - nombre y horario son obligatorios.
      - el nuevo nombre debe ser único entre grupos activos, EXCLUYENDO el
        propio registro.
      - dirty checking: solo se actualizan los campos que cambiaron realmente;
        si no hubo cambios, no se escribe ni se audita.
      - se registra en Auditoria los campos modificados con su valor
        anterior y nuevo.

    Retorna una tupla (exito: bool, mensaje: str).
    """
    valores, error = _normalizar_y_validar(nombre, horario, descripcion)
    if error:
        return False, error
    nombre, horario, descripcion = valores["nombre"], valores["horario"], valores["descripcion"]

    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT nombre_grupo, horario, descripcion, cupo_maximo FROM Grupos WHERE id_grupo = ?",
            (id_grupo,),
        )
        actual = cursor.fetchone()
        if not actual:
            return False, "El grupo no existe."
        actual = dict(actual)

        # Unicidad del nuevo nombre entre activos, excluyendo el propio registro (HU06)
        if _nombre_duplicado_activo(cursor, nombre, excluir_id=id_grupo):
            return False, MSG_NOMBRE_DUPLICADO

        # Cupo (Sprint 5): no puede quedar por debajo de los inscriptos vigentes
        if cupo_maximo is None:
            cupo_maximo = actual["cupo_maximo"]
        cupo_maximo, error = _validar_cupo(cupo_maximo)
        if error:
            return False, error
        vigentes, periodo = _vigentes_maximos(cursor, id_grupo)
        if cupo_maximo < vigentes:
            return False, MSG_CUPO_MENOR.format(vigentes=vigentes, periodo=periodo)

        # Dirty checking: detectar solo los campos que cambiaron
        nuevos = {"nombre_grupo": nombre, "horario": horario, "descripcion": descripcion,
                  "cupo_maximo": cupo_maximo}
        cambios = {
            campo: {"anterior": actual[campo], "nuevo": valor}
            for campo, valor in nuevos.items()
            if (actual[campo] or None) != (valor or None)
        }
        if not cambios:
            return True, "No se realizaron cambios."

        set_clause = ", ".join(f"{campo} = ?" for campo in cambios)
        params = [nuevos[campo] for campo in cambios] + [id_grupo]
        cursor.execute(f"UPDATE Grupos SET {set_clause} WHERE id_grupo = ?", params)

        # Auditoría con valores anterior/nuevo, en la misma transacción
        registrar_auditoria(
            accion="UPDATE",
            entidad="Grupos",
            id_entidad=id_grupo,
            datos={"cambios": cambios},
            usuario=usuario,
            conn=conn,
        )

        conn.commit()
        return True, "Cambios guardados correctamente."
    except Exception as e:
        print(f"Error al editar grupo: {e}")
        return False, "Ocurrió un error al guardar los cambios."
    finally:
        conn.close()


def desactivar_grupo(id_grupo, usuario=None):
    """
    Baja lógica de un grupo (KAN-31).

    Reglas:
      - no se puede desactivar si tiene alumnos con estado 'activo'.
      - nunca se borra físicamente: solo cambia estado a 'inactivo'.
      - se registra la operación en Auditoria.

    Retorna (exito: bool, mensaje: str).
    """
    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT nombre_grupo, estado FROM Grupos WHERE id_grupo = ?", (id_grupo,))
        grupo = cursor.fetchone()
        if not grupo:
            return False, "El grupo no existe."
        grupo = dict(grupo)

        if grupo["estado"] == "inactivo":
            return False, "El grupo ya está inactivo."

        # Bloqueo: no desactivar si tiene alumnos activos
        cursor.execute(
            "SELECT COUNT(*) FROM Alumnos WHERE id_grupo = ? AND estado = 'activo'",
            (id_grupo,),
        )
        alumnos_activos = cursor.fetchone()[0]
        vigentes, _periodo = _vigentes_maximos(cursor, id_grupo)
        if vigentes > 0 and alumnos_activos == 0:
            return False, (f"No se puede desactivar: el grupo tiene {vigentes} "
                           f"inscripción(es) vigente(s).")
        if alumnos_activos > 0:
            return False, (
                f"No se puede desactivar: el grupo tiene {alumnos_activos} "
                f"alumno(s) activo(s)."
            )

        cursor.execute("UPDATE Grupos SET estado = 'inactivo' WHERE id_grupo = ?", (id_grupo,))
        registrar_auditoria(
            accion="UPDATE",
            entidad="Grupos",
            id_entidad=id_grupo,
            datos={"cambios": {"estado": {"anterior": "activo", "nuevo": "inactivo"}}},
            usuario=usuario,
            conn=conn,
        )
        conn.commit()
        return True, f"Grupo '{grupo['nombre_grupo']}' desactivado correctamente."
    except Exception as e:
        print(f"Error al desactivar grupo: {e}")
        return False, "Ocurrió un error al desactivar el grupo."
    finally:
        conn.close()


def reactivar_grupo(id_grupo, usuario=None):
    """
    Reactiva un grupo inactivo (KAN-31).

    Reglas:
      - solo se reactiva si no hay otro grupo ACTIVO con el mismo nombre.
      - se registra la operación en Auditoria.

    Retorna (exito: bool, mensaje: str).
    """
    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT nombre_grupo, estado FROM Grupos WHERE id_grupo = ?", (id_grupo,))
        grupo = cursor.fetchone()
        if not grupo:
            return False, "El grupo no existe."
        grupo = dict(grupo)

        if grupo["estado"] == "activo":
            return False, "El grupo ya está activo."

        # Unicidad entre activos, excluyendo el propio registro (regla sistémica HU06)
        if _nombre_duplicado_activo(cursor, grupo["nombre_grupo"], excluir_id=id_grupo):
            return False, MSG_NOMBRE_DUPLICADO

        cursor.execute("UPDATE Grupos SET estado = 'activo' WHERE id_grupo = ?", (id_grupo,))
        registrar_auditoria(
            accion="UPDATE",
            entidad="Grupos",
            id_entidad=id_grupo,
            datos={"cambios": {"estado": {"anterior": "inactivo", "nuevo": "activo"}}},
            usuario=usuario,
            conn=conn,
        )
        conn.commit()
        return True, f"Grupo '{grupo['nombre_grupo']}' reactivado correctamente."
    except Exception as e:
        print(f"Error al reactivar grupo: {e}")
        return False, "Ocurrió un error al reactivar el grupo."
    finally:
        conn.close()


def obtener_detalle_grupo(id_grupo):
    """
    Retorna el detalle de un grupo (HU05) incluyendo la cantidad de alumnos
    activos vinculados. Devuelve None si el grupo no existe.
    """
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Grupos WHERE id_grupo = ?", (id_grupo,))
        row = cursor.fetchone()
        if not row:
            return None
        grupo = dict(row)
        cursor.execute(
            """
            SELECT id_alumno, nombre, apellido, dni
            FROM Alumnos
            WHERE id_grupo = ? AND estado = 'activo'
            ORDER BY apellido, nombre
            """,
            (id_grupo,),
        )
        alumnos = [dict(r) for r in cursor.fetchall()]
        grupo["alumnos"] = alumnos
        grupo["alumnos_activos"] = len(alumnos)
        return grupo
    finally:
        conn.close()


def listar_grupos(incluir_inactivos=False):
    """Lista los grupos. Por defecto, solo los activos."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        if incluir_inactivos:
            cursor.execute("SELECT * FROM Grupos ORDER BY nombre_grupo")
        else:
            cursor.execute(
                "SELECT * FROM Grupos WHERE estado = 'activo' ORDER BY nombre_grupo"
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
