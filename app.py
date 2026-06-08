import streamlit as st
import pandas as pd
import io
import sqlite3
from datetime import datetime
import extra_streamlit_components as stx  # Sistema de cookies
import time

# =====================================
# CONFIGURACIÓN (¡SIEMPRE PRIMERO!)
# =====================================
st.set_page_config(
    page_title="ERP VILLAN",
    page_icon="logo.png",
    layout="wide"
)

# Colocamos el logo con protección contra errores
try:
    st.logo("logo.png", size="large")
except Exception:
    # Si la imagen en GitHub sigue vacía o falla, 
    # muestra texto para que la web NO se caiga.
    st.sidebar.markdown("### 📊 ERP VILLAN")
# LISTA DE SOCIOS
SOCIOS = ["cesar", "larry", "jahairo"]

# ==========================
# CONEXIÓN SQLITE (Con protección contra bloqueos)
# ==========================

conn = sqlite3.connect(
    "villan.db",
    check_same_thread=False,
    timeout=20  # Evita el error 'database is locked' dando tiempo de espera
)
cursor = conn.cursor()

# Creación de tablas
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
    utilidad REAL,
    vendedor TEXT
)
""")

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventario(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto TEXT,
    categoria TEXT,
    talla TEXT,
    stock INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    clave TEXT
)
""")
conn.commit()

# PARCHE DE MIGRACIÓN: Agrega la columna vendedor si la base de datos es antigua
try:
    cursor.execute("ALTER TABLE ventas ADD COLUMN vendedor TEXT DEFAULT 'admin'")
    conn.commit()
except sqlite3.OperationalError:
    # Si la columna ya existe, SQLite dará error, pero lo ignoramos de forma segura
    pass

# Crear socios iniciales automáticamente si no existen
for socio in SOCIOS:
    cursor.execute("INSERT OR IGNORE INTO usuarios(usuario, clave) VALUES(?, '1234')", (socio,))
conn.commit()

# ==========================
# COOKIES Y LOGIN INTELIGENTE (Versión Web Estable)
# ==========================

import time  # Asegúrate de tener esta importación arriba si no existe

cookie_manager = stx.CookieManager()

# !!! TRUCO CLAVE PARA LA WEB !!!
# Forzamos al sistema a esperar hasta 3 segundos a que las cookies carguen en el navegador
# Esto evita que el código se ejecute en blanco y te bote con F5
with st.spinner("Verificando sesión..."):
    for _ in range(30):  # Intenta 30 veces (3 segundos en total)
        cookie_usuario = cookie_manager.get(cookie="villan_user")
        if cookie_usuario is not None:
            break
        time.sleep(0.1)

if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

# Si encontramos la cookie y no estaba logueado en la pestaña, lo dejamos pasar
if cookie_usuario and not st.session_state.logueado:
    st.session_state.logueado = True
    st.session_state.usuario_actual = cookie_usuario

# Si no está logueado ni tiene cookies guardadas, pide contraseña
if not st.session_state.logueado:
    st.title("🔐 ERP VILLAN")

    usuario_input = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        u_limpio = usuario_input.strip().lower()
        
        cursor.execute("""
            SELECT usuario FROM usuarios
            WHERE LOWER(usuario) = ? AND clave = ?
        """, (u_limpio, clave))

        resultado = cursor.fetchone()

        if resultado:
            st.session_state.logueado = True
            st.session_state.usuario_actual = resultado[0].lower()
            
            # Guardamos la cookie en el navegador por 30 días
            cookie_manager.set(cookie="villan_user", val=resultado[0].lower(), max_age=2592000)
            st.success("Acceso correcto")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
            
    st.stop()

# ==========================
# CARGAR DATOS EN MEMORIA
# ==========================

if "ventas" not in st.session_state:
    cursor.execute("SELECT fecha, mes, anio, sku, producto, categoria, talla, canal, cliente, precio, costo, utilidad, vendedor FROM ventas")
    datos = cursor.fetchall()
    st.session_state.ventas = [
        {
            "Fecha": x[0], "Mes": x[1], "Año": x[2], "SKU": x[3],
            "Producto": x[4], "Categoría": x[5], "Talla": x[6],
            "Canal": x[7], "Cliente": x[8], "Precio": x[9],
            "Costo": x[10], "Utilidad": x[11], "Vendedor": x[12]
        } for x in datos
    ]

if "gastos" not in st.session_state:
    cursor.execute("SELECT fecha, mes, anio, concepto, categoria, responsable, monto FROM gastos")
    datos = cursor.fetchall()
    st.session_state.gastos = [
        {
            "Fecha": x[0], "Mes": x[1], "Año": x[2], "Concepto": x[3],
            "Categoría": x[4], "Responsable": x[5], "Monto": x[6]
        } for x in datos
    ]

if "inventario" not in st.session_state:
    cursor.execute("SELECT producto, categoria, talla, stock FROM inventario")
    datos = cursor.fetchall()
    st.session_state.inventario = [
        {
            "Producto": x[0], "Categoría": x[1], "Talla": x[2], "Stock": x[3]
        } for x in datos
    ]

# =====================================
# MENÚ DINÁMICO POR ROL
# =====================================

es_socio = st.session_state.usuario_actual in SOCIOS

if es_socio:
    opciones_menu = ["Dashboard", "Ventas", "Inventario", "Gastos", "Gestionar Usuarios"]
else:
    opciones_menu = ["Ventas", "Inventario"]

menu = st.sidebar.selectbox("Menú", opciones_menu)

if st.sidebar.button("Cerrar Sesión"):
    # Borramos el pase del navegador al cerrar sesión a propósito
    cookie_manager.delete(cookie="villan_user")
    
    st.session_state.logueado = False
    st.session_state.usuario_actual = ""
    st.session_state.pop("ventas", None)
    st.session_state.pop("gastos", None)
    st.session_state.pop("inventario", None)
    st.rerun()

# =====================================
# VENTAS
# =====================================

if menu == "Ventas":
    st.title("🛒 Registro de Ventas")
    st.write(f"👤 Atendido por: **{st.session_state.usuario_actual.title()}**")

    fecha = st.date_input("Fecha de Venta", datetime.now())
    producto_input = st.text_input("Nombre del Producto")
    producto = producto_input.strip().title()
    
    categoria = st.selectbox("Categoría", ["Pantalón", "Polo", "Polera", "Casaca", "Short", "Otro"])
    talla = st.selectbox("Talla", ["XS", "S", "M", "L", "XL", "XXL"])
    canal = st.selectbox("Canal de Venta", ["Instagram", "WhatsApp", "TikTok", "Tienda Física", "Otro"])
    cliente = st.text_input("Cliente").strip().title()
    precio = st.number_input("Precio de Venta", min_value=0.0)
    
    if es_socio:
        costo = st.number_input("Costo (Precio Mayorista)", min_value=0.0)
    else:
        costo = 0.0

    if st.button("Guardar Venta"):
        if not producto:
            st.error("❌ Por favor, ingresa el nombre del producto.")
            st.stop()

        producto_encontrado = False
        for item in st.session_state.inventario:
            if item["Producto"] == producto and item["Talla"] == talla:
                producto_encontrado = True
                if item["Stock"] <= 0:
                    st.error(f"❌ No hay stock disponible para {producto} en talla {talla}.")
                    st.stop()

                item["Stock"] -= 1
                cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (item["Stock"], item["Producto"], item["Talla"]))
                conn.commit()
                break

        if not producto_encontrado:
            st.error(f"❌ El producto '{producto}' en talla {talla} no existe en el inventario.")
            st.stop()

        utilidad = precio - costo
        sku_generado = f"{producto} {talla}"
        vendedor_actual = st.session_state.usuario_actual

        cursor.execute("""
            INSERT INTO ventas(fecha, mes, anio, sku, producto, categoria, talla, canal, cliente, precio, costo, utilidad, vendedor)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            fecha.strftime("%d/%m/%Y"), fecha.strftime("%m"), fecha.year, sku_generado,
            producto, categoria, talla, canal, cliente, precio, costo, utilidad, vendedor_actual
        ))
        conn.commit()

        st.session_state.ventas.append({
            "Fecha": fecha.strftime("%d/%m/%Y"), "Mes": fecha.strftime("%m"), "Año": fecha.year,
            "SKU": sku_generado, "Producto": producto, "Categoría": categoria, "Talla": talla,
            "Canal": canal, "Cliente": cliente, "Precio": precio, "Costo": costo, "Utilidad": utilidad,
            "Vendedor": vendedor_actual
        })
        st.success("✅ Venta registrada con éxito")
        st.rerun()  

    st.divider()

    if st.session_state.ventas:
        df_ventas = pd.DataFrame(st.session_state.ventas)
        df_ventas.index = range(1, len(df_ventas) + 1)
        
        st.subheader("📋 Ventas Registradas (Historial General)")
        if not es_socio:
            df_ventas_publicas = df_ventas.drop(columns=["Costo", "Utilidad"])
            st.dataframe(df_ventas_publicas, use_container_width=True)
        else:
            st.dataframe(df_ventas, use_container_width=True)

        st.subheader("🗑 Eliminar o Modificar Venta")
        venta_eliminar = st.selectbox(
            "Selecciona la venta",
            range(len(st.session_state.ventas)),
            format_func=lambda x: f"{st.session_state.ventas[x]['SKU']} | Vendedor: {st.session_state.ventas[x]['Vendedor'].title()} | S/ {st.session_state.ventas[x]['Precio']}"
        )

        venta = st.session_state.ventas[venta_eliminar]
        puede_eliminar = es_socio or (st.session_state.usuario_actual == venta["Vendedor"])

        if puede_eliminar:
            if st.button("Eliminar Venta"):
                for item in st.session_state.inventario:
                    if item["Producto"] == venta["Producto"] and item["Talla"] == venta["Talla"]:
                        item["Stock"] += 1
                        cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (item["Stock"], item["Producto"], item["Talla"]))
                        break

                cursor.execute("DELETE FROM ventas WHERE fecha=? AND sku=? AND precio=? AND cliente=? AND vendedor=?", 
                               (venta['Fecha'], venta['SKU'], venta['Precio'], venta['Cliente'], venta['Vendedor']))
                conn.commit()
                st.session_state.ventas.pop(venta_eliminar)
                st.success("Venta eliminada y stock devuelto al inventario.")
                st.rerun()
        else:
            st.warning(f"🔒 No puedes eliminar esta venta. Solo la puede modificar **{venta['Vendedor'].title()}** o un Socio.")

        if es_socio:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                df_ventas.to_excel(writer, index=False)
            st.download_button("📥 Descargar Ventas Excel", data=excel_buffer.getvalue(), file_name="ventas_villan.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================================
# INVENTARIO
# =====================================

elif menu == "Inventario":
    st.title("📦 Inventario VILLAN")

    if es_socio:
        st.subheader("➕ Agregar / Modificar Stock")
        producto_input = st.text_input("Producto")
        producto = producto_input.strip().title()
        categoria = st.selectbox("Categoría", ["Pantalón", "Polo", "Polera", "Casaca", "Short", "Otro"])
        talla = st.selectbox("Talla", ["XS", "S", "M", "L", "XL", "XXL"])
        stock = st.number_input("Stock", min_value=0, step=1)

        if st.button("Agregar Inventario"):
            if not producto:
                st.error("❌ Por favor, ingresa el nombre del producto.")
                st.stop()

            existe = False
            for item in st.session_state.inventario:
                if item["Producto"] == producto and item["Talla"] == talla:
                    item["Stock"] += stock
                    cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (item["Stock"], item["Producto"], talla))
                    existe = True
                    break

            if not existe:
                st.session_state.inventario.append({"Producto": producto, "Categoría": categoria, "Talla": talla, "Stock": stock})
                cursor.execute("INSERT INTO inventario(producto, categoria, talla, stock) VALUES(?,?,?,?)", (producto, categoria, talla, stock))
            
            conn.commit()
            st.success(f"✅ {producto} (Talla {talla}) actualizado.")
            st.rerun()
        st.divider()

    if st.session_state.inventario:
        df_inv = pd.DataFrame(st.session_state.inventario)
        st.subheader("📦 Inventario Actual Disponible")
        st.dataframe(df_inv, use_container_width=True)

        st.subheader("⚠ Productos con Bajo Stock")
        bajo_stock = df_inv[df_inv["Stock"] <= 3]
        if len(bajo_stock) > 0:
            st.warning("Hay productos con bajo stock")
            st.dataframe(bajo_stock, use_container_width=True)
        else:
            st.success("Stock saludable")

# =====================================
# GASTOS (Solo Socios)
# =====================================

elif menu == "Gastos" and es_socio:
    st.title("💸 Registro de Gastos")

    fecha = st.date_input("Fecha del Gasto", datetime.now())
    concepto = st.text_input("Concepto").strip().title()
    categoria = st.selectbox("Categoría", ["Viaje Gamarra", "Hospedaje", "Comida", "Marketing", "Meta Ads", "TikTok Ads", "Reunión", "Transporte", "Otro"])
    responsable = st.text_input("Responsable").strip().title()
    monto = st.number_input("Monto", min_value=0.0)

    if st.button("Guardar Gasto"):
        cursor.execute("INSERT INTO gastos(fecha, mes, anio, concepto, categoria, responsable, monto) VALUES(?,?,?,?,?,?,?)", (fecha.strftime("%d/%m/%Y"), fecha.strftime("%m"), fecha.year, concepto, categoria, responsable, monto))
        conn.commit()
        st.session_state.gastos.append({"Fecha": fecha.strftime("%d/%m/%Y"), "Mes": fecha.strftime("%m"), "Año": fecha.year, "Concepto": concepto, "Categoría": categoria, "Responsable": responsable, "Monto": monto})
        st.success("Gasto registrado con éxito")
        st.rerun()

    st.divider()

    if st.session_state.gastos:
        df_gastos = pd.DataFrame(st.session_state.gastos)
        st.subheader("📋 Gastos Registrados")
        st.dataframe(df_gastos, use_container_width=True)

        st.subheader("🗑 Eliminar Gasto")
        gasto_eliminar = st.selectbox("Selecciona gasto a eliminar", range(len(st.session_state.gastos)), format_func=lambda x: f"{st.session_state.gastos[x]['Concepto']} | S/ {st.session_state.gastos[x]['Monto']}")

        if st.button("Eliminar Gasto"):
            gasto = st.session_state.gastos[gasto_eliminar]
            cursor.execute("DELETE FROM gastos WHERE fecha=? AND concepto=? AND monto=? AND responsable=?", (gasto['Fecha'], gasto['Concepto'], gasto['Monto'], gasto['Responsable']))
            conn.commit()
            st.session_state.gastos.pop(gasto_eliminar)
            st.success("Gasto eliminado permanentemente")
            st.rerun()

# =====================================
# GESTIONAR USUARIOS (Solo Socios)
# =====================================

elif menu == "Gestionar Usuarios" and es_socio:
    st.title("👥 Control de Usuarios - VILLAN")
    
    st.subheader("➕ Registrar Nuevo Empleado o Socio")
    nuevo_usuario = st.text_input("Nombre de Usuario").strip().lower()
    nueva_clave = st.text_input("Contraseña para el usuario", type="password")
    
    if st.button("Crear Usuario"):
        if not nuevo_usuario or not nueva_clave:
            st.error("❌ Ambos campos son obligatorios.")
        else:
            try:
                cursor.execute("INSERT INTO usuarios(usuario, clave) VALUES(?, ?)", (nuevo_usuario, nueva_clave))
                conn.commit()
                st.success(f"✅ Usuario '{nuevo_usuario}' creado con éxito.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("❌ Ese nombre de usuario ya existe. Elige otro.")

    st.divider()
    
    st.subheader("📋 Usuarios con Acceso")
    cursor.execute("SELECT id, usuario FROM usuarios")
    lista_usuarios = cursor.fetchall()
    df_usuarios = pd.DataFrame(lista_usuarios, columns=["ID", "Usuario"])
    st.dataframe(df_usuarios, use_container_width=True)
    
    st.subheader("🗑 Eliminar Acceso")
    usuarios_eliminables = [u for u in lista_usuarios if u[1] not in SOCIOS]
    
    if usuarios_eliminables:
        usuario_a_borrar = st.selectbox(
            "Selecciona el usuario a eliminar",
            range(len(usuarios_eliminables)),
            format_func=lambda x: usuarios_eliminables[x][1].title()
        )
        
        if st.button("Eliminar Usuario"):
            id_borrar = usuarios_eliminables[usuario_a_borrar][0]
            nom_borrar = usuarios_eliminables[usuario_a_borrar][1]
            
            cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_borrar,))
            conn.commit()
            st.success(f"🗑 El usuario '{nom_borrar}' ha sido eliminado.")
            st.rerun()
    else:
        st.info("No hay usuarios asignados como vendedores para eliminar.")

# =====================================
# DASHBOARD (Solo Socios)
# =====================================

elif menu == "Dashboard" and es_socio:
    st.title("📊 ERP VILLAN")
    st.write(f"👋 ¡Bienvenido Socio, **{st.session_state.usuario_actual.title()}**!")

    total_ventas = sum(x["Precio"] for x in st.session_state.ventas)
    total_costos = sum(x["Costo"] for x in st.session_state.ventas)
    total_gastos = sum(x["Monto"] for x in st.session_state.gastos)
    utilidad = total_ventas - total_costos - total_gastos
    margen = (utilidad / total_ventas * 100) if total_ventas > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Ventas", f"S/ {total_ventas:,.2f}")
    c2.metric("Costos", f"S/ {total_costos:,.2f}")
    c3.metric("Gastos", f"S/ {total_gastos:,.2f}")
    c4.metric("Utilidad", f"S/ {utilidad:,.2f}")
    c5.metric("Margen %", f"{margen:.2f}%")

    st.divider()

    if st.session_state.ventas:
        df_ventas = pd.DataFrame(st.session_state.ventas)
        st.subheader("🏆 Productos Más Vendidos")
        st.bar_chart(df_ventas["SKU"].value_counts())

        st.subheader("📲 Ventas por Canal")
        st.bar_chart(df_ventas["Canal"].value_counts())

    if st.session_state.gastos:
        df_gastos = pd.DataFrame(st.session_state.gastos)
        st.subheader("💸 Gastos por Categoría")
        st.bar_chart(df_gastos["Categoría"].value_counts())

    st.divider()
    st.info("ERP VILLAN v6.0 - Edición Web Protegida con Cookies")