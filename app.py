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
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #0b0c10 !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.5px !important;
    }
    [data-testid="stSidebar"] {
        background-color: #111217 !important;
        border-right: 1px solid rgba(222, 255, 154, 0.05) !important;
    }
    [data-testid="stSidebarHeader"] img {
        filter: drop-shadow(0px 4px 10px rgba(222, 255, 154, 0.2));
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #16171d, #111216) !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-radius: 20px !important;
        padding: 24px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
    }
    div[data-testid="stMetric"]:hover {
        border-color: rgba(222, 255, 154, 0.5) !important;
    }
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
    .stButton>button, .stDownloadButton>button {
        background: #16171d !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        width: 100%;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background: #deff9a !important;
        color: #000000 !important;
        border-color: #deff9a !important;
    }
    </style>
""", unsafe_allow_html=True)

try:
    st.logo("logo.png", size="large")
except Exception:
    st.sidebar.markdown("### 📊 ERP VILLAN")

SOCIOS = ["cesar", "larry", "jahairo"]

# ==========================
# CONEXIÓN SQLITE
# ==========================
conn = sqlite3.connect("villan.db", check_same_thread=False, timeout=20)
cursor = conn.cursor()

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

try:
    cursor.execute("ALTER TABLE ventas ADD COLUMN vendedor TEXT DEFAULT 'admin'")
    conn.commit()
except sqlite3.OperationalError:
    pass

for socio in SOCIOS:
    cursor.execute("INSERT OR IGNORE INTO usuarios(usuario, clave) VALUES(?, '1234')", (socio,))
conn.commit()

# ===================================================
# 🔒 GESTIÓN DE SESIÓN ASÍNCRONA (PROPUESTA CÉSAR)
# ===================================================
cookie_manager = stx.CookieManager()

if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

# Leer cookie del navegador de forma pasiva
cookie_usuario = cookie_manager.get(cookie="villan_user")

# Si la cookie está disponible y no se ha reflejado en sesión, la recuperamos
if cookie_usuario and not st.session_state.logueado:
    st.session_state.logueado = True
    st.session_state.usuario_actual = cookie_usuario.lower()

# Renderizado de la Pantalla de Login (Protección contra falsos negativos de F5)
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

# =====================================
# CARGA DE DATOS EN MEMORIA REAL-TIME
# =====================================
if "ventas" not in st.session_state:
    cursor.execute("SELECT fecha, mes, anio, sku, producto, categoria, talla, canal, cliente, precio, costo, utilidad, vendedor FROM ventas")
    st.session_state.ventas = [
        {"Fecha": x[0], "Mes": x[1], "Año": x[2], "SKU": x[3], "Producto": x[4], "Categoría": x[5], "Talla": x[6], "Canal": x[7], "Cliente": x[8], "Precio": x[9], "Costo": x[10], "Utilidad": x[11], "Vendedor": x[12]} for x in cursor.fetchall()
    ]

if "gastos" not in st.session_state:
    cursor.execute("SELECT fecha, mes, anio, concepto, categoria, responsable, monto FROM gastos")
    st.session_state.gastos = [
        {"Fecha": x[0], "Mes": x[1], "Año": x[2], "Concepto": x[3], "Categoría": x[4], "Responsable": x[5], "Monto": x[6]} for x in cursor.fetchall()
    ]

if "inventario" not in st.session_state:
    cursor.execute("SELECT producto, categoria, talla, stock FROM inventario")
    st.session_state.inventario = [
        {"Producto": x[0], "Categoría": x[1], "Talla": x[2], "Stock": x[3]} for x in cursor.fetchall()
    ]

# =====================================
# MENÚ NATIVO SEGÚN ROL DE USUARIO
# =====================================
es_socio = st.session_state.usuario_actual in SOCIOS
opciones_menu = ["Dashboard", "Ventas", "Inventario", "Gastos", "Gestionar Usuarios"] if es_socio else ["Ventas", "Inventario"]

menu = st.sidebar.selectbox("Menú", opciones_menu)

# Cierre de sesión quirúrgico y limpio sin romper estados internos
if st.sidebar.button("❌ Cerrar Sesión"):
    cookie_manager.delete(cookie="villan_user")
    time.sleep(0.2)
    st.session_state.pop("logueado", None)
    st.session_state.pop("usuario_actual", None)
    st.rerun()

# =====================================
# SECCIÓN: DASHBOARD
# =====================================
if menu == "Dashboard" and es_socio:
    st.title("📊 Balance General Financiero")
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
        st.subheader("🏆 Prendas Más Vendidas")
        st.bar_chart(df_ventas["SKU"].value_counts())

# =====================================
# SECCIÓN: VENTAS
# =====================================
elif menu == "Ventas":
    st.title("🛒 Registro de Ventas")
    st.write(f"👤 Atendido por: **{st.session_state.usuario_actual.title()}**")

    if not st.session_state.inventario:
        st.info("No hay productos disponibles en el almacén. Por favor, registra stock en la pestaña de Inventario.")
    else:
        with st.form("formulario_ventas_villan"):
            opciones_prendas = [f"{item['Producto']} (Talla {item['Talla']}) - Disponibles: {item['Stock']} und" for item in st.session_state.inventario]
            prenda_seleccionada = st.selectbox("Selecciona el artículo vendido desde el Almacén:", opciones_prendas)
            
            idx_sel = opciones_prendas.index(prenda_seleccionada)
            prenda_objeto = st.session_state.inventario[idx_sel]

            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha de Venta", datetime.now())
                canal = st.selectbox("Canal de Venta", ["Tienda Física", "Instagram", "WhatsApp", "TikTok", "Otro"])
                cliente = st.text_input("Nombre del Cliente", "Cliente General")
            with col2:
                precio = st.number_input("Precio de Venta cobrado (S/)", min_value=0.0, value=89.90)
                if es_socio:
                    costo = st.number_input("Costo de Fábrica base (S/)", min_value=0.0, value=40.0)
                else:
                    costo = 0.0

            guardar_venta = st.form_submit_button("🚀 Registrar Transacción")

        if guardar_venta:
            if prenda_objeto["Stock"] <= 0:
                st.error("❌ Error: No se puede vender este artículo porque no queda stock disponible en almacén.")
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
                    "Fecha": fecha.strftime("%d/%m/%Y"), "Mes": fecha.strftime("%m"), "Año": fecha.year, "SKU": sku_generado, "Producto": prenda_objeto['Producto'], "Categoría": prenda_objeto['Categoría'], "Talla": prenda_objeto['Talla'], "Canal": canal, "Cliente": cliente, "Precio": precio, "Costo": costo, "Utilidad": utilidad, "Vendedor": vendedor_actual
                })
                st.success("✅ Venta añadida al historial de manera exitosa.")
                st.rerun()

    st.divider()
    if st.session_state.ventas:
        df_ventas = pd.DataFrame(st.session_state.ventas)
        df_ventas.index = range(1, len(df_ventas) + 1)
        st.subheader("📋 Historial Reciente de Ventas")
        
        df_mostrar = df_ventas if es_socio else df_ventas.drop(columns=["Costo", "Utilidad"])
        st.dataframe(df_mostrar, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_mostrar.to_excel(writer, index=False, sheet_name='Reporte_Ventas')
        buffer.seek(0)

        st.download_button(
            label="📥 Descargar Extracto de Ventas en Excel",
            data=buffer,
            file_name=f"Ventas_Villan_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.subheader("🗑 Eliminar una Transacción")
        venta_eliminar = st.selectbox("Selecciona la transacción a cancelar:", range(len(st.session_state.ventas)), format_func=lambda x: f"{st.session_state.ventas[x]['SKU']} | {st.session_state.ventas[x]['Vendedor'].title()} | S/ {st.session_state.ventas[x]['Precio']}")
        v_sel = st.session_state.ventas[venta_eliminar]

        if es_socio or (st.session_state.usuario_actual == v_sel["Vendedor"]):
            if st.button("Confirmar y Devolver a Stock"):
                for item in st.session_state.inventario:
                    if item["Producto"] == v_sel["Producto"] and item["Talla"] == v_sel["Talla"]:
                        item["Stock"] += 1
                        cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (item["Stock"], item["Producto"], item["Talla"]))
                        break
                cursor.execute("DELETE FROM ventas WHERE fecha=? AND sku=? AND precio=? AND cliente=? AND vendedor=?", (v_sel['Fecha'], v_sel['SKU'], v_sel['Precio'], v_sel['Cliente'], v_sel['Vendedor']))
                conn.commit()
                st.session_state.ventas.pop(venta_eliminar)
                st.success("Venta removida correctamente y stock devuelto.")
                st.rerun()

# =====================================
# SECCIÓN: INVENTARIO
# =====================================
elif menu == "Inventario":
    st.title("📦 Almacén e Inventario VILLAN")

    if es_socio:
        with st.expander("➕ Registrar Nueva Prenda o Agregar Stock"):
            p_in = st.text_input("Nombre de la Prenda (Ejemplo: Jogger Negro)")
            prod = p_in.strip().title()
            cat = st.selectbox("Categoría", ["Pantalón", "Polo", "Polera", "Casaca", "Short", "Otro"])
            tll = st.selectbox("Talla", ["XS", "S", "M", "L", "XL", "XXL"])
            stk = st.number_input("Unidades que ingresan", min_value=1, step=1)

            if st.button("Guardar Stock en Almacén"):
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
                    st.success("Inventario actualizado de forma exitosa.")
                    st.rerun()

    if st.session_state.inventario:
        df_inv = pd.DataFrame(st.session_state.inventario)
        df_inv.index = range(1, len(df_inv) + 1)
        st.subheader("📋 Stock Físico Disponible")
        st.dataframe(df_inv, use_container_width=True)

        st.subheader("⚠ Alertas de Stock Crítico (3 unidades o menos)")
        bajo = df_inv[df_inv["Stock"] <= 3]
        if not bajo.empty:
            st.dataframe(bajo, use_container_width=True)
        else:
            st.success("Todo en orden. Almacén con stock óptimo.")

# =====================================
# SECCIÓN: GASTOS
# =====================================
elif menu == "Gastos" and es_socio:
    st.title("💸 Control de Gastos")
    f_g = st.date_input("Fecha", datetime.now())
    con = st.text_input("Concepto de Gasto").strip().title()
    cat = st.selectbox("Categoría de Gasto", ["Viaje Gamarra", "Hospedaje", "Comida", "Marketing", "Meta Ads", "Transporte", "Otro"])
    resp = st.text_input("Responsable del pago").strip().title()
    mon = st.number_input("Monto total pagado (S/)", min_value=0.0)

    if st.button("Registrar Gasto"):
        cursor.execute("INSERT INTO gastos(fecha, mes, anio, concepto, categoria, responsable, monto) VALUES(?,?,?,?,?,?,?)", (f_g.strftime("%d/%m/%Y"), f_g.strftime("%m"), f_g.year, con, cat, resp, mon))
        conn.commit()
        st.session_state.gastos.append({"Fecha": f_g.strftime("%d/%m/%Y"), "Mes": f_g.strftime("%m"), "Año": f_g.year, "Concepto": con, "Categoría": cat, "Responsable": resp, "Monto": mon})
        st.success("Gasto guardado de forma conforme.")
        st.rerun()

    if st.session_state.gastos:
        df_gastos = pd.DataFrame(st.session_state.gastos)
        df_gastos.index = range(1, len(df_gastos) + 1)
        st.dataframe(df_gastos, use_container_width=True)

# =====================================
# 👥 SECCIÓN: GESTIONAR USUARIOS
# =====================================
elif menu == "Gestionar Usuarios" and es_socio:
    st.title("👥 Panel de Control de Personal")
    
    st.subheader("📋 Usuarios Registrados con Acceso al Sistema")
    cursor.execute("SELECT id, usuario FROM usuarios")
    lista_usuarios = cursor.fetchall()
    df_usuarios = pd.DataFrame(lista_usuarios, columns=["ID_Sistema", "Nombre_Usuario"])
    df_usuarios.index = range(1, len(df_usuarios) + 1)
    st.dataframe(df_usuarios, use_container_width=True)
    
    st.divider()

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