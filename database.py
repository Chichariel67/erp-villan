import sqlite3

conn = sqlite3.connect("villan.db")

cursor = conn.cursor()

# ==========================
# TABLA VENTAS
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS ventas(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    mes TEXT,
    anio INTEGER,
    sku TEXT,
    producto TEXT,
    categoria TEXT,
    talla TEXT,
    canal TEXT,
    cliente TEXT,
    precio REAL,
    costo REAL,
    utilidad REAL
)
""")

# ==========================
# TABLA GASTOS
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS gastos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    mes TEXT,
    anio INTEGER,
    concepto TEXT,
    categoria TEXT,
    responsable TEXT,
    monto REAL
)
""")

# ==========================
# TABLA INVENTARIO
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventario(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto TEXT,
    categoria TEXT,
    talla TEXT,
    stock INTEGER
)
""")

conn.commit()
conn.close()

print("Base de datos creada correctamente")