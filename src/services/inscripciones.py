"""
Flamingo Sys — Servicio de Inscripciones (Sprint 5)

Inscripción = entidad transaccional: un alumno se inscribe en un grupo para
un período (año). Ciclo de estados: vigente -> anulada | finalizada.

  HU01 registrar_inscripcion   — alta con cupo y sin duplicados por período
  HU02 anular_inscripcion      — baja con motivo, libera el cupo
  HU03 listar_inscripciones    — listado con filtros + exportar_listado_excel
  HU04 informe_ocupacion       — informe por período + exportar_informe_pdf
"""

import datetime

from db.database import get_connection, normalizar_texto
from services.auditoria import registrar as registrar_auditoria

# ── Mensajes canónicos ───────────────────────────────────────────────
MSG_ALUMNO_OBLIGATORIO = "Debe seleccionar un alumno."
MSG_GRUPO_OBLIGATORIO = "Debe seleccionar un grupo."
MSG_PERIODO_INVALIDO = "El período debe ser el año en curso o el siguiente."
MSG_ALUMNO_INEXISTENTE = "El alumno seleccionado no existe."
MSG_ALUMNO_INACTIVO = "El alumno seleccionado no está activo."
MSG_GRUPO_INEXISTENTE = "El grupo seleccionado no existe."
MSG_GRUPO_INACTIVO = "El grupo seleccionado no está activo."
MSG_DUPLICADA = "El alumno ya tiene una inscripción vigente en el período {periodo}."
MSG_SIN_CUPO = "{grupo} no tiene cupo disponible ({ocupados}/{cupo})."
MSG_MOTIVO_OBLIGATORIO = "Debe seleccionar el motivo de la anulación."
MSG_DETALLE_CORTO = "Describí el motivo con al menos {minimo} caracteres."
MSG_NO_VIGENTE = "Solo se pueden anular inscripciones vigentes."

# Motivos de anulación: lista cerrada para poder agruparlos en el informe.
MOTIVOS_ANULACION = (
    "Cambio de horario",
    "Motivos económicos",
    "Lesión o salud",
    "Mudanza",
    "Falta de interés",
    "Error de carga",
    "Otro",
)
MOTIVO_BAJA_ALUMNO = "Baja del alumno"
MIN_CARACTERES_DETALLE = 10

# Umbral para marcar un grupo como "Casi completo" en el informe
UMBRAL_CASI_COMPLETO = 90


# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════
def anio_actual() -> int:
    return datetime.date.today().year


def periodos_habilitados():
    """Períodos en los que se puede inscribir: el año en curso y el siguiente."""
    actual = anio_actual()
    return [actual, actual + 1]


def contar_vigentes(cursor, id_grupo, periodo, excluir_id=None) -> int:
    """Cantidad de inscripciones vigentes de un grupo en un período."""
    sql = ("SELECT COUNT(*) FROM Inscripciones "
           "WHERE id_grupo = ? AND periodo = ? AND estado = 'vigente'")
    params = [id_grupo, periodo]
    if excluir_id is not None:
        sql += " AND id_inscripcion != ?"
        params.append(excluir_id)
    cursor.execute(sql, params)
    return cursor.fetchone()[0]


def validar_alta(cursor, id_alumno, id_grupo, periodo):
    """
    Reglas de negocio del alta (HU01), compartidas con el alta de alumno.
    Retorna None si todo es válido, o el mensaje de error.
    """
    if not id_alumno:
        return MSG_ALUMNO_OBLIGATORIO
    if not id_grupo:
        return MSG_GRUPO_OBLIGATORIO
    if periodo not in periodos_habilitados():
        return MSG_PERIODO_INVALIDO

    if id_alumno != "nuevo":
        cursor.execute("SELECT estado FROM Alumnos WHERE id_alumno = ?", (id_alumno,))
        alumno = cursor.fetchone()
        if not alumno:
            return MSG_ALUMNO_INEXISTENTE
        if alumno["estado"] != "activo":
            return MSG_ALUMNO_INACTIVO

    cursor.execute("SELECT nombre_grupo, estado, cupo_maximo FROM Grupos WHERE id_grupo = ?",
                   (id_grupo,))
    grupo = cursor.fetchone()
    if not grupo:
        return MSG_GRUPO_INEXISTENTE
    if grupo["estado"] != "activo":
        return MSG_GRUPO_INACTIVO

    if id_alumno != "nuevo":
        cursor.execute(
            "SELECT 1 FROM Inscripciones "
            "WHERE id_alumno = ? AND periodo = ? AND estado = 'vigente'",
            (id_alumno, periodo))
        if cursor.fetchone():
            return MSG_DUPLICADA.format(periodo=periodo)

    ocupados = contar_vigentes(cursor, id_grupo, periodo)
    if ocupados >= grupo["cupo_maximo"]:
        return MSG_SIN_CUPO.format(grupo=grupo["nombre_grupo"], ocupados=ocupados,
                                   cupo=grupo["cupo_maximo"])
    return None


def insertar_inscripcion(cursor, id_alumno, id_grupo, periodo, usuario):
    """
    Inserta la inscripción y la audita. No valida ni hace commit: lo usa
    registrar_inscripcion y el alta de alumno, dentro de su transacción.
    """
    cursor.execute(
        "INSERT INTO Inscripciones (id_alumno, id_grupo, periodo, usuario) "
        "VALUES (?, ?, ?, ?)",
        (id_alumno, id_grupo, periodo, usuario))
    id_inscripcion = cursor.lastrowid

    # El grupo del alumno refleja su inscripción del año en curso
    if periodo == anio_actual():
        cursor.execute("UPDATE Alumnos SET id_grupo = ? WHERE id_alumno = ?",
                       (id_grupo, id_alumno))

    registrar_auditoria(
        accion="INSERT", entidad="Inscripciones", id_entidad=id_inscripcion,
        datos={"id_alumno": id_alumno, "id_grupo": id_grupo, "periodo": periodo},
        usuario=usuario, conn=cursor.connection,
    )
    return id_inscripcion


def _anular_en_tx(cursor, inscripcion, motivo, detalle, usuario):
    """Pasa una inscripción vigente a anulada y la audita (sin commit)."""
    hoy = datetime.date.today().isoformat()
    cursor.execute(
        "UPDATE Inscripciones SET estado = 'anulada', fecha_anulacion = ?, "
        "motivo_anulacion = ?, detalle_anulacion = ? WHERE id_inscripcion = ?",
        (hoy, motivo, detalle, inscripcion["id_inscripcion"]))
    registrar_auditoria(
        accion="UPDATE", entidad="Inscripciones",
        id_entidad=inscripcion["id_inscripcion"],
        datos={"cambios": {"estado": {"anterior": "vigente", "nuevo": "anulada"}},
               "motivo": motivo, "detalle": detalle},
        usuario=usuario, conn=cursor.connection,
    )


# ══════════════════════════════════════════════════════════════════
# HU01 — Registrar inscripción
# ══════════════════════════════════════════════════════════════════
def registrar_inscripcion(id_alumno, id_grupo, periodo, usuario=None):
    """
    Inscribe un alumno activo en un grupo activo para un período.

    Reglas:
      - el período es el año en curso o el siguiente.
      - el alumno no puede tener otra inscripción vigente en ese período.
      - el grupo debe tener cupo (vigentes < cupo_maximo).
      - alta + auditoría en una sola transacción.

    Retorna (exito: bool, mensaje: str).
    """
    try:
        periodo = int(periodo)
    except (TypeError, ValueError):
        return False, MSG_PERIODO_INVALIDO

    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()
        error = validar_alta(cursor, id_alumno, id_grupo, periodo)
        if error:
            return False, error

        insertar_inscripcion(cursor, id_alumno, id_grupo, periodo, usuario)
        conn.commit()

        cursor.execute(
            "SELECT a.nombre, a.apellido, g.nombre_grupo FROM Alumnos a, Grupos g "
            "WHERE a.id_alumno = ? AND g.id_grupo = ?", (id_alumno, id_grupo))
        fila = cursor.fetchone()
        return True, (f"{fila['nombre']} {fila['apellido']} quedó inscripto en "
                      f"{fila['nombre_grupo']} para el período {periodo}.")
    except Exception as e:
        conn.rollback()
        print(f"Error al registrar inscripción: {e}")
        return False, "Ocurrió un error al registrar la inscripción."
    finally:
        conn.close()


def obtener_alumnos_activos():
    """Alumnos activos para el combo del formulario, ordenados por apellido."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_alumno, nombre, apellido, dni FROM Alumnos "
            "WHERE estado = 'activo' ORDER BY apellido, nombre")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def obtener_grupos_con_cupo(periodo):
    """Grupos activos con su cupo y la cantidad de vigentes en el período."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.id_grupo, g.nombre_grupo, g.horario, g.cupo_maximo,
                   (SELECT COUNT(*) FROM Inscripciones i
                     WHERE i.id_grupo = g.id_grupo AND i.periodo = ?
                       AND i.estado = 'vigente') AS ocupados
            FROM Grupos g
            WHERE g.estado = 'activo'
            ORDER BY g.nombre_grupo
        """, (periodo,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# HU02 — Anular inscripción
# ══════════════════════════════════════════════════════════════════
def validar_motivo(motivo, detalle):
    """Retorna None si el motivo es válido, o el mensaje de error."""
    if motivo not in MOTIVOS_ANULACION:
        return MSG_MOTIVO_OBLIGATORIO
    if motivo == "Otro" and len((detalle or "").strip()) < MIN_CARACTERES_DETALLE:
        return MSG_DETALLE_CORTO.format(minimo=MIN_CARACTERES_DETALLE)
    return None


def anular_inscripcion(id_inscripcion, motivo, detalle=None, usuario=None):
    """
    Anula una inscripción vigente (baja lógica: nunca se borra).

    Reglas:
      - solo desde estado 'vigente'.
      - motivo obligatorio de la lista; si es 'Otro', detalle de 10+ caracteres.
      - guarda fecha y motivo, libera el cupo y audita en la misma transacción.

    Retorna (exito: bool, mensaje: str).
    """
    detalle = (detalle or "").strip() or None
    error = validar_motivo(motivo, detalle)
    if error:
        return False, error

    conn = get_connection()
    if not conn:
        return False, "No se pudo conectar con la base de datos."

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.id_inscripcion, i.estado, a.nombre, a.apellido, g.nombre_grupo
            FROM Inscripciones i
            JOIN Alumnos a ON a.id_alumno = i.id_alumno
            JOIN Grupos g ON g.id_grupo = i.id_grupo
            WHERE i.id_inscripcion = ?
        """, (id_inscripcion,))
        insc = cursor.fetchone()
        if not insc:
            return False, "La inscripción no existe."
        if insc["estado"] != "vigente":
            return False, MSG_NO_VIGENTE

        _anular_en_tx(cursor, insc, motivo, detalle, usuario)
        conn.commit()
        return True, (f"Inscripción de {insc['nombre']} {insc['apellido']} en "
                      f"{insc['nombre_grupo']} anulada. Se liberó un lugar del cupo.")
    except Exception as e:
        conn.rollback()
        print(f"Error al anular inscripción: {e}")
        return False, "Ocurrió un error al anular la inscripción."
    finally:
        conn.close()


def anular_vigentes_de_alumno(cursor, id_alumno, usuario):
    """
    Al desactivar un alumno se anulan sus inscripciones vigentes para liberar
    el cupo. Corre dentro de la transacción de la baja del alumno.
    """
    cursor.execute(
        "SELECT id_inscripcion FROM Inscripciones "
        "WHERE id_alumno = ? AND estado = 'vigente'", (id_alumno,))
    for fila in cursor.fetchall():
        _anular_en_tx(cursor, fila, MOTIVO_BAJA_ALUMNO, None, usuario)


# ══════════════════════════════════════════════════════════════════
# HU03 — Listado de inscripciones
# ══════════════════════════════════════════════════════════════════
def periodos_registrados():
    """Períodos con inscripciones más los habilitados, del más reciente al más viejo."""
    conn = get_connection()
    if not conn:
        return periodos_habilitados()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT periodo FROM Inscripciones")
        periodos = {r[0] for r in cursor.fetchall()} | set(periodos_habilitados())
        return sorted(periodos, reverse=True)
    finally:
        conn.close()


def listar_inscripciones(periodo=None, id_grupo=None, estado=None, busqueda=""):
    """
    Lista inscripciones con alumno y grupo, con filtros opcionales.

    periodo  : año o None (todos)
    id_grupo : id o None (todos)
    estado   : 'vigente' | 'anulada' | 'finalizada' | None (todos)
    busqueda : nombre, apellido o DNI, sin distinguir acentos ni mayúsculas
    """
    conn = get_connection()
    if not conn:
        return []

    query = """
        SELECT i.*, a.nombre, a.apellido, a.dni, g.nombre_grupo, g.horario
        FROM Inscripciones i
        JOIN Alumnos a ON a.id_alumno = i.id_alumno
        JOIN Grupos g ON g.id_grupo = i.id_grupo
    """
    condiciones, params = [], []
    if periodo is not None:
        condiciones.append("i.periodo = ?")
        params.append(int(periodo))
    if id_grupo is not None:
        condiciones.append("i.id_grupo = ?")
        params.append(id_grupo)
    if estado in ("vigente", "anulada", "finalizada"):
        condiciones.append("i.estado = ?")
        params.append(estado)

    busqueda = (busqueda or "").strip()
    if busqueda:
        condiciones.append(
            "(normalizar(a.nombre) LIKE ? OR normalizar(a.apellido) LIKE ? OR a.dni LIKE ?"
            " OR normalizar(a.nombre || ' ' || a.apellido) LIKE ?"
            " OR normalizar(a.apellido || ' ' || a.nombre) LIKE ?)")
        term = f"%{normalizar_texto(busqueda)}%"
        params.extend([term] * 5)

    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " ORDER BY i.periodo DESC, g.nombre_grupo, a.apellido, a.nombre"

    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


COLUMNAS_LISTADO = ("Alumno", "DNI", "Grupo", "Período", "Fecha", "Estado")


def fila_listado(insc: dict):
    """Valores de una inscripción tal como se ven en el listado."""
    return (
        f"{insc['apellido']}, {insc['nombre']}",
        insc["dni"],
        insc["nombre_grupo"],
        insc["periodo"],
        insc["fecha_inscripcion"],
        insc["estado"].capitalize(),
    )


def exportar_listado_excel(path, inscripciones, filtros_texto=""):
    """
    Exporta el listado (las mismas filas y columnas que en pantalla) a .xlsx.
    Retorna (exito: bool, mensaje: str).
    """
    if not inscripciones:
        return False, "No hay inscripciones para exportar."
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = "Inscripciones"
        ws.append(["Flamingo Sys — Listado de inscripciones"])
        ws["A1"].font = Font(bold=True, size=14)
        ws.append([f"Filtros: {filtros_texto or 'ninguno'}"])
        ws.append([f"Generado: {datetime.datetime.now():%d/%m/%Y %H:%M}"])
        ws.append([])
        ws.append(list(COLUMNAS_LISTADO))
        encabezado = ws.max_row
        for celda in ws[encabezado]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="E91E8C")
        for insc in inscripciones:
            ws.append(list(fila_listado(insc)))
        for col, ancho in zip("ABCDEF", (32, 12, 22, 10, 14, 12)):
            ws.column_dimensions[col].width = ancho
        ws.append([])
        ws.append([f"Total: {len(inscripciones)} inscripciones"])
        wb.save(path)
        return True, f"Se exportaron {len(inscripciones)} inscripciones."
    except PermissionError:
        return False, "No se pudo guardar: el archivo está abierto en otro programa."
    except Exception as e:
        print(f"Error exportando Excel: {e}")
        return False, "Ocurrió un error al exportar el listado."


# ══════════════════════════════════════════════════════════════════
# HU04 — Informe de ocupación de grupos por período
# ══════════════════════════════════════════════════════════════════
def estado_ocupacion(porcentaje: float) -> str:
    if porcentaje >= 100:
        return "Completo"
    if porcentaje >= UMBRAL_CASI_COMPLETO:
        return "Casi completo"
    return "Disponible"


def informe_ocupacion(periodo):
    """
    Arma el informe de ocupación del período.

    Retorna un dict:
      periodo, hay_datos,
      grupos   : [{nombre_grupo, horario, cupo, vigentes, libres, porcentaje,
                   estado, altas, anuladas}]  (grupos activos + los que tuvieron
                   inscripciones en el período aunque hoy estén inactivos)
      totales  : {cupo, vigentes, libres, porcentaje, altas, anuladas}
      motivos  : [{motivo, cantidad}] de las anulaciones del período
    """
    periodo = int(periodo)
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.id_grupo, g.nombre_grupo, g.horario, g.cupo_maximo AS cupo,
                   g.estado AS estado_grupo,
                   COALESCE(SUM(i.estado IN ('vigente', 'finalizada')), 0) AS vigentes,
                   COUNT(i.id_inscripcion) AS altas,
                   COALESCE(SUM(i.estado = 'anulada'), 0) AS anuladas
            FROM Grupos g
            LEFT JOIN Inscripciones i ON i.id_grupo = g.id_grupo AND i.periodo = ?
            GROUP BY g.id_grupo
            HAVING g.estado = 'activo' OR COUNT(i.id_inscripcion) > 0
            ORDER BY g.nombre_grupo
        """, (periodo,))
        grupos = []
        for r in cursor.fetchall():
            g = dict(r)
            g["libres"] = max(g["cupo"] - g["vigentes"], 0)
            g["porcentaje"] = round(g["vigentes"] * 100 / g["cupo"], 1) if g["cupo"] else 0
            g["estado"] = estado_ocupacion(g["porcentaje"])
            grupos.append(g)

        cupo = sum(g["cupo"] for g in grupos)
        vigentes = sum(g["vigentes"] for g in grupos)
        totales = {
            "cupo": cupo,
            "vigentes": vigentes,
            "libres": sum(g["libres"] for g in grupos),
            "porcentaje": round(vigentes * 100 / cupo, 1) if cupo else 0,
            "altas": sum(g["altas"] for g in grupos),
            "anuladas": sum(g["anuladas"] for g in grupos),
        }

        cursor.execute("""
            SELECT motivo_anulacion AS motivo, COUNT(*) AS cantidad
            FROM Inscripciones
            WHERE periodo = ? AND estado = 'anulada'
            GROUP BY motivo_anulacion
            ORDER BY cantidad DESC, motivo
        """, (periodo,))
        motivos = [dict(r) for r in cursor.fetchall()]

        return {
            "periodo": periodo,
            "hay_datos": totales["altas"] > 0,
            "grupos": grupos,
            "totales": totales,
            "motivos": motivos,
        }
    finally:
        conn.close()


def exportar_informe_pdf(path, informe, usuario=None):
    """
    Genera el PDF del informe con encabezado (escuela, período, fecha de
    emisión y usuario) y el mismo contenido que la pantalla.
    Retorna (exito: bool, mensaje: str).
    """
    if not informe or not informe.get("hay_datos"):
        return False, "No hay inscripciones para el período seleccionado."
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                        Table, TableStyle)
    except ImportError:
        return False, "Falta la librería reportlab (pip install -r requirements.txt)."

    rosa = colors.HexColor("#E91E8C")
    estilos = getSampleStyleSheet()
    emitido = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(2 * cm, 1.2 * cm,
                          f"Flamingo Sys · Emitido el {emitido} por {usuario or '—'}")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
        canvas.restoreState()

    def estilo_tabla(filas_totales=0):
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), rosa),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ]
        if filas_totales:
            estilo += [("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                       ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FDF2F8"))]
        return TableStyle(estilo)

    t = informe["totales"]
    elementos = [
        Paragraph("Flamingo Sys — Escuela de Vóley", estilos["Title"]),
        Paragraph(f"Informe de ocupación de grupos · Período {informe['periodo']}",
                  estilos["Heading2"]),
        Paragraph(f"Ocupación general: <b>{t['porcentaje']}%</b> "
                  f"({t['vigentes']} de {t['cupo']} lugares). "
                  f"Altas del período: {t['altas']}. Anulaciones: {t['anuladas']}.",
                  estilos["Normal"]),
        Spacer(1, 0.5 * cm),
        Paragraph("Ocupación por grupo", estilos["Heading3"]),
    ]

    filas = [["Grupo", "Horario", "Cupo", "Inscriptos", "Libres", "Ocupación", "Estado"]]
    for g in informe["grupos"]:
        filas.append([g["nombre_grupo"], g["horario"], g["cupo"], g["vigentes"],
                      g["libres"], f"{g['porcentaje']}%", g["estado"]])
    filas.append(["Total", "", t["cupo"], t["vigentes"], t["libres"],
                  f"{t['porcentaje']}%", ""])
    tabla = Table(filas, colWidths=[3.2 * cm, 4.6 * cm, 1.4 * cm, 2 * cm,
                                    1.5 * cm, 2 * cm, 2.6 * cm], repeatRows=1)
    tabla.setStyle(estilo_tabla(filas_totales=1))
    elementos += [tabla, Spacer(1, 0.6 * cm),
                  Paragraph("Movimientos del período", estilos["Heading3"])]

    filas_mov = [["Grupo", "Altas", "Anuladas"]]
    for g in informe["grupos"]:
        filas_mov.append([g["nombre_grupo"], g["altas"], g["anuladas"]])
    filas_mov.append(["Total", t["altas"], t["anuladas"]])
    tabla_mov = Table(filas_mov, colWidths=[6 * cm, 3 * cm, 3 * cm])
    tabla_mov.setStyle(estilo_tabla(filas_totales=1))
    elementos += [tabla_mov, Spacer(1, 0.6 * cm),
                  Paragraph("Anulaciones por motivo", estilos["Heading3"])]

    if informe["motivos"]:
        filas_mot = [["Motivo", "Cantidad"]] + [[m["motivo"], m["cantidad"]]
                                                for m in informe["motivos"]]
        tabla_mot = Table(filas_mot, colWidths=[6 * cm, 3 * cm])
        tabla_mot.setStyle(estilo_tabla())
        elementos.append(tabla_mot)
    else:
        elementos.append(Paragraph("No hubo anulaciones en el período.", estilos["Normal"]))

    try:
        doc = SimpleDocTemplate(path, pagesize=A4, topMargin=1.8 * cm, bottomMargin=2 * cm,
                                title=f"Informe de ocupación {informe['periodo']}")
        doc.build(elementos, onFirstPage=pie, onLaterPages=pie)
        return True, "Informe exportado correctamente."
    except PermissionError:
        return False, "No se pudo guardar: el archivo está abierto en otro programa."
    except Exception as e:
        print(f"Error exportando PDF: {e}")
        return False, "Ocurrió un error al exportar el informe."
