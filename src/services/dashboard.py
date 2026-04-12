from db.database import get_connection
from datetime import datetime, timedelta

def obtener_resumen_dashboard():
    """
    Recopila datos clave para la vista principal.
    - Alumnos activos totales
    - Recaudación semanal (últimos 7 días)
    - Asistencia promedio semanal
    """
    conn = get_connection()
    if not conn: return {}
    
    try:
        cursor = conn.cursor()
        
        # Alumnos activos
        cursor.execute("SELECT COUNT(*) FROM Alumnos WHERE estado = 'activo'")
        total_alumnos = cursor.fetchone()[0]
        
        # Recaudación semanal (basada en fecha_pago de los últimos 7 días)
        fecha_limite = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("SELECT SUM(monto) FROM Pagos WHERE fecha_pago >= ?", (fecha_limite,))
        recaudacion_semanal = cursor.fetchone()[0] or 0.0
        
        # Asistencia semanal (promedio de presentes por clase en los últimos 7 días)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Asistencias 
            WHERE fecha_clase >= ? AND estado = 'presente'
        """, (fecha_limite,))
        asistencias_semanales = cursor.fetchone()[0]
        
        return {
            'total_alumnos': total_alumnos,
            'recaudacion_semanal': recaudacion_semanal,
            'asistencias_semanales': asistencias_semanales,
            'fecha_actualización': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
    finally:
        conn.close()

def obtener_proximas_clases():
    """Mock de próximas clases basado en los horarios de los grupos."""
    # En una versión real, esto podría venir de un calendario de eventos.
    return [
        {'grupo': 'Infantil', 'horario': 'Lunes 18:00', 'lugar': 'Cancha 1'},
        {'grupo': 'Adultos', 'horario': 'Lunes 20:30', 'lugar': 'Cancha Principal'},
        {'grupo': 'Juvenil', 'horario': 'Martes 19:00', 'lugar': 'Cancha 2'},
    ]
def obtener_ingresos_mensuales():
    """Obtiene ingresos agrupados por mes para los últimos 6 meses."""
    conn = get_connection()
    if not conn:
        return {"labels": [], "valores": []}
    
    try:
        cursor = conn.cursor()
        # Query para agrupar por mes (YYYY-MM)
        cursor.execute("""
            SELECT strftime('%m', fecha_pago) as mes, SUM(monto) 
            FROM Pagos 
            WHERE fecha_pago >= date('now', '-6 months')
            AND estado = 'pagado'
            GROUP BY mes
            ORDER BY fecha_pago ASC
        """)
        rows = cursor.fetchall()
        
        meses_nombres = {
            "01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr", "05": "May", "06": "Jun",
            "07": "Jul", "08": "Ago", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic"
        }
        
        labels = [meses_nombres.get(r[0], r[0]) for r in rows]
        valores = [r[1] for r in rows]
        
        # Si no hay datos, devolver algo coherente para el gráfico
        if not labels:
            labels = ["Sin datos"]
            valores = [0]
            
        return {"labels": labels, "valores": valores}
    finally:
        conn.close()
