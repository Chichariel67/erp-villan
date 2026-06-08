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
# CONEXIÓN SQLITE
# ==========================
conn = sqlite3.connect(
    "villan.db",
    check_same_thread=False,
    timeout=20
)
cursor = conn.cursor()

# Creación de tablas básicas
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

# Parche de migración de columna vendedor
try:
    cursor.execute("ALTER TABLE ventas ADD COLUMN vendedor TEXT DEFAULT 'admin'")
    conn.commit()
except sqlite3.OperationalError:
    pass

# Crear socios iniciales si no existen
for socio in SOCIOS:
    cursor.execute("INSERT OR IGNORE INTO usuarios(usuario, clave) VALUES(?, '1234')", (socio,))
conn.commit()

# ===================================================
# 🔒 COOKIES Y LOGIN INTELIGENTE (TU LOGICA ORIGINAL RECUPERADA)
# ===================================================
cookie_manager = stx.CookieManager()

# Forzamos al sistema a esperar de forma segura el token del navegador
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

# Si no está logueado ni tiene cookies válidas, bloquea con contraseña
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
# CARGAR DATA EN MEMORIA
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

# Arreglo definitivo del cierre de sesión con purga limpia de cookies
if st.sidebar.button("❌ Cerrar Sesión"):
    cookie_manager.delete(cookie="villan_user")
    time.sleep(0.3)  # Pausa obligatoria para que el navegador ejecute el borrado
    st.session_state.logueado = False
    st.session_state.usuario_actual = ""
    st.session_state.pop("ventas", None)
    st.session_state.pop("gastos", None)
    st.session_state.pop("inventario", None)
    st.rerun()

# =====================================
# SECCIÓN: VENTAS (CON REFRESH ARREGLADO)
# =====================================
if menu == "Ventas":
    st.title("🛒 Registro de Ventas")
    st.write(f"👤 Atendido por: **{st.session_state.usuario_actual.title()}**")

    if not st.session_state.inventario:
        st.info("No hay productos en almacén. Registra stock primero.")
    else:
        # Metemos el proceso en un FORMULARIO para evitar que la página parpadee al escribir
        with st.form("formulario_venta_limpio"):
            opciones_prendas = [f"{item['Producto']} (Talla {item['Talla']}) - Disponibles: {item['Stock']} und" for item in st.session_state.inventario]
            prenda_seleccionada = st.selectbox("Selecciona el artículo vendido:", opciones_prendas)
            
            idx_sel = opciones_prendas.index(prenda_seleccionada)
            prenda_objeto = st.session_state.inventario[idx_sel]

            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha de Venta", datetime.now())
                canal = st.selectbox("Canal de Venta", ["Tienda Física", "Instagram", "WhatsApp", "TikTok", "Otro"])
                cliente = st.text_input("Nombre del Cliente", "Cliente General")
            with col2:
                precio = st.number_input("Precio de Venta (S/)", min_value=0.0, value=89.90)
                if es_socio:
                    costo = st.number_input("Costo de Fábrica (S/)", min_value=0.0, value=40.0)
                else:
                    costo = 0.0

            # El botón de guardar dentro del formulario procesa de golpe, SIN REFRESH PREVIO
            enviar_venta = st.form_submit_button("🚀 Procesar y Guardar Venta")

        if enviar_venta:
            if prenda_objeto["Stock"] <= 0:
                st.error("❌ Operación abortada: Este producto no cuenta con stock físico en almacén.")
            else:
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
                    "Fecha": fecha.strftime("%d/%m/%Y"), "Mes": fecha.strftime("%m"), "Año": fecha.year, "SKU": sku_generado, "Producto": prenda_objeto['Producto'], "Categoría": prenda_objeto['Categoría'], "Talla": prenda_objeto['Talla'], "Canal": canal, "Cliente": cliente, "Precio": precio, "Costo": costo, "Utilidad": utilidad, "Vendedor": seller_actual if 'seller_actual' in locals() else vendedor_actual
                })
                st.success("✅ Venta añadida al historial.")
                st.rerun()

    st.divider()
    if st.session_state.ventas:
        df_ventas = pd.DataFrame(st.session_state.ventas)
        df_ventas.index = range(1, len(df_ventas) + 1)
        st.subheader("📋 Ventas del Historial")
        st.dataframe(df_ventas if es_socio else df_ventas.drop(columns=["Costo", "Utilidad"]), use_container_width=True)

        st.subheader("🗑 Eliminar una Venta")
        venta_eliminar = st.selectbox("Selecciona la transacción:", range(len(st.session_state.ventas)), format_func=lambda x: f"{st.session_state.ventas[x]['SKU']} | {st.session_state.ventas[x]['Vendedor'].title()} | S/ {st.session_state.ventas[x]['Precio']}")
        v_sel = st.session_state.ventas[venta_eliminar]

        if es_socio or (st.session_state.usuario_actual == v_sel["Vendedor"]):
            if st.button("Confirmar Eliminación"):
                for item in st.session_state.inventario:
                    if item["Producto"] == v_sel["Producto"] and item["Talla"] == v_sel["Talla"]:
                        item["Stock"] += 1
                        cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (item["Stock"], item["Producto"], item["Talla"]))
                        break
                cursor.execute("DELETE FROM ventas WHERE fecha=? AND sku=? AND precio=? AND cliente=? AND vendedor=?", (v_sel['Fecha'], v_sel['SKU'], v_sel['Precio'], v_sel['Cliente'], v_sel['Vendedor']))
                conn.commit()
                st.session_state.ventas.pop(venta_eliminar)
                st.success("Venta removida y stock devuelto.")
                st.rerun()

# =====================================
# SECCIÓN: INVENTARIO
# =====================================
elif menu == "Inventario":
    st.title("📦 Almacén e Inventario VILLAN")

    if es_socio:
        with st.expander("➕ Formulario para agregar stock"):
            p_in = st.text_input("Nombre de la Prenda")
            prod = p_in.strip().title()
            cat = st.selectbox("Categoría", ["Pantalón", "Polo", "Polera", "Casaca", "Short", "Otro"])
            tll = st.selectbox("Talla", ["XS", "S", "M", "L", "XL", "XXL"])
            stk = st.number_input("Unidades entrantes", min_value=1, step=1)

            if st.button("Guardar en Almacén"):
                if prod:
                    ex = False
                    for item in st.session_state.inventario:
                        if item["Producto"] == prod and item["Talla"] == tll:
                            item["Stock"] += stk
                            cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (item["Stock"], prod, tll))
                            ex = True
                            break
                    if not ex:
                        st.session_state.inventario.append({"Producto": prod, "Categoría": cat, "Talla": tll, "Stock": stk})
                        cursor.execute("INSERT INTO inventario(producto, categoria, talla, stock) VALUES(?,?,?,?)", (prod, cat, tll, stk))
                    conn.commit()
                    st.success("Inventario actualizado.")
                    st.rerun()

    if st.session_state.inventario:
        df_inv = pd.DataFrame(st.session_state.inventario)
        st.subheader("📋 Stock Físico Disponible")
        st.dataframe(df_inv, use_container_width=True)

        st.subheader("⚠ Alertas de Stock Crítico (3 o menos)")
        bajo = df_inv[df_inv["Stock"] <= 3]
        if not bajo.empty:
            st.dataframe(bajo, use_container_width=True)
        else:
            st.success("Todo en orden, stock óptimo.")

# =====================================
# SECCIÓN: GASTOS (SOCIOS)
# =====================================
elif menu == "Gastos" and es_socio:
    st.title("💸 Control de Gastos")
    f_g = st.date_input("Fecha", datetime.now())
    con = st.text_input("Concepto").strip().title()
    cat = st.selectbox("Categoría", ["Viaje Gamarra", "Hospedaje", "Comida", "Marketing", "Meta Ads", "Transporte", "Otro"])
    resp = st.text_input("Responsable").strip().title()
    mon = st.number_input("Monto (S/)", min_value=0.0)

    if st.button("Registrar Gasto"):
        cursor.execute("INSERT INTO gastos(fecha, mes, anio, concepto, categoria, responsable, monto) VALUES(?,?,?,?,?,?,?)", (f_g.strftime("%d/%m/%Y"), f_g.strftime("%m"), f_g.year, con, cat, resp, mon))
        conn.commit()
        st.session_state.gastos.append({"Fecha": f_g.strftime("%d/%m/%Y"), "Mes": f_g.strftime("%m"), "Año": f_g.year, "Concepto": con, "Categoría": cat, "Responsable": resp, "Monto": mon})
        st.success("Gasto guardado.")
        st.rerun()

    if st.session_state.gastos:
        st.dataframe(pd.DataFrame(st.session_state.gastos), use_container_width=True)

# ===================================================
# 👥 SECCIÓN: GESTIONAR USUARIOS (REPARADA AL 100%)
# ===================================================
elif menu == "Gestionar Usuarios" and es_socio:
    st.title("👥 Panel de Control de Personal")
    
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
    
    # 🚨 AQUÍ ESTÁ TU TABLA DEVUELTA: Te muestra exactamente quiénes están inscritos
    st.subheader("📋 Usuarios Registrados con Acceso al Sistema")
    cursor.execute("SELECT id, usuario FROM usuarios")
    lista_usuarios = cursor.fetchall()
    df_usuarios = pd.DataFrame(lista_usuarios, columns=["ID_Sistema", "Nombre_Usuario"])
    st.dataframe(df_usuarios, use_container_width=True)
    
    st.subheader("🗑 Dar de Baja / Eliminar Acceso")
    usuarios_eliminables = [u for u in lista_usuarios if u[1] not in SOCIOS]
    
    if usuarios_eliminables:
        usuario_a_borrar = st.selectbox(
            "Selecciona el usuario a eliminar",
            range(len(usuarios_eliminables)),
            format_func=lambda x: usuarios_eliminables[x][1].title()
        )
        
        if st.button("Eliminar Usuario Permanentemente"):
            id_borrar = usuarios_eliminables[usuario_a_borrar][0]
            nom_borrar = usuarios_eliminables[usuario_a_borrar][1]
            
            cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_borrar,))
            conn.commit()
            st.success(f"🗑 El acceso para '{nom_borrar}' ha sido revocado.")
            st.rerun()
    else:
        st.info("No hay usuarios asignados como vendedores adicionales para eliminar.")

# =====================================
# SECCIÓN: DASHBOARD
# =====================================
elif menu == "Dashboard" and es_socio:
    st.title("📊 Balance y Rendimiento General")
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
        st.subheader("🏆 Prendas Líderes en Venta")
        st.bar_chart(df_ventas["SKU"].value_counts())