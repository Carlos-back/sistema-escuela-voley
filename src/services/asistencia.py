import pandas as pd
from datetime import datetime
from db.database import get_connection

def registrar_asistencia(id_alumno, fecha, estado):
    """Registra o actualiza la asistencia de un alumno para una fecha."""
    conn = get_connection()
    if not conn: return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Asistencias (id_alumno, fecha_clase, estado)
            VALUES (?, ?, ?)
            ON CONFLICT(id_alumno, fecha_clase) DO UPDATE SET estado = excluded.estado
        """, (id_alumno, fecha, estado))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar asistencia: {e}")
        return False
    finally:
        conn.close()

def consultar_asistencia(id_grupo=None, fecha=None, id_alumno=None):
    """Consulta asistencia con filtros."""
    conn = get_connection()
    if not conn: return []
    
    query = """
        SELECT a.nombre, a.apellido, g.nombre_grupo, asist.fecha_clase, asist.estado
        FROM Asistencias asist
        JOIN Alumnos a ON asist.id_alumno = a.id_alumno
        JOIN Grupos g ON a.id_grupo = g.id_grupo
        WHERE 1=1
    """
    params = []
    
    if id_grupo:
        query += " AND a.id_grupo = ?"
        params.append(id_grupo)
    if fecha:
        query += " AND asist.fecha_clase = ?"
        params.append(fecha)
    if id_alumno:
        query += " AND a.id_alumno = ?"
        params.append(id_alumno)
        
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def exportar_asistencia_excel(path, id_grupo=None, mes=None):
    """Genera un reporte de asistencia en Excel."""
    try:
        asistencias = consultar_asistencia(id_grupo=id_grupo)
        if not asistencias:
            return False, "No hay datos para exportar."
            
        df = pd.DataFrame(asistencias)
        
        # Filtrar por mes si se solicita (fecha_clase está en formato YYYY-MM-DD)
        if mes:
            df['fecha_clase'] = pd.to_datetime(df['fecha_clase'])
            df = df[df['fecha_clase'].dt.strftime('%m') == mes]
            
        df.to_excel(path, index=False)
        return True, "Reporte generado con éxito."
    except Exception as e:
        return False, f"Error al exportar: {e}"
