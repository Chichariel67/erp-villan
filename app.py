import streamlit as st
import pandas as pd
import io
import sqlite3
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
# Se ha implementado una paleta en tonos plomo mate oscuro para evitar el negro básico,
# logrando un contraste más elegante y técnico para la marca.
st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">

    <style>
    /* Fondo principal en plomo mate profundo */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #2b2c30 !important; 
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.5px !important;
        color: #f0f0f0 !important;
    }

    /* Barra lateral en un plomo mate un poco más oscuro para dar profundidad */
    [data-testid="stSidebar"] {
        background-color: #1e1f22 !important;
        border-right: 1px solid rgba(222, 255, 154, 0.1) !important;
    }
    
    [data-testid="stSidebarHeader"] img {
        filter: drop-shadow(0px 4px 10px rgba(222, 255, 154, 0.2));
    }

    /* Tarjetas de métricas */
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

    /* Botones de acción general */
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

def inicializar_base_datos():
    """Crea las tablas asegurando que cada conexión se abra y cierre correctamente."""
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        cursor = conn.cursor()
        
        # Tabla Ventas
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
            vendedor TEXT DEFAULT 'admin'
        )
        """)
        
        # Tabla Gastos
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
        
        # Tabla Usuarios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            clave TEXT
        )
        """)
        
        # Migraciones (por si la tabla existe pero le faltan columnas nuevas)
        try:
            cursor.execute("ALTER TABLE ventas ADD COLUMN vendedor TEXT DEFAULT 'admin'")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE inventario ADD COLUMN costo_base REAL DEFAULT 0.0")
        except sqlite3.OperationalError:
            pass

        # Asegurar que los socios existan en el sistema
        for socio in SOCIOS:
            cursor.execute("INSERT OR IGNORE INTO usuarios(usuario, clave) VALUES(?, '1234')", (socio,))
            
        conn.commit()

# Ejecutar inicialización de DB
inicializar_base_datos()

# =====================================================================
# 4. GESTIÓN DE SESIÓN EXPLICITA Y SEGURA
# =====================================================================
cookie_manager = stx.CookieManager(key="villan_manager")

# Inicializamos el estado de manera explícita
if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

# Leemos la cookie actual
cookie_usuario = cookie_manager.get(cookie="villan_user")

# Si hay cookie válida y no estábamos logueados, restauramos la sesión
if cookie_usuario and not st.session_state.logueado:
    st.session_state.logueado = True
    st.session_state.usuario_actual = cookie_usuario.lower()

# =====================================================================
# 5. CARGA DE DATOS EN MEMORIA (AL CARGAR LA APP)
# =====================================================================
def cargar_datos_memoria():
    """Carga los datos de SQLite a st.session_state para uso rápido"""
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        cursor = conn.cursor()
        
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
            cursor.execute("SELECT producto, categoria, talla, stock, costo_base FROM inventario")
            st.session_state.inventario = [
                {"Producto": x[0], "Categoría": x[1], "Talla": x[2], "Stock": x[3], "Costo_Base": x[4]} for x in cursor.fetchall()
            ]

# =====================================================================
# 6. ESTRUCTURA PRINCIPAL DE VISTAS (SEPARACIÓN LOGIN VS APP)
# =====================================================================

if not st.session_state.logueado:
    # -----------------------------------------------------------------
    # VISTA DE LOGIN
    # -----------------------------------------------------------------
    st.title("🔐 ERP VILLAN")
    st.write("Por favor, identifícate para ingresar al sistema.")
    
    usuario_input = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        u_limpio = usuario_input.strip().lower()
        
        with sqlite3.connect(DB_NAME, timeout=20) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT usuario FROM usuarios WHERE LOWER(usuario) = ? AND clave = ?", (u_limpio, clave))
            resultado = cursor.fetchone()

        if resultado:
            st.session_state.logueado = True
            st.session_state.usuario_actual = resultado[0].lower()
            cookie_manager.set(cookie="villan_user", val=resultado[0].lower(), max_age=2592000)
            st.success("Acceso correcto. Preparando entorno...")
            time.sleep(1) # Pequeña pausa para asegurar la escritura de la cookie
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

else:
    # -----------------------------------------------------------------
    # VISTA PRINCIPAL DEL SISTEMA ERP
    # -----------------------------------------------------------------
    cargar_datos_memoria()
    
    es_socio = st.session_state.usuario_actual in SOCIOS
    
    if es_socio:
        opciones_menu = ["Dashboard", "Ventas", "Inventario", "Gastos", "Gestionar Usuarios"]
    else:
        opciones_menu = ["Ventas", "Inventario"]

    menu = st.sidebar.selectbox("Menú de Navegación", opciones_menu)

    # --- LÓGICA DE CIERRE DE SESIÓN A PRUEBA DE FALLOS ---
    if st.sidebar.button("❌ Cerrar Sesión"):
        # 1. Intentamos eliminar la cookie de manera segura
        try:
            cookie_manager.delete(cookie="villan_user")
        except Exception:
            pass # Si falla, no importa, el estado de sesión manda.
            
        # 2. Reseteamos las variables de autenticación
        st.session_state.logueado = False
        st.session_state.usuario_actual = ""
        
        # 3. Limpiamos toda la memoria de datos explícitamente
        claves_a_borrar = ["ventas", "gastos", "inventario"]
        for clave in claves_a_borrar:
            if clave in st.session_state:
                del st.session_state[clave]
                
        # 4. Pausa de 1 segundo clave. Esto le da tiempo al navegador de procesar el javascript
        # que borra la cookie ANTES de recargar la página. Evita el pantallazo negro.
        time.sleep(1.0)
        st.rerun()

    # =====================================
    # MÓDULO: DASHBOARD
    # =====================================
    if menu == "Dashboard" and es_socio:
        st.title("📊 Balance General Financiero")
        st.write(f"👋 ¡Bienvenido Socio, **{st.session_state.usuario_actual.title()}**!")

        total_ventas = sum(float(x["Precio"]) for x in st.session_state.ventas)
        total_costos = sum(float(x["Costo"]) for x in st.session_state.ventas)
        total_gastos = sum(float(x["Monto"]) for x in st.session_state.gastos)
        
        utilidad = total_ventas - total_costos - total_gastos
        if total_ventas > 0:
            margen = (utilidad / total_ventas) * 100
        else:
            margen = 0.0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Ventas Totales", f"S/ {total_ventas:,.2f}")
        c2.metric("Costos Producción", f"S/ {total_costos:,.2f}")
        c3.metric("Gastos Operativos", f"S/ {total_gastos:,.2f}")
        c4.metric("Utilidad Neta", f"S/ {utilidad:,.2f}")
        c5.metric("Margen Beneficio", f"{margen:.2f}%")

        st.divider()
        if st.session_state.ventas:
            df_ventas = pd.DataFrame(st.session_state.ventas)
            st.subheader("🏆 Prendas Más Vendidas por SKU")
            conteo_ventas = df_ventas["SKU"].value_counts()
            st.bar_chart(conteo_ventas)

    # =====================================
    # MÓDULO: VENTAS
    # =====================================
    elif menu == "Ventas":
        st.title("🛒 Registro de Transacciones de Venta")
        st.write(f"👤 Atendido por: **{st.session_state.usuario_actual.title()}**")

        inventario_disponible = [item for item in st.session_state.inventario if item['Stock'] > 0]

        if not inventario_disponible:
            st.info("⚠️ No hay productos con stock disponible en el almacén en este momento.")
        else:
            with st.form("formulario_ventas_villan"):
                st.subheader("Nueva Venta")
                opciones_prendas = [f"{item['Producto']} (Talla {item['Talla']}) - Disponibles: {item['Stock']} und" for item in inventario_disponible]
                prenda_seleccionada = st.selectbox("Selecciona el artículo a vender:", opciones_prendas)
                
                col1, col2 = st.columns(2)
                with col1:
                    fecha = st.date_input("Fecha de Venta", datetime.now())
                    canal = st.selectbox("Canal de Venta", ["Tienda Física", "Instagram", "WhatsApp", "TikTok", "Otro"])
                    cliente = st.text_input("Nombre del Cliente", "Cliente General")
                with col2:
                    precio = st.number_input("Precio final cobrado (S/)", min_value=0.0, value=89.90, step=1.0)
                    
                guardar_venta = st.form_submit_button("🚀 Registrar y Descontar Stock")

            if guardar_venta:
                # Recuperar el objeto exacto seleccionado
                idx_sel = opciones_prendas.index(prenda_seleccionada)
                prenda_objeto = inventario_disponible[idx_sel]

                # Validación doble de seguridad
                if prenda_objeto["Stock"] <= 0:
                    st.error("❌ Error Crítico: Se intentó vender un producto sin stock.")
                else:
                    # 1. Actualizar Stock en DB
                    nuevo_stock = prenda_objeto["Stock"] - 1
                    with sqlite3.connect(DB_NAME, timeout=20) as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (nuevo_stock, prenda_objeto["Producto"], prenda_objeto["Talla"]))
                        
                        # 2. Calcular Utilidad y Costo
                        costo_real = float(prenda_objeto.get("Costo_Base", 0.0))
                        utilidad_calculada = float(precio) - costo_real
                        sku_generado = f"{prenda_objeto['Producto']} {prenda_objeto['Talla']}"
                        vendedor_actual = st.session_state.usuario_actual
                        fecha_str = fecha.strftime("%d/%m/%Y")
                        mes_str = fecha.strftime("%m")
                        anio_int = fecha.year

                        # 3. Registrar Venta en DB
                        cursor.execute("""
                            INSERT INTO ventas(fecha, mes, anio, sku, producto, categoria, talla, canal, cliente, precio, costo, utilidad, vendedor)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (fecha_str, mes_str, anio_int, sku_generado, prenda_objeto['Producto'], prenda_objeto['Categoría'], prenda_objeto['Talla'], canal, cliente, precio, costo_real, utilidad_calculada, vendedor_actual))
                        conn.commit()

                    # 4. Actualizar Memoria Local
                    prenda_objeto["Stock"] = nuevo_stock # Actualiza la lista en memoria
                    st.session_state.ventas.append({
                        "Fecha": fecha_str, "Mes": mes_str, "Año": anio_int, "SKU": sku_generado, 
                        "Producto": prenda_objeto['Producto'], "Categoría": prenda_objeto['Categoría'], 
                        "Talla": prenda_objeto['Talla'], "Canal": canal, "Cliente": cliente, 
                        "Precio": precio, "Costo": costo_real, "Utilidad": utilidad_calculada, "Vendedor": vendedor_actual
                    })
                    
                    st.success("✅ Venta registrada con éxito en el historial.")
                    time.sleep(0.5)
                    st.rerun()

        st.divider()
        if st.session_state.ventas:
            df_ventas = pd.DataFrame(st.session_state.ventas)
            df_ventas.index = range(1, len(df_ventas) + 1)
            st.subheader("📋 Historial Completo de Ventas")
            
            # Filtro de privacidad de costos para no socios
            if es_socio:
                df_mostrar = df_ventas
            else:
                df_mostrar = df_ventas.drop(columns=["Costo", "Utilidad"])
                
            st.dataframe(df_mostrar, use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_mostrar.to_excel(writer, index=False, sheet_name='Reporte_Ventas')
            buffer.seek(0)

            st.download_button(
                label="📥 Descargar Extracto de Ventas (Excel)",
                data=buffer,
                file_name=f"Ventas_Villan_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.subheader("🗑 Anular y Devolver a Almacén")
            st.write("Selecciona una transacción para anularla. El producto retornará automáticamente al stock.")
            
            lista_opciones_anular = []
            for i, v in enumerate(st.session_state.ventas):
                texto_opcion = f"ID:{i} | {v['Fecha']} | {v['SKU']} | Vendedor: {v['Vendedor'].title()} | S/ {v['Precio']}"
                lista_opciones_anular.append((i, texto_opcion))
                
            venta_eliminar_idx = st.selectbox("Transacción a cancelar:", [x[0] for x in lista_opciones_anular], format_func=lambda x: [y[1] for y in lista_opciones_anular if y[0] == x][0])
            
            if venta_eliminar_idx is not None:
                v_sel = st.session_state.ventas[venta_eliminar_idx]

                if es_socio or (st.session_state.usuario_actual == v_sel["Vendedor"]):
                    if st.button("⚠️ Confirmar Anulación de Venta"):
                        with sqlite3.connect(DB_NAME, timeout=20) as conn:
                            cursor = conn.cursor()
                            
                            # 1. Retornar el stock a la DB
                            for item in st.session_state.inventario:
                                if item["Producto"] == v_sel["Producto"] and item["Talla"] == v_sel["Talla"]:
                                    item["Stock"] += 1
                                    cursor.execute("UPDATE inventario SET stock = ? WHERE producto = ? AND talla = ?", (item["Stock"], item["Producto"], item["Talla"]))
                                    break
                                    
                            # 2. Borrar la venta de la DB
                            cursor.execute("DELETE FROM ventas WHERE fecha=? AND sku=? AND precio=? AND cliente=? AND vendedor=?", (v_sel['Fecha'], v_sel['SKU'], v_sel['Precio'], v_sel['Cliente'], v_sel['Vendedor']))
                            conn.commit()
                            
                        # 3. Limpiar memoria
                        st.session_state.ventas.pop(venta_eliminar_idx)
                        st.success("Venta eliminada y stock devuelto exitosamente.")
                        time.sleep(0.8)
                        st.rerun()

    # =====================================
    # MÓDULO: INVENTARIO
    # =====================================
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
                            
                            # Buscar si ya existe la prenda para sumar stock
                            for item in st.session_state.inventario:
                                if item["Producto"] == prod and item["Talla"] == tll:
                                    item["Stock"] += stk
                                    item["Costo_Base"] = c_base
                                    cursor.execute("UPDATE inventario SET stock = ?, costo_base = ? WHERE producto = ? AND talla = ?", (item["Stock"], c_base, prod, tll))
                                    existe_producto = True
                                    break
                                    
                            # Si no existe, crear registro nuevo
                            if not existe_producto:
                                st.session_state.inventario.append({"Producto": prod, "Categoría": cat, "Talla": tll, "Stock": stk, "Costo_Base": c_base})
                                cursor.execute("INSERT INTO inventario(producto, categoria, talla, stock, costo_base) VALUES(?,?,?,?,?)", (prod, cat, tll, stk, c_base))
                                
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
            
            if es_socio:
                df_inv_mostrar = df_inv
            else:
                df_inv_mostrar = df_inv.drop(columns=["Costo_Base"])
                
            st.dataframe(df_inv_mostrar, use_container_width=True)

            st.subheader("⚠ Alertas Automáticas de Reposición (Stock Crítico)")
            bajo_stock = df_inv_mostrar[df_inv_mostrar["Stock"] <= 3]
            if not bajo_stock.empty:
                st.error("Atención: Los siguientes artículos requieren reposición inmediata.")
                st.dataframe(bajo_stock, use_container_width=True)
            else:
                st.success("Toda la mercadería se encuentra por encima del margen crítico. Almacén estable.")

    # =====================================
    # MÓDULO: GASTOS
    # =====================================
    elif menu == "Gastos" and es_socio:
        st.title("💸 Control Central de Gastos y Egresos")
        
        with st.form("form_gastos"):
            f_g = st.date_input("Fecha de Egreso", datetime.now())
            con = st.text_input("Concepto Detallado del Gasto").strip().title()
            cat = st.selectbox("Clasificación Contable", ["Viaje Gamarra", "Hospedaje", "Comida", "Marketing", "Meta Ads", "Transporte", "Suministros", "Otro"])
            resp = st.text_input("Personal Responsable").strip().title()
            mon = st.number_input("Monto Total Facturado (S/)", min_value=0.0, step=1.0)
            
            btn_gasto = st.form_submit_button("Registrar Egreso")

        if btn_gasto:
            if con != "" and resp != "" and mon > 0:
                fecha_str = f_g.strftime("%d/%m/%Y")
                mes_str = f_g.strftime("%m")
                anio_int = f_g.year
                
                with sqlite3.connect(DB_NAME, timeout=20) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO gastos(fecha, mes, anio, concepto, categoria, responsable, monto) VALUES(?,?,?,?,?,?,?)", (fecha_str, mes_str, anio_int, con, cat, resp, mon))
                    conn.commit()
                    
                st.session_state.gastos.append({"Fecha": fecha_str, "Mes": mes_str, "Año": anio_int, "Concepto": con, "Categoría": cat, "Responsable": resp, "Monto": mon})
                st.success("✅ Gasto procesado y guardado en la base de datos.")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("⚠️ Por favor completa la descripción, el responsable y asegúrate de que el monto sea mayor a 0.")

        st.divider()
        if st.session_state.gastos:
            st.subheader("📋 Libro de Egresos")
            df_gastos = pd.DataFrame(st.session_state.gastos)
            df_gastos.index = range(1, len(df_gastos) + 1)
            st.dataframe(df_gastos, use_container_width=True)

    # =====================================
    # MÓDULO: GESTIONAR USUARIOS
    # =====================================
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
            if nuevo_usuario == "" or nueva_clave == "":
                st.error("❌ Los campos de usuario y contraseña son de llenado obligatorio.")
            else:
                try:
                    with sqlite3.connect(DB_NAME, timeout=20) as conn:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios(usuario, clave) VALUES(?, ?)", (nuevo_usuario, nueva_clave))
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
            usuario_a_borrar = st.selectbox(
                "Seleccione la cuenta a dar de baja permanentemente:",
                range(len(usuarios_eliminables)),
                format_func=lambda x: usuarios_eliminables[x][1].title()
            )
            
            if st.button("⚠️ Ejecutar Baja de Usuario"):
                id_borrar = usuarios_eliminables[usuario_a_borrar][0]
                nom_borrar = usuarios_eliminables[usuario_a_borrar][1]
                
                with sqlite3.connect(DB_NAME, timeout=20) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_borrar,))
                    conn.commit()
                    
                st.success(f"🗑 Las credenciales de '{nom_borrar}' han sido revocadas exitosamente.")
                time.sleep(0.5)
                st.rerun()
        else:
            st.info("Actualmente no existen vendedores regulares registrados. Los accesos de los socios no pueden ser eliminados desde este panel.")