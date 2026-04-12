from db.database import get_connection

def registrar_insumo(nombre, cantidad, minimo_stock=5, descripcion=None):
    """Agrega un nuevo insumo al stock."""
    conn = get_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Insumos (nombre, cantidad, minimo_stock, descripcion)
            VALUES (?, ?, ?, ?)
        """, (nombre, cantidad, minimo_stock, descripcion))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar insumo: {e}")
        return False
    finally:
        conn.close()

def listar_insumos():
    """Retorna todos los insumos."""
    conn = get_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Insumos")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def actualizar_stock(id_insumo, nueva_cantidad):
    """Actualiza la cantidad de un insumo."""
    conn = get_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Insumos SET cantidad = ? WHERE id_insumo = ?", (nueva_cantidad, id_insumo))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al actualizar stock: {e}")
        return False
    finally:
        conn.close()

def alertas_reposicion():
    """Retorna insumos cuyo stock está por debajo del mínimo."""
    conn = get_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Insumos WHERE cantidad <= minimo_stock")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def eliminar_insumo(id_insumo):
    """Elimina un insumo del stock."""
    conn = get_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Insumos WHERE id_insumo = ?", (id_insumo,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al eliminar insumo: {e}")
        return False
    finally:
        conn.close()
