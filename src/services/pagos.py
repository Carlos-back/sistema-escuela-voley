import pandas as pd
from datetime import datetime
from db.database import get_connection

def registrar_pago(id_alumno, mes, monto, metodo_pago):
    """Registra el pago de una cuota."""
    conn = get_connection()
    if not conn: return False
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Pagos (id_alumno, mes, monto, fecha_pago, metodo_pago, estado)
            VALUES (?, ?, ?, ?, ?, 'pagado')
            ON CONFLICT(id_alumno, mes) DO UPDATE SET 
                monto = excluded.monto,
                fecha_pago = excluded.fecha_pago,
                metodo_pago = excluded.metodo_pago,
                estado = 'pagado'
        """, (id_alumno, mes, monto, fecha_hoy, metodo_pago))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar pago: {e}")
        return False
    finally:
        conn.close()

def consultar_pagos(id_alumno=None, mes=None, estado=None):
    """Consulta pagos con filtros."""
    conn = get_connection()
    if not conn: return []
    
    query = """
        SELECT p.*, a.nombre, a.apellido, a.dni
        FROM Pagos p
        JOIN Alumnos a ON p.id_alumno = a.id_alumno
        WHERE 1=1
    """
    params = []
    
    if id_alumno:
        query += " AND p.id_alumno = ?"
        params.append(id_alumno)
    if mes:
        query += " AND p.mes = ?"
        params.append(mes)
    if estado:
        query += " AND p.estado = ?"
        params.append(estado)
        
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def detectar_pagos_atrasados():
    """
    Identifica alumnos que no han pagado el mes actual.
    Para simplificar, asume que 'mes' se guarda como 'MM-YYYY'.
    """
    mes_actual = datetime.now().strftime('%m-%Y')
    conn = get_connection()
    if not conn: return []
    
    try:
        cursor = conn.cursor()
        # Buscar alumnos activos que no tengan un registro de pago para el mes actual
        cursor.execute("""
            SELECT id_alumno, nombre, apellido, dni 
            FROM Alumnos 
            WHERE estado = 'activo' 
            AND id_alumno NOT IN (
                SELECT id_alumno FROM Pagos WHERE mes = ? AND estado = 'pagado'
            )
        """, (mes_actual,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def exportar_pagos_excel(path, mes=None):
    """Exporta el reporte de pagos a Excel."""
    try:
        pagos = consultar_pagos(mes=mes)
        if not pagos:
            return False, "No hay pagos registrados."
            
        df = pd.DataFrame(pagos)
        df.to_excel(path, index=False)
        return True, "Reporte exportado correctamente."
    except Exception as e:
        return False, f"Error al exportar: {e}"
