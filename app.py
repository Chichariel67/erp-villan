import streamlit as st
import pandas as pd
import io
import sqlite3
from datetime import datetime
import extra_streamlit_components as stx  # Sistema de cookies
import time
import warnings

# =====================================
# SILENCIAR ADVERTENCIA AMARILLA SIN ROMPER EL F5
# =====================================
warnings.filterwarnings("ignore", message=".*CachedWidgetWarning.*")

# =====================================
# CONFIGURACIÓN (¡SIEMPRE PRIMERO!)
# =====================================
st.set_page_config(
    page_title="ERP VILLAN",
    page_icon="📊",  # Cambiado temporalmente por si no encuentra "logo.png"
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
DB_NAME = "villan.db"

# =====================================
# FUNCIONES SECORES DE BASE DE DATOS (HILOS SEGUROS)
# =====================================
def ejecutar_query(query, params=(), traer_datos=False, ejecutar_muchos=False):
    """Maneja la apertura y cierre de conexiones de manera segura para evitar corrupciones."""
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        cursor = conn.cursor()
        if ejecutar_muchos:
            cursor.executemany(query, params)
        else:
            cursor.execute(query, params)
        
        if traer_datos:
            return cursor.fetchall()
        conn.commit()

# Inicialización de tablas
ejecutar_query("""
CREATE TABLE IF NOT EXISTS ventas(
    id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, mes TEXT, anio INTEGER,
    sku TEXT, producto TEXT, categoria TEXT, talla TEXT, canal TEXT,
    cliente TEXT, precio REAL, costo REAL, utilidad REAL, vendedor TEXT
)""")

ejecutar_query("""
CREATE TABLE IF NOT EXISTS gastos(
    id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, mes TEXT, anio INTEGER,
    concepto TEXT, categoria TEXT, responsable TEXT, monto REAL
)""")

ejecutar_query("""
CREATE TABLE IF NOT EXISTS inventario(
    id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT, categoria TEXT, talla TEXT, stock INTEGER, costo_base REAL DEFAULT 0.0
)""")

ejecutar_query("""
CREATE TABLE IF NOT EXISTS usuarios(
    id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, clave TEXT
)""")

# Migración e inserción de socios por defecto
try:
    ejecutar_query("ALTER TABLE ventas ADD COLUMN vendedor TEXT DEFAULT 'admin'")
except sqlite3.OperationalError:
    pass

try:
    ejecutar_query("ALTER TABLE inventario ADD COLUMN costo_base REAL DEFAULT 0.0")
except sqlite3.OperationalError:
    pass

for socio in SOCIOS:
    ejecutar_query("INSERT OR IGNORE INTO usuarios(usuario, clave) VALUES(?, '1234')", (socio,))

# ===================================================
# 🔒 GESTIÓN DE SESIÓN (CORREGIDO PARA EVITAR ADVERTENCIAS)
# ===================================================
# Inicializamos el gestor de cookies directamente sin decorar con caché
cookie_manager = stx.CookieManager(key="villan_manager")

if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

# Se lee la cookie conservada en el navegador del usuario
cookie_usuario = cookie_manager.get(cookie="villan_user")

if cookie_usuario and not st.session_state.logueado:
    st.session_state.logueado = True
    st.session_state.usuario_actual = cookie_usuario.lower()

# --- PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    st.title("🔐 ERP VILLAN")
    usuario_input = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        u_limpio = usuario_input.strip().lower()
        resultado = ejecutar_query("SELECT usuario FROM usuarios WHERE LOWER(usuario) = ? AND clave = ?", (u_limpio, clave), traer_datos=True)

        if resultado:
            st.session_state.logueado = True
            st.session_state.usuario_actual = resultado[0][0].lower()
            cookie_manager.set(cookie="villan_user", val=resultado[0][0].lower(), max_age=2592000)
            st.success("Acceso correcto")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
    st.stop()

# =====================================
# CARGA O SINCRONIZACIÓN DE DATOS EN MEMORIA
# =====================================
if "ventas" not in st.session_state:
    datos = ejecutar_query("SELECT fecha, mes, anio, sku, producto, categoria, talla, canal, cliente, precio, costo, utilidad, vendedor FROM ventas", traer_datos=True)
    st.session_state.ventas = [
        {"Fecha": x[0], "Mes": x[1], "Año": x[2], "SKU": x[3], "Producto": x[4], "Categoría": x[5], "Talla": x[6], "Canal": x[7], "Cliente": x[8], "Precio": x[9], "Costo": x[10], "Utilidad": x[11], "Vendedor": x[12]} for x in datos
    ]

if "gastos" not in st.session_state:
    datos = ejecutar_query("SELECT fecha, mes, anio, concepto, categoria, responsable, monto FROM gastos", traer_datos=True)
    st.session_state.gastos = [
        {"Fecha": x[0], "Mes": x[1], "Año": x[2], "Concepto": x[3], "Categoría": x[4], "Responsable": x[5], "Monto": x[6]} for x in datos
    ]

if "inventario" not in st.session_state:
    datos = ejecutar_query("SELECT producto, categoria, talla, stock, costo_base FROM inventario", traer_datos=True)
    st.session_state.inventario = [
        {"Producto": x[0], "Categoría": x[1], "Talla": x[2], "Stock": x[3], "Costo_Base": x[4]} for x in datos
    ]

# =====================================
# MENÚ LATERAL
# =====================================
es_socio = st.session_state.usuario_actual in SOCIOS
opciones_menu = ["Dashboard", "Ventas", "Inventario", "Gastos", "Gestionar Usuarios"] if es_socio else ["Ventas", "Inventario"]

menu = st.sidebar.selectbox("Menú", opciones_menu)

if st.sidebar.button("❌ Cerrar Sesión"):
    cookie_manager.delete(cookie="villan_user")
    st.session_state.logueado = False
    st.session_state.usuario_actual = ""
    for key in ["ventas", "gastos", "inventario"]:
        if key in st.session_state:
            del st.session_state[key]
    time.sleep(0.5)
    st.rerun()

# =====================================
# MÓDULOS DEL SISTEMA
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

elif menu == "Ventas":
    st.title("🛒 Registro de Ventas")
    st.write(f"👤 Atendido por: **{st.session_state.usuario_actual.title()}**")

    if not st.session_state.inventario or sum(item['Stock'] for item in st.session_state.inventario) == 0:
        st.info("No hay productos con stock disponible en el almacén.")
    else:
        with st.form("formulario_ventas_villan"):
            opciones_prendas = [f"{item['Producto']} (Talla {item['Talla']}) - Disponibles: {item['Stock']} und" for item in st.session_state.inventario if item['Stock'] > 0]
            prenda_seleccionada = st.selectbox("Selecciona el artículo vendido desde el Almacén:", opciones_prendas)
            
            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha de Venta", datetime.now())
                canal = st.selectbox("Canal de Venta", ["Tienda Física", "Instagram", "WhatsApp", "TikTok", "Otro"])
                cliente = st.text_input("Nombre del Cliente", "Cliente General")
            with col2:
                precio = st.number_input("Precio de Venta cobrado (S/)", min_value=0.0, value=89.90)
                
            guardar_venta = st.form_submit_button("🚀 Registrar Transacción")

        if guardar_venta:
            idx_sel = opciones_prendas.index(prenda_seleccionada)
            # Encontrar el objeto real filtrando solo los que tienen stock activo
            prenda_objeto = [item for item in st.session_state.inventario if item['Stock'] > 0][idx_sel]

            prenda_objeto["Stock"] -= 1
            ejecutar_query("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (prenda_objeto["Stock"], prenda_objeto["Producto"], prenda_objeto["Talla"]))
            
            # Corrección: El costo se hereda automáticamente del inventario para no alterar las utilidades corporativas reales
            costo_real = prenda_objeto.get("Costo_Base", 0.0)
            utilidad_calculada = precio - costo_real
            sku_generado = f"{prenda_objeto['Producto']} {prenda_objeto['Talla']}"
            vendedor_actual = st.session_state.usuario_actual

            ejecutar_query("""
                INSERT INTO ventas(fecha, mes, anio, sku, producto, categoria, talla, canal, cliente, precio, costo, utilidad, vendedor)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (fecha.strftime("%d/%m/%Y"), fecha.strftime("%m"), fecha.year, sku_generado, prenda_objeto['Producto'], prenda_objeto['Categoría'], prenda_objeto['Talla'], canal, cliente, precio, costo_real, utilidad_calculada, vendedor_actual))

            st.session_state.ventas.append({
                "Fecha": fecha.strftime("%d/%m/%Y"), "Mes": fecha.strftime("%m"), "Año": fecha.year, "SKU": sku_generado, "Producto": prenda_objeto['Producto'], "Categoría": prenda_objeto['Categoría'], "Talla": prenda_objeto['Talla'], "Canal": canal, "Cliente": cliente, "Precio": precio, "Costo": costo_real, "Utilidad": utilidad_calculada, "Vendedor": vendedor_actual
            })
            st.success("✅ Venta añadida al historial de manera exitosa.")
            time.sleep(0.4)
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
                        ejecutar_query("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (item["Stock"], item["Producto"], item["Talla"]))
                        break
                ejecutar_query("DELETE FROM ventas WHERE fecha=? AND sku=? AND precio=? AND cliente=? AND vendedor=?", (v_sel['Fecha'], v_sel['SKU'], v_sel['Precio'], v_sel['Cliente'], v_sel['Vendedor']))
                st.session_state.ventas.pop(venta_eliminar)
                st.success("Venta removida correctamente y stock devuelto.")
                time.sleep(0.4)
                st.rerun()

elif menu == "Inventario":
    st.title("📦 Almacén e Inventario VILLAN")

    if es_socio:
        with st.expander("➕ Registrar Nueva Prenda o Agregar Stock"):
            p_in = st.text_input("Nombre de la Prenda (Ejemplo: Jogger Negro)")
            prod = p_in.strip().title()
            cat = st.selectbox("Categoría", ["Pantalón", "Polo", "Polera", "Casaca", "Short", "Otro"])
            tll = st.selectbox("Talla", ["XS", "S", "M", "L", "XL", "XXL"])
            stk = st.number_input("Unidades que ingresan", min_value=1, step=1)
            c_base = st.number_input("Costo de fábrica unitario (S/)", min_value=0.0, value=40.0)

            if st.button("Guardar Stock en Almacén"):
                if prod:
                    ex = False
                    for item in st.session_state.inventario:
                        if item["Producto"] == prod and item["Talla"] == tll:
                            item["Stock"] += stk
                            item["Costo_Base"] = c_base  # Actualiza el costo base por si cambió
                            ejecutar_query("UPDATE inventario SET stock = ?, costo_base = ? WHERE producto = ? AND talla = ?", (item["Stock"], c_base, prod, tll))
                            ex = True
                            break
                    if not ex:
                        st.session_state.inventario.append({"Producto": prod, "Categoría": cat, "Talla": tll, "Stock": stk, "Costo_Base": c_base})
                        ejecutar_query("INSERT INTO inventario(producto, categoria, talla, stock, costo_base) VALUES(?,?,?,?,?)", (prod, cat, tll, stk, c_base))
                    st.success("Inventario actualizado de forma exitosa.")
                    time.sleep(0.4)
                    st.rerun()

    if st.session_state.inventario:
        df_inv = pd.DataFrame(st.session_state.inventario)
        df_inv.index = range(1, len(df_inv) + 1)
        st.subheader("📋 Stock Físico Disponible")
        
        # Ocultar costo base a los vendedores
        df_inv_mostrar = df_inv if es_socio else df_inv.drop(columns=["Costo_Base"])
        st.dataframe(df_inv_mostrar, use_container_width=True)

        st.subheader("⚠ Alertas de Stock Crítico (3 unidades o menos)")
        bajo = df_inv_mostrar[df_inv_mostrar["Stock"] <= 3]
        if not bajo.empty:
            st.dataframe(bajo, use_container_width=True)
        else:
            st.success("Todo en orden. Almacén con stock óptimo.")

elif menu == "Gastos" and es_socio:
    st.title("💸 Control de Gastos")
    f_g = st.date_input("Fecha", datetime.now())
    con = st.text_input("Concepto de Gasto").strip().title()
    cat = st.selectbox("Categoría de Gasto", ["Viaje Gamarra", "Hospedaje", "Comida", "Marketing", "Meta Ads", "Transporte", "Otro"])
    resp = st.text_input("Responsable del pago").strip().title()
    mon = st.number_input("Monto total pagado (S/)", min_value=0.0)

    if st.button("Registrar Gasto"):
        if con and resp and mon > 0:
            ejecutar_query("INSERT INTO gastos(fecha, mes, anio, concepto, categoria, responsable, monto) VALUES(?,?,?,?,?,?,?)", (f_g.strftime("%d/%m/%Y"), f_g.strftime("%m"), f_g.year, con, cat, resp, mon))
            st.session_state.gastos.append({"Fecha": f_g.strftime("%d/%m/%Y"), "Mes": f_g.strftime("%m"), "Año": f_g.year, "Concepto": con, "Categoría": cat, "Responsable": resp, "Monto": mon})
            st.success("Gasto guardado de forma conforme.")
            time.sleep(0.4)
            st.rerun()
        else:
            st.error("Por favor completa todos los campos con montos válidos.")

    if st.session_state.gastos:
        df_gastos = pd.DataFrame(st.session_state.gastos)
        df_gastos.index = range(1, len(df_gastos) + 1)
        st.dataframe(df_gastos, use_container_width=True)

elif menu == "Gestionar Usuarios" and es_socio:
    st.title("👥 Panel de Control de Personal")
    
    st.subheader("📋 Usuarios Registrados con Acceso al Sistema")
    lista_usuarios = ejecutar_query("SELECT id, usuario FROM usuarios", traer_datos=True)
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
                ejecutar_query("INSERT INTO usuarios(usuario, clave) VALUES(?, ?)", (nuevo_usuario, nueva_clave))
                st.success(f"✅ Usuario '{nuevo_usuario}' creado con éxito.")
                time.sleep(0.4)
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
            
            ejecutar_query("DELETE FROM usuarios WHERE id = ?", (id_borrar,))
            st.success(f"🗑 El acceso para '{nom_borrar}' ha sido revocado.")
            time.sleep(0.4)
            st.rerun()
    else:
        st.info("No hay usuarios asignados como vendedores adicionales para eliminar.")