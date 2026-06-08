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

# =====================================
# DISEÑO VISUAL ULTRA-PREMIUM (VILLAN BLACK-EDITION)
# =====================================
st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">

    <style>
    /* Aplicar tipografía moderna a toda la aplicación */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #0b0c10 !important; /* Fondo oscuro cinematográfico */
    }

    /* Títulos con estilo Cyber/Urbano */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.5px !important;
    }

    /* Animación de carga fluida para toda la app */
    .stApp {
        animation: smoothReveal 1s cubic-bezier(0.1, 0.8, 0.2, 1);
    }
    @keyframes smoothReveal {
        from { opacity: 0; filter: blur(5px); transform: scale(0.99); }
        to { opacity: 1; filter: blur(0); transform: scale(1); }
    }

    /* DISEÑO DE LA BARRA LATERAL (SIDEBAR) FLOTANTE */
    [data-testid="stSidebar"] {
        background-color: #111217 !important;
        border-right: 1px solid rgba(222, 255, 154, 0.05) !important;
    }
    
    /* El logo con efecto respiración de luz de fondo (Glow) */
    [data-testid="stSidebarHeader"] img {
        filter: drop-shadow(0px 4px 10px rgba(222, 255, 154, 0.2));
        animation: villainGlow 4s infinite ease-in-out;
        transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    [data-testid="stSidebarHeader"] img:hover {
        transform: scale(1.08) rotate(-1deg);
    }
    @keyframes villainGlow {
        0%, 100% { filter: drop-shadow(0px 0px 8px rgba(222, 255, 154, 0.15)); }
        50% { filter: drop-shadow(0px 0px 20px rgba(222, 255, 154, 0.5)); }
    }

    /* TARJETAS DE MÉTRICAS INTERACTIVAS (GRID PREMIUM) */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #16171d, #111216) !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-radius: 20px !important;
        padding: 24px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
        backdrop-filter: blur(4px) !important;
        transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    }
    
    /* Efecto cuando pasas el mouse por encima de las tarjetas */
    div[data-testid="stMetric"]:hover {
        transform: translateY(-8px) scale(1.01) !important;
        border-color: rgba(222, 255, 154, 0.5) !important; /* Borde verde limón neón */
        box-shadow: 0 15px 30px rgba(222, 255, 154, 0.08) !important;
    }
    
    /* Estilizar el texto dentro de las métricas */
    div[data-testid="stMetricLabel"] {
        font-size: 14px !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        color: #8a8f98 !important;
    }
    div[data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }

    /* BOTONES ESTILO NEÓN INTERACTIVO */
    .stButton>button {
        background: #16171d !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        background: #deff9a !important; /* Fondo verde limón en hover */
        color: #000000 !important; /* Texto negro para contraste */
        border-color: #deff9a !important;
        box-shadow: 0 0 15px rgba(222, 255, 154, 0.4) !important;
        transform: translateY(-2px) !important;
    }

    /* TARJETAS INTERACTIVAS DE PRODUCTOS (CATÁLOGO DE COMPRA) */
    .product-card {
        background: #16171d;
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }
    .product-card:hover {
        border-color: #deff9a;
        transform: scale(1.02);
    }
    </style>
""", unsafe_allow_html=True)

# Colocamos el logo en la barra lateral con protección contra errores
try:
    st.logo("logo.png", size="large")
except Exception:
    st.sidebar.markdown("### 📊 ERP VILLAN")

# LISTA DE SOCIOS
SOCIOS = ["cesar", "larry", "jahairo"]

# ==========================
# CONEXIÓN SQLITE (Con protección contra bloqueos)
# ==========================
conn = sqlite3.connect(
    "villan.db",
    check_same_thread=False,
    timeout=20
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

# PARCHE DE MIGRACIÓN
try:
    cursor.execute("ALTER TABLE ventas ADD COLUMN vendedor TEXT DEFAULT 'admin'")
    conn.commit()
except sqlite3.OperationalError:
    pass

for socio in SOCIOS:
    cursor.execute("INSERT OR IGNORE INTO usuarios(usuario, clave) VALUES(?, '1234')", (socio,))
conn.commit()

# ==========================
# COOKIES Y LOGIN INTELIGENTE
# ==========================
cookie_manager = stx.CookieManager()

with st.spinner("Verificando sesión..."):
    for _ in range(30):
        cookie_usuario = cookie_manager.get(cookie="villan_user")
        if cookie_usuario is not None:
            break
        time.sleep(0.1)

if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

if cookie_usuario and not st.session_state.logueado:
    st.session_state.logueado = True
    st.session_state.usuario_actual = cookie_usuario

if not st.session_state.logueado:
    st.title("🔐 ERP VILLAN")
    usuario_input = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        u_limpio = usuario_input.strip().lower()
        cursor.execute("SELECT usuario FROM usuarios WHERE LOWER(usuario) = ? AND clave = ?", (u_limpio, clave))
        resultado = cursor.fetchone()

        if resultado:
            st.session_state.logueado = True
            st.session_state.usuario_actual = resultado[0].lower()
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
        {"Fecha": x[0], "Mes": x[1], "Año": x[2], "SKU": x[3], "Producto": x[4], "Categoría": x[5], "Talla": x[6], "Canal": x[7], "Cliente": x[8], "Precio": x[9], "Costo": x[10], "Utilidad": x[11], "Vendedor": x[12]} for x in datos
    ]

if "gastos" not in st.session_state:
    cursor.execute("SELECT fecha, mes, anio, concepto, categoria, responsable, monto FROM gastos")
    datos = cursor.fetchall()
    st.session_state.gastos = [
        {"Fecha": x[0], "Mes": x[1], "Año": x[2], "Concepto": x[3], "Categoría": x[4], "Responsable": x[5], "Monto": x[6]} for x in datos
    ]

if "inventario" not in st.session_state:
    cursor.execute("SELECT producto, categoria, talla, stock FROM inventario")
    datos = cursor.fetchall()
    st.session_state.inventario = [
        {"Producto": x[0], "Categoría": x[1], "Talla": x[2], "Stock": x[3]} for x in datos
    ]

# =====================================
# MENÚ DINÁMICO POR ROL
# =====================================
es_socio = st.session_state.usuario_actual in SOCIOS
opciones_menu = ["Dashboard", "Ventas", "Inventario", "Gastos", "Gestionar Usuarios"] if es_socio else ["Ventas", "Inventario"]

menu = st.sidebar.selectbox("Menú", opciones_menu)

# 🛠️ CORRECCIÓN DEL BOTÓN DE CERRAR SESIÓN (PAUSA DE BORRADO INTEGRADA)
if st.sidebar.button("❌ Cerrar Sesión"):
    cookie_manager.delete(cookie="villan_user")
    time.sleep(0.2)  # Le da tiempo al navegador de borrar la cookie por completo
    st.session_state.logueado = False
    st.session_state.usuario_actual = ""
    st.session_state.pop("ventas", None)
    st.session_state.pop("gastos", None)
    st.session_state.pop("inventario", None)
    st.rerun()

# =====================================
# MODULO: VENTAS (DISEÑO INTERACTIVO)
# =====================================
if menu == "Ventas":
    st.title("🛒 Caja de Ventas Rápida")
    st.write(f"👤 Atendido por: **{st.session_state.usuario_actual.title()}**")

    # Mostrar catálogo de selección rápida interactiva
    st.subheader("👕 Paso 1: Selecciona la Prenda a Vender")
    
    if not st.session_state.inventario:
        st.info("No hay productos registrados en el inventario actual.")
        st.stop()

    # Formateamos los productos en tarjetas para que hagan clic en una
    opciones_prendas = [f"{item['Producto']} (Talla {item['Talla']}) - Stock: {item['Stock']} und" for item in st.session_state.inventario]
    prenda_seleccionada = st.selectbox("Toca aquí y elige el producto vendido:", opciones_prendas)
    
    # Extraer el índice seleccionado
    idx_sel = opciones_prendas.index(prenda_seleccionada)
    prenda_objeto = st.session_state.inventario[idx_sel]

    st.markdown(f"""
        <div class="product-card">
            <h3 style='color:#deff9a; margin:0;'>Item Seleccionado: {prenda_objeto['Producto']}</h3>
            <p style='margin:5px 0 0 0; color:#8a8f98;'>Categoría: {prenda_objeto['Categoría']} | Talla: <b>{prenda_objeto['Talla']}</b> | Disponibles: <b>{prenda_objeto['Stock']} und</b></p>
        </div>
    """, unsafe_allow_html=True)

    st.subheader("📝 Paso 2: Detalles del Cliente y Pago")
    col1, col2, col3 = st.columns(3)
    with col1:
        fecha = st.date_input("Fecha de Venta", datetime.now())
        canal = st.selectbox("Canal de Venta", ["Tienda Física", "Instagram", "WhatsApp", "TikTok", "Otro"])
    with col2:
        cliente = st.text_input("Nombre del Cliente", "Cliente General").strip().title()
        precio = st.number_input("Precio Cobrado (S/)", min_value=0.0, value=89.90)
    with col3:
        if es_socio:
            costo = st.number_input("Costo Real de Fábrica (S/)", min_value=0.0, value=40.0)
        else:
            costo = 0.0

    if st.button("🚀 Registrar y Procesar Venta"):
        if prenda_objeto["Stock"] <= 0:
            st.error(f"❌ ¡Operación Cancelada! No queda stock de este producto.")
            st.stop()

        # Descontar stock
        prenda_objeto["Stock"] -= 1
        cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (prenda_objeto["Stock"], prenda_objeto["Producto"], prenda_objeto["Talla"]))
        
        utilidad = precio - costo
        sku_generado = f"{prenda_objeto['Producto']} {prenda_objeto['Talla']}"
        vendedor_actual = st.session_state.usuario_actual

        cursor.execute("""
            INSERT INTO ventas(fecha, mes, anio, sku, producto, categoria, talla, canal, cliente, precio, costo, utilidad, vendedor)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (fecha.strftime("%d/%m/%Y"), fecha.strftime("%m"), fecha.year, sku_generado, prenda_objeto['Producto'], prenda_objeto['Categoría'], prenda_objeto['Talla'], canal, cliente, precio, costo, utilidad, vendedor_actual))
        conn.commit()

        st.session_state.ventas.append({
            "Fecha": fecha.strftime("%d/%m/%Y"), "Mes": fecha.strftime("%m"), "Año": fecha.year, "SKU": sku_generado, "Producto": prenda_objeto['Producto'], "Categoría": prenda_objeto['Categoría'], "Talla": prenda_objeto['Talla'], "Canal": canal, "Cliente": cliente, "Precio": precio, "Costo": costo, "Utilidad": utilidad, "Vendedor": vendedor_actual
        })
        st.success("✅ ¡Venta Guardada con éxito!")
        st.rerun()

    st.divider()
    if st.session_state.ventas:
        df_ventas = pd.DataFrame(st.session_state.ventas)
        st.subheader("📋 Historial de Turno")
        st.dataframe(df_ventas if es_socio else df_ventas.drop(columns=["Costo", "Utilidad"]), use_container_width=True)

# =====================================
# MODULO: INVENTARIO (CON SEMÁFORO VISUAL)
# =====================================
elif menu == "Inventario":
    st.title("📦 Panel de Control de Inventario")

    if es_socio:
        with st.expander("➕ Abrir Formulario para Registrar Nueva Mercadería o Tallas"):
            producto_input = st.text_input("Nombre de la Prenda (Ej: Casaca Bomber)")
            producto = producto_input.strip().title()
            categoria = st.selectbox("Categoría de Ropa", ["Pantalón", "Polo", "Polera", "Casaca", "Short", "Otro"])
            talla = st.selectbox("Talla de Fabricación", ["XS", "S", "M", "L", "XL", "XXL"])
            stock = st.number_input("Cantidad de Unidades que Entran", min_value=1, step=1, value=12)

            if st.button("📥 Almacenar en Base de Datos"):
                if not producto:
                    st.error("Ingresa un nombre de producto válido")
                    st.stop()
                
                existe = False
                for item in st.session_state.inventario:
                    if item["Producto"] == producto and item["Talla"] == talla:
                        item["Stock"] += stock
                        cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (item["Stock"], producto, talla))
                        existe = True
                        break

                if not existe:
                    st.session_state.inventario.append({"Producto": producto, "Categoría": categoria, "Talla": talla, "Stock": stock})
                    cursor.execute("INSERT INTO inventario(producto, categoria, talla, stock) VALUES(?,?,?,?)", (producto, categoria, talla, stock))
                
                conn.commit()
                st.success("✅ Inventario Actualizado")
                st.rerun()

    # MÓDULO SEMÁFORO: Interfaz Funcional de Alertas
    st.subheader("🚨 Alertas de Reposición Urgente")
    df_inv = pd.DataFrame(st.session_state.inventario)
    
    if not df_inv.empty:
        criticos = df_inv[df_inv["Stock"] <= 3]
        if not criticos.empty:
            for _, item in criticos.iterrows():
                st.error(f"🔴 **CRÍTICO:** Quedan solo **{item['Stock']}** unidades de **{item['Producto']}** (Talla {item['Talla']}). ¡Toca ir a Gamarra!")
        else:
            st.success("🟢 Todo correcto. Todos tus artículos tienen stock saludable.")
        
        st.subheader("📋 Lista Completa de Almacén")
        st.dataframe(df_inv, use_container_width=True)

# =====================================
# GASTOS
# =====================================
elif menu == "Gastos" and es_socio:
    st.title("💸 Registro de Gastos")
    fecha = st.date_input("Fecha del Gasto", datetime.now())
    concepto = st.text_input("Concepto").strip().title()
    categoria = st.selectbox("Categoría", ["Viaje Gamarra", "Hospedaje", "Comida", "Marketing", "Meta Ads", "Transporte", "Otro"])
    responsable = st.text_input("Responsable").strip().title()
    monto = st.number_input("Monto", min_value=0.0)

    if st.button("Guardar Gasto"):
        cursor.execute("INSERT INTO gastos(fecha, mes, anio, concepto, categoria, responsable, monto) VALUES(?,?,?,?,?,?,?)", (fecha.strftime("%d/%m/%Y"), fecha.strftime("%m"), fecha.year, concepto, categoria, responsable, monto))
        conn.commit()
        st.session_state.gastos.append({"Fecha": fecha.strftime("%d/%m/%Y"), "Mes": fecha.strftime("%m"), "Año": fecha.year, "Concepto": concepto, "Categoría": categoria, "Responsable": responsable, "Monto": monto})
        st.success("Gasto registrado")
        st.rerun()

    if st.session_state.gastos:
        st.dataframe(pd.DataFrame(st.session_state.gastos), use_container_width=True)

# =====================================
# GESTIONAR USUARIOS
# =====================================
elif menu == "Gestionar Usuarios" and es_socio:
    st.title("👥 Control de Usuarios")
    nuevo_usuario = st.text_input("Nombre de Usuario").strip().lower()
    nueva_clave = st.text_input("Contraseña", type="password")
    
    if st.button("Crear Usuario"):
        if nuevo_usuario and nueva_clave:
            try:
                cursor.execute("INSERT INTO usuarios(usuario, clave) VALUES(?, ?)", (nuevo_usuario, nueva_clave))
                conn.commit()
                st.success("Usuario creado")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("El usuario ya existe")

# =====================================
# DASHBOARD
# =====================================
elif menu == "Dashboard" and es_socio:
    st.title("📊 Panel General Financiero")
    st.write(f"👋 ¡Bienvenido Socio, **{st.session_state.usuario_actual.title()}**!")

    total_ventas = sum(x["Precio"] for x in st.session_state.ventas)
    total_costos = sum(x["Costo"] for x in st.session_state.ventas)
    total_gastos = sum(x["Monto"] for x in st.session_state.gastos)
    utilidad = total_ventas - total_costos - total_gastos
    margen = (utilidad / total_ventas * 100) if total_ventas > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Ventas Total", f"S/ {total_ventas:,.2f}")
    c2.metric("Costos Mat.", f"S/ {total_costos:,.2f}")
    c3.metric("Gastos Op.", f"S/ {total_gastos:,.2f}")
    c4.metric("Utilidad Neta", f"S/ {utilidad:,.2f}")
    c5.metric("Margen %", f"{margen:.2f}%")

    st.divider()
    if st.session_state.ventas:
        df_ventas = pd.DataFrame(st.session_state.ventas)
        st.subheader("🏆 Productos Más Vendidos")
        st.bar_chart(df_ventas["SKU"].value_counts())