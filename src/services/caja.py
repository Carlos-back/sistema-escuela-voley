import pandas as pd
from db.database import get_connection

def registrar_movimiento(tipo, monto, descripcion, categoria=None, fecha=None):
    """Registra un ingreso o egreso en la caja."""
    conn = get_connection()
    if not conn: return False
    
    try:
        cursor = conn.cursor()
        if fecha:
            cursor.execute("""
                INSERT INTO Movimientos (tipo, monto, descripcion, categoria, fecha)
                VALUES (?, ?, ?, ?, ?)
            """, (tipo, monto, descripcion, categoria, fecha))
        else:
            cursor.execute("""
                INSERT INTO Movimientos (tipo, monto, descripcion, categoria)
                VALUES (?, ?, ?, ?)
            """, (tipo, monto, descripcion, categoria))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar movimiento: {e}")
        return False
    finally:
        conn.close()

def consultar_movimientos(desde=None, hasta=None, tipo=None):
    """Consulta movimientos de caja en un período."""
    conn = get_connection()
    if not conn: return []
    
    query = "SELECT * FROM Movimientos WHERE 1=1"
    params = []
    
    if desde:
        query += " AND fecha >= ?"
        params.append(desde)
    if hasta:
        query += " AND fecha <= ?"
        params.append(hasta)
    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
        
    query += " ORDER BY fecha DESC"
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def obtener_balance(desde=None, hasta=None):
    """Retorna el total de ingresos, egresos y el balance neto."""
    movs = consultar_movimientos(desde, hasta)
    ingresos = sum(m['monto'] for m in movs if m['tipo'] == 'ingreso')
    egresos = sum(m['monto'] for m in movs if m['tipo'] == 'egreso')
    return {
        'ingresos': ingresos,
        'egresos': egresos,
        'balance': ingresos - egresos
    }

def exportar_caja_excel(path, desde=None, hasta=None):
    """Exporta el reporte financiero a Excel."""
    try:
        movs = consultar_movimientos(desde, hasta)
        if not movs:
            return False, "No hay movimientos para exportar."
            
        df = pd.DataFrame(movs)
        df.to_excel(path, index=False)
        return True, "Reporte exportado correctamente."
    except Exception as e:
        return False, f"Error al exportar: {e}"
