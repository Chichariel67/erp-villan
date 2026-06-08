import streamlit as st
import pandas as pd
import io
import sqlite3
import hashlib
from datetime import datetime
import extra_streamlit_components as stx
import time
import warnings

# =====================================================================
# 1. CONFIGURACIÓN INICIAL Y SILENCIADO DE ADVERTENCIAS
# =====================================================================
warnings.filterwarnings("ignore", message=".*CachedWidgetWarning.*")

st.set_page_config(
    page_title="ERP VILLAN",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# 2. DISEÑO VISUAL ULTRA-PREMIUM (ESTILO PLOMO MATE)
# =====================================================================
st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">

    <style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #2b2c30 !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.5px !important;
        color: #f0f0f0 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #1e1f22 !important;
        border-right: 1px solid rgba(222, 255, 154, 0.1) !important;
    }
    [data-testid="stSidebarHeader"] img {
        filter: drop-shadow(0px 4px 10px rgba(222, 255, 154, 0.2));
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #36383d, #2b2c30) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 24px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2) !important;
    }
    div[data-testid="stMetric"]:hover {
        border-color: rgba(222, 255, 154, 0.5) !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        color: #a0a5b0 !important;
    }
    div[data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }
    .stButton>button, .stDownloadButton>button {
        background: #36383d !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background: #deff9a !important;
        color: #1e1f22 !important;
        border-color: #deff9a !important;
    }
    </style>
""", unsafe_allow_html=True)

try:
    st.logo("logo.png", size="large")
except Exception:
    st.sidebar.markdown("### 📊 ERP VILLAN")

# =====================================================================
# 3. VARIABLES GLOBALES Y CONFIGURACIÓN DE BASE DE DATOS
# =====================================================================
SOCIOS = ["cesar", "larry", "jahairo"]
DB_NAME = "villan.db"

MESES = {
    "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
    "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
    "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
}

# =====================================================================
# FIX #4: Contraseñas con hash SHA-256 en lugar de texto plano
# =====================================================================
def hashear_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode()).hexdigest()


def inicializar_base_datos():
    """Crea las tablas asegurando que cada conexión se abra y cierre correctamente."""
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        cursor = conn.cursor()

        # Tabla Ventas — incluye id explícito para DELETE seguro (FIX #1)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            mes TEXT,
            mes_nombre TEXT,
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
            vendedor TEXT DEFAULT 'admin'
        )
        """)

        # Tabla Gastos — incluye id para futura anulación (FIX #8)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            mes TEXT,
            mes_nombre TEXT,
            anio INTEGER,
            concepto TEXT,
            categoria TEXT,
            responsable TEXT,
            monto REAL
        )
        """)

        # Tabla Inventario
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            categoria TEXT,
            talla TEXT,
            stock INTEGER,
            costo_base REAL DEFAULT 0.0
        )
        """)

        # Tabla Usuarios — clave guardada como hash
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            clave TEXT
        )
        """)

        # ── Migraciones defensivas ──────────────────────────────────
        for col_sql in [
            "ALTER TABLE ventas ADD COLUMN vendedor TEXT DEFAULT 'admin'",
            "ALTER TABLE ventas ADD COLUMN mes_nombre TEXT DEFAULT ''",
            "ALTER TABLE gastos ADD COLUMN mes_nombre TEXT DEFAULT ''",
            "ALTER TABLE inventario ADD COLUMN costo_base REAL DEFAULT 0.0",
        ]:
            try:
                cursor.execute(col_sql)
            except sqlite3.OperationalError:
                pass

        # ── Migración de contraseñas en texto plano a hash ──────────
        # Si algún usuario tiene clave sin hash (longitud != 64), la migramos.
        cursor.execute("SELECT id, clave FROM usuarios")
        for uid, clave in cursor.fetchall():
            if len(clave) != 64:  # SHA-256 hex = 64 chars
                cursor.execute("UPDATE usuarios SET clave = ? WHERE id = ?", (hashear_clave(clave), uid))

        # Asegurar socios con clave '1234' hasheada
        clave_default = hashear_clave("1234")
        for socio in SOCIOS:
            cursor.execute(
                "INSERT OR IGNORE INTO usuarios(usuario, clave) VALUES(?, ?)",
                (socio, clave_default)
            )

        conn.commit()


inicializar_base_datos()

# =====================================================================
# 4. GESTIÓN DE SESIÓN
# =====================================================================
cookie_manager = stx.CookieManager(key="villan_manager")

if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

cookie_usuario = cookie_manager.get(cookie="villan_user")

if cookie_usuario and not st.session_state.logueado:
    st.session_state.logueado = True
    st.session_state.usuario_actual = cookie_usuario.lower()

# =====================================================================
# 5. CARGA DE DATOS EN MEMORIA
# FIX #2: Función separada para forzar recarga desde DB cuando se necesite
# =====================================================================
def cargar_ventas_db():
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, fecha, mes, mes_nombre, anio, sku, producto, categoria,
                   talla, canal, cliente, precio, costo, utilidad, vendedor
            FROM ventas
        """)
        st.session_state.ventas = [
            {
                "id": x[0], "Fecha": x[1], "Mes": x[2], "Mes_Nombre": x[3],
                "Año": x[4], "SKU": x[5], "Producto": x[6], "Categoría": x[7],
                "Talla": x[8], "Canal": x[9], "Cliente": x[10],
                "Precio": x[11], "Costo": x[12], "Utilidad": x[13], "Vendedor": x[14]
            }
            for x in cursor.fetchall()
        ]


def cargar_gastos_db():
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, fecha, mes, mes_nombre, anio, concepto, categoria, responsable, monto
            FROM gastos
        """)
        st.session_state.gastos = [
            {
                "id": x[0], "Fecha": x[1], "Mes": x[2], "Mes_Nombre": x[3],
                "Año": x[4], "Concepto": x[5], "Categoría": x[6],
                "Responsable": x[7], "Monto": x[8]
            }
            for x in cursor.fetchall()
        ]


def cargar_inventario_db():
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, producto, categoria, talla, stock, costo_base FROM inventario")
        st.session_state.inventario = [
            {
                "id": x[0], "Producto": x[1], "Categoría": x[2],
                "Talla": x[3], "Stock": x[4], "Costo_Base": x[5]
            }
            for x in cursor.fetchall()
        ]


def cargar_datos_memoria():
    """Carga todos los datos desde DB a session_state (solo si aún no están cargados)."""
    if "ventas" not in st.session_state:
        cargar_ventas_db()
    if "gastos" not in st.session_state:
        cargar_gastos_db()
    if "inventario" not in st.session_state:
        cargar_inventario_db()


# =====================================================================
# 6. ESTRUCTURA PRINCIPAL
# =====================================================================
if not st.session_state.logueado:
    # ── LOGIN ────────────────────────────────────────────────────────
    st.title("🔐 ERP VILLAN")
    st.write("Por favor, identifícate para ingresar al sistema.")

    usuario_input = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        u_limpio = usuario_input.strip().lower()
        clave_hash = hashear_clave(clave)  # FIX #4: comparar contra hash

        with sqlite3.connect(DB_NAME, timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT usuario FROM usuarios WHERE LOWER(usuario) = ? AND clave = ?",
                (u_limpio, clave_hash)
            )
            resultado = cursor.fetchone()

        if resultado:
            st.session_state.logueado = True
            st.session_state.usuario_actual = resultado[0].lower()
            cookie_manager.set(cookie="villan_user", val=resultado[0].lower(), max_age=2592000)
            st.success("Acceso correcto. Preparando entorno...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

else:
    # ── APP PRINCIPAL ────────────────────────────────────────────────
    cargar_datos_memoria()

    es_socio = st.session_state.usuario_actual in SOCIOS

    if es_socio:
        opciones_menu = ["Dashboard", "Ventas", "Inventario", "Gastos", "Gestionar Usuarios"]
    else:
        opciones_menu = ["Ventas", "Inventario"]

    menu = st.sidebar.selectbox("Menú de Navegación", opciones_menu)

    # ── Botón de actualizar datos (FIX #2) ──────────────────────────
    if st.sidebar.button("🔄 Actualizar Datos"):
        cargar_ventas_db()
        cargar_gastos_db()
        cargar_inventario_db()
        st.rerun()

    # ── Cierre de sesión ─────────────────────────────────────────────
    if st.sidebar.button("❌ Cerrar Sesión"):
        try:
            cookie_manager.delete(cookie="villan_user")
        except Exception:
            pass

        st.session_state.logueado = False
        st.session_state.usuario_actual = ""

        for clave_estado in ["ventas", "gastos", "inventario"]:
            if clave_estado in st.session_state:
                del st.session_state[clave_estado]

        time.sleep(1.0)
        st.rerun()

    # ================================================================
    # MÓDULO: DASHBOARD
    # ================================================================
    if menu == "Dashboard" and es_socio:
        st.title("📊 Balance General Financiero")
        st.write(f"👋 ¡Bienvenido Socio, **{st.session_state.usuario_actual.title()}**!")

        # ── Filtros de período ───────────────────────────────────────
        años_disponibles = sorted(set(v["Año"] for v in st.session_state.ventas), reverse=True) if st.session_state.ventas else [datetime.now().year]
        col_f1, col_f2 = st.columns([1, 3])
        with col_f1:
            año_sel = st.selectbox("Filtrar por Año", ["Todos"] + [str(a) for a in años_disponibles])
        with col_f2:
            meses_disp = ["Todos"] + list(MESES.values())
            mes_sel = st.selectbox("Filtrar por Mes", meses_disp)

        # Aplicar filtros
        ventas_filtradas = st.session_state.ventas
        gastos_filtrados = st.session_state.gastos

        if año_sel != "Todos":
            ventas_filtradas = [v for v in ventas_filtradas if str(v["Año"]) == año_sel]
            gastos_filtrados = [g for g in gastos_filtrados if str(g["Año"]) == año_sel]

        if mes_sel != "Todos":
            ventas_filtradas = [v for v in ventas_filtradas if v.get("Mes_Nombre") == mes_sel]
            gastos_filtrados = [g for g in gastos_filtrados if g.get("Mes_Nombre") == mes_sel]

        total_ventas = sum(float(x["Precio"]) for x in ventas_filtradas)
        total_costos = sum(float(x["Costo"]) for x in ventas_filtradas)
        total_gastos = sum(float(x["Monto"]) for x in gastos_filtrados)
        utilidad = total_ventas - total_costos - total_gastos
        margen = (utilidad / total_ventas * 100) if total_ventas > 0 else 0.0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Ventas Totales", f"S/ {total_ventas:,.2f}")
        c2.metric("Costos Producción", f"S/ {total_costos:,.2f}")
        c3.metric("Gastos Operativos", f"S/ {total_gastos:,.2f}")
        c4.metric("Utilidad Neta", f"S/ {utilidad:,.2f}")
        c5.metric("Margen Beneficio", f"{margen:.2f}%")

        st.divider()

        if ventas_filtradas:
            df_ventas = pd.DataFrame(ventas_filtradas)
            st.subheader("🏆 Prendas Más Vendidas por SKU")
            conteo_ventas = df_ventas["SKU"].value_counts()
            st.bar_chart(conteo_ventas)

            st.subheader("📅 Ventas por Mes")
            ventas_mes = df_ventas.groupby("Mes_Nombre")["Precio"].sum().sort_index()
            st.bar_chart(ventas_mes)

    # ================================================================
    # MÓDULO: VENTAS
    # ================================================================
    elif menu == "Ventas":
        st.title("🛒 Registro de Transacciones de Venta")
        st.write(f"👤 Atendido por: **{st.session_state.usuario_actual.title()}**")

        inventario_disponible = [item for item in st.session_state.inventario if item["Stock"] > 0]

        if not inventario_disponible:
            st.info("⚠️ No hay productos con stock disponible en el almacén en este momento.")
        else:
            with st.form("formulario_ventas_villan"):
                st.subheader("Nueva Venta")
                opciones_prendas = [
                    f"{item['Producto']} (Talla {item['Talla']}) - Disponibles: {item['Stock']} und"
                    for item in inventario_disponible
                ]
                prenda_seleccionada = st.selectbox("Selecciona el artículo a vender:", opciones_prendas)

                col1, col2 = st.columns(2)
                with col1:
                    fecha = st.date_input("Fecha de Venta", datetime.now())
                    canal = st.selectbox("Canal de Venta", ["Tienda Física", "Instagram", "WhatsApp", "TikTok", "Otro"])
                    cliente = st.text_input("Nombre del Cliente", "Cliente General")
                with col2:
                    precio = st.number_input("Precio final cobrado (S/)", min_value=1.0, value=89.90, step=1.0)

                guardar_venta = st.form_submit_button("🚀 Registrar y Descontar Stock")

            if guardar_venta:
                idx_sel = opciones_prendas.index(prenda_seleccionada)
                prenda_objeto = inventario_disponible[idx_sel]

                if prenda_objeto["Stock"] <= 0:
                    st.error("❌ Error Crítico: Se intentó vender un producto sin stock.")
                else:
                    nuevo_stock = prenda_objeto["Stock"] - 1
                    costo_real = float(prenda_objeto.get("Costo_Base", 0.0))
                    utilidad_calculada = float(precio) - costo_real

                    # FIX #5: SKU más robusto con timestamp para evitar colisiones
                    ts = datetime.now().strftime("%H%M%S")
                    sku_generado = f"{prenda_objeto['Producto'][:3].upper()}-{prenda_objeto['Talla']}-{ts}"

                    vendedor_actual = st.session_state.usuario_actual
                    fecha_str = fecha.strftime("%d/%m/%Y")
                    mes_str = fecha.strftime("%m")
                    mes_nombre = MESES[mes_str]
                    anio_int = fecha.year

                    with sqlite3.connect(DB_NAME, timeout=20) as conn:
                        cursor = conn.cursor()
                        # Actualizar stock en DB usando id del inventario (más seguro)
                        cursor.execute(
                            "UPDATE inventario SET stock = ? WHERE id = ?",
                            (nuevo_stock, prenda_objeto["id"])
                        )
                        # Registrar venta
                        cursor.execute("""
                            INSERT INTO ventas(fecha, mes, mes_nombre, anio, sku, producto, categoria,
                                               talla, canal, cliente, precio, costo, utilidad, vendedor)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            fecha_str, mes_str, mes_nombre, anio_int, sku_generado,
                            prenda_objeto["Producto"], prenda_objeto["Categoría"],
                            prenda_objeto["Talla"], canal, cliente,
                            precio, costo_real, utilidad_calculada, vendedor_actual
                        ))
                        nuevo_id = cursor.lastrowid
                        conn.commit()

                    # Actualizar memoria local
                    prenda_objeto["Stock"] = nuevo_stock
                    st.session_state.ventas.append({
                        "id": nuevo_id, "Fecha": fecha_str, "Mes": mes_str,
                        "Mes_Nombre": mes_nombre, "Año": anio_int, "SKU": sku_generado,
                        "Producto": prenda_objeto["Producto"], "Categoría": prenda_objeto["Categoría"],
                        "Talla": prenda_objeto["Talla"], "Canal": canal, "Cliente": cliente,
                        "Precio": precio, "Costo": costo_real, "Utilidad": utilidad_calculada,
                        "Vendedor": vendedor_actual
                    })

                    st.success("✅ Venta registrada con éxito en el historial.")
                    time.sleep(0.5)
                    st.rerun()

        st.divider()

        if st.session_state.ventas:
            df_ventas = pd.DataFrame(st.session_state.ventas)

            # Mostrar últimas 100 por defecto (FIX menor: paginación simple)
            st.subheader("📋 Historial Completo de Ventas")
            mostrar_todo = st.toggle("Mostrar todas las ventas", value=False)
            df_display = df_ventas if mostrar_todo else df_ventas.tail(100)
            df_display = df_display.copy()
            df_display.index = range(1, len(df_display) + 1)

            # Columnas ocultas para no socios
            cols_ocultar_no_socio = ["id", "Mes", "Costo", "Utilidad"]
            cols_ocultar_socio = ["id", "Mes"]

            if es_socio:
                df_mostrar = df_display.drop(columns=cols_ocultar_socio, errors="ignore")
            else:
                df_mostrar = df_display.drop(columns=cols_ocultar_no_socio, errors="ignore")

            st.dataframe(df_mostrar, use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_mostrar.to_excel(writer, index=False, sheet_name="Reporte_Ventas")
            buffer.seek(0)

            st.download_button(
                label="📥 Descargar Extracto de Ventas (Excel)",
                data=buffer,
                file_name=f"Ventas_Villan_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # ── Anulación de ventas (FIX #1: DELETE por ID real) ────
            st.subheader("🗑 Anular y Devolver a Almacén")
            st.write("Selecciona una transacción para anularla. El producto retornará automáticamente al stock.")

            # FIX #6: Diccionario O(1) en lugar de búsqueda O(n²)
            mapa_opciones = {
                v["id"]: f"ID:{v['id']} | {v['Fecha']} | {v['SKU']} | Vendedor: {v['Vendedor'].title()} | S/ {v['Precio']}"
                for v in st.session_state.ventas
            }

            if mapa_opciones:
                id_seleccionado = st.selectbox(
                    "Transacción a cancelar:",
                    options=list(mapa_opciones.keys()),
                    format_func=lambda x: mapa_opciones[x]
                )

                v_sel = next((v for v in st.session_state.ventas if v["id"] == id_seleccionado), None)

                if v_sel and (es_socio or st.session_state.usuario_actual == v_sel["Vendedor"]):
                    if st.button("⚠️ Confirmar Anulación de Venta"):
                        with sqlite3.connect(DB_NAME, timeout=20) as conn:
                            cursor = conn.cursor()

                            # Retornar stock por id de inventario (FIX #7: más robusto)
                            for item in st.session_state.inventario:
                                if item["Producto"] == v_sel["Producto"] and item["Talla"] == v_sel["Talla"]:
                                    item["Stock"] += 1
                                    cursor.execute(
                                        "UPDATE inventario SET stock = ? WHERE id = ?",
                                        (item["Stock"], item["id"])
                                    )
                                    break

                            # FIX #1: DELETE por id único — ya no borra duplicados accidentales
                            cursor.execute("DELETE FROM ventas WHERE id = ?", (v_sel["id"],))
                            conn.commit()

                        st.session_state.ventas = [v for v in st.session_state.ventas if v["id"] != id_seleccionado]
                        st.success("Venta eliminada y stock devuelto exitosamente.")
                        time.sleep(0.8)
                        st.rerun()

    # ================================================================
    # MÓDULO: INVENTARIO
    # ================================================================
    elif menu == "Inventario":
        st.title("📦 Almacén Central e Inventario")

        if es_socio:
            with st.expander("➕ Ingreso de Mercadería al Almacén", expanded=False):
                st.write("Completa los datos para registrar un nuevo lote de prendas.")
                p_in = st.text_input("Nombre de la Prenda (Ej. Jogger Técnico Oversize)")
                prod = p_in.strip().title()
                cat = st.selectbox("Categoría Técnica", ["Pantalón", "Polo", "Polera", "Casaca", "Short", "Otro"])
                tll = st.selectbox("Talla", ["XS", "S", "M", "L", "XL", "XXL"])
                stk = st.number_input("Cantidad de Unidades a Ingresar", min_value=1, step=1)
                c_base = st.number_input("Costo de Producción Unitario (S/)", min_value=0.0, value=40.0, step=1.0)

                if st.button("💾 Guardar Ingreso"):
                    if prod != "":
                        existe_producto = False
                        with sqlite3.connect(DB_NAME, timeout=20) as conn:
                            cursor = conn.cursor()
                            for item in st.session_state.inventario:
                                if item["Producto"] == prod and item["Talla"] == tll:
                                    item["Stock"] += stk
                                    item["Costo_Base"] = c_base
                                    cursor.execute(
                                        "UPDATE inventario SET stock = ?, costo_base = ? WHERE id = ?",
                                        (item["Stock"], c_base, item["id"])
                                    )
                                    existe_producto = True
                                    break

                            if not existe_producto:
                                cursor.execute(
                                    "INSERT INTO inventario(producto, categoria, talla, stock, costo_base) VALUES(?,?,?,?,?)",
                                    (prod, cat, tll, stk, c_base)
                                )
                                nuevo_id = cursor.lastrowid
                                st.session_state.inventario.append({
                                    "id": nuevo_id, "Producto": prod, "Categoría": cat,
                                    "Talla": tll, "Stock": stk, "Costo_Base": c_base
                                })
                            conn.commit()

                        st.success("✅ Base de inventario actualizada de forma exitosa.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Debes colocar el nombre de la prenda.")

        if st.session_state.inventario:
            df_inv = pd.DataFrame(st.session_state.inventario)
            df_inv.index = range(1, len(df_inv) + 1)
            st.subheader("📋 Estado Actual del Almacén")

            cols_ocultar_inv = ["id"]
            if not es_socio:
                cols_ocultar_inv.append("Costo_Base")

            df_inv_mostrar = df_inv.drop(columns=cols_ocultar_inv, errors="ignore")
            st.dataframe(df_inv_mostrar, use_container_width=True)

            st.subheader("⚠ Alertas Automáticas de Reposición (Stock Crítico)")
            bajo_stock = df_inv_mostrar[df_inv_mostrar["Stock"] <= 3]
            if not bajo_stock.empty:
                st.error("Atención: Los siguientes artículos requieren reposición inmediata.")
                st.dataframe(bajo_stock, use_container_width=True)
            else:
                st.success("Toda la mercadería se encuentra por encima del margen crítico. Almacén estable.")

    # ================================================================
    # MÓDULO: GASTOS
    # ================================================================
    elif menu == "Gastos" and es_socio:
        st.title("💸 Control Central de Gastos y Egresos")

        with st.form("form_gastos"):
            f_g = st.date_input("Fecha de Egreso", datetime.now())
            con = st.text_input("Concepto Detallado del Gasto").strip().title()
            cat = st.selectbox("Clasificación Contable", [
                "Viaje Gamarra", "Hospedaje", "Comida", "Marketing",
                "Meta Ads", "Transporte", "Suministros", "Otro"
            ])
            resp = st.text_input("Personal Responsable").strip().title()
            mon = st.number_input("Monto Total Facturado (S/)", min_value=0.0, step=1.0)
            btn_gasto = st.form_submit_button("Registrar Egreso")

        if btn_gasto:
            if con and resp and mon > 0:
                fecha_str = f_g.strftime("%d/%m/%Y")
                mes_str = f_g.strftime("%m")
                mes_nombre = MESES[mes_str]
                anio_int = f_g.year

                with sqlite3.connect(DB_NAME, timeout=20) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO gastos(fecha, mes, mes_nombre, anio, concepto, categoria, responsable, monto) VALUES(?,?,?,?,?,?,?,?)",
                        (fecha_str, mes_str, mes_nombre, anio_int, con, cat, resp, mon)
                    )
                    nuevo_id = cursor.lastrowid
                    conn.commit()

                st.session_state.gastos.append({
                    "id": nuevo_id, "Fecha": fecha_str, "Mes": mes_str,
                    "Mes_Nombre": mes_nombre, "Año": anio_int,
                    "Concepto": con, "Categoría": cat, "Responsable": resp, "Monto": mon
                })
                st.success("✅ Gasto procesado y guardado en la base de datos.")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("⚠️ Por favor completa la descripción, el responsable y asegúrate de que el monto sea mayor a 0.")

        st.divider()

        if st.session_state.gastos:
            st.subheader("📋 Libro de Egresos")

            # FIX #8: Anulación de gastos
            df_gastos = pd.DataFrame(st.session_state.gastos)
            df_gastos_mostrar = df_gastos.drop(columns=["id", "Mes"], errors="ignore")
            df_gastos_mostrar.index = range(1, len(df_gastos_mostrar) + 1)
            st.dataframe(df_gastos_mostrar, use_container_width=True)

            st.subheader("🗑 Anular Egreso")
            mapa_gastos = {
                g["id"]: f"ID:{g['id']} | {g['Fecha']} | {g['Concepto']} | S/ {g['Monto']}"
                for g in st.session_state.gastos
            }
            id_gasto_sel = st.selectbox(
                "Selecciona el egreso a anular:",
                options=list(mapa_gastos.keys()),
                format_func=lambda x: mapa_gastos[x]
            )
            if st.button("⚠️ Confirmar Anulación de Egreso"):
                with sqlite3.connect(DB_NAME, timeout=20) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM gastos WHERE id = ?", (id_gasto_sel,))
                    conn.commit()
                st.session_state.gastos = [g for g in st.session_state.gastos if g["id"] != id_gasto_sel]
                st.success("Egreso eliminado correctamente.")
                time.sleep(0.5)
                st.rerun()

    # ================================================================
    # MÓDULO: GESTIONAR USUARIOS
    # ================================================================
    elif menu == "Gestionar Usuarios" and es_socio:
        st.title("👥 Panel Administrativo de Usuarios")

        st.subheader("Usuarios con Acceso Activo")
        with sqlite3.connect(DB_NAME, timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, usuario FROM usuarios")
            lista_usuarios = cursor.fetchall()

        df_usuarios = pd.DataFrame(lista_usuarios, columns=["ID_Sistema", "Nombre_Usuario"])
        df_usuarios.index = range(1, len(df_usuarios) + 1)
        st.dataframe(df_usuarios, use_container_width=True)

        st.divider()
        st.subheader("➕ Dar de Alta a Nuevo Personal")
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            nuevo_usuario = st.text_input("Nuevo Nombre de Usuario").strip().lower()
        with col_u2:
            nueva_clave = st.text_input("Asignar Contraseña Temporal", type="password")

        if st.button("Registrar Credenciales"):
            if not nuevo_usuario or not nueva_clave:
                st.error("❌ Los campos de usuario y contraseña son de llenado obligatorio.")
            else:
                try:
                    with sqlite3.connect(DB_NAME, timeout=20) as conn:
                        cursor = conn.cursor()
                        # FIX #4: guardar hash en lugar de texto plano
                        cursor.execute(
                            "INSERT INTO usuarios(usuario, clave) VALUES(?, ?)",
                            (nuevo_usuario, hashear_clave(nueva_clave))
                        )
                        conn.commit()
                    st.success(f"✅ Nuevo acceso generado para '{nuevo_usuario}'.")
                    time.sleep(0.5)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ El nombre de usuario ingresado ya se encuentra registrado.")

        st.divider()
        st.subheader("🗑 Revocación de Accesos")
        usuarios_eliminables = [u for u in lista_usuarios if u[1] not in SOCIOS]

        if usuarios_eliminables:
            mapa_usuarios = {u[0]: u[1].title() for u in usuarios_eliminables}
            id_usuario_borrar = st.selectbox(
                "Seleccione la cuenta a dar de baja permanentemente:",
                options=list(mapa_usuarios.keys()),
                format_func=lambda x: mapa_usuarios[x]
            )

            if st.button("⚠️ Ejecutar Baja de Usuario"):
                nom_borrar = mapa_usuarios[id_usuario_borrar]
                with sqlite3.connect(DB_NAME, timeout=20) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_usuario_borrar,))
                    conn.commit()
                st.success(f"🗑 Las credenciales de '{nom_borrar}' han sido revocadas exitosamente.")
                time.sleep(0.5)
                st.rerun()
        else:
            st.info("Actualmente no existen vendedores regulares registrados. Los accesos de los socios no pueden ser eliminados desde este panel.")