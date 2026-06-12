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
# 1. CONFIGURACIÓN INICIAL
# =====================================================================
warnings.filterwarnings("ignore", message=".*CachedWidgetWarning.*")

st.set_page_config(
    page_title="ERP VILLAN",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #36383d, #2b2c30) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 24px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2) !important;
    }
    div[data-testid="stMetric"]:hover { border-color: rgba(222, 255, 154, 0.5) !important; }
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
    /* Tablas de datos editables en Finanzas */
    .fin-tabla { border-radius: 12px; overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

try:
    st.logo("logo.png", size="large")
except Exception:
    st.sidebar.markdown("### 📊 ERP VILLAN")

# =====================================================================
# 2. CONSTANTES
# =====================================================================
SOCIOS   = ["cesar", "larry", "jahairo"]
DB_NAME  = "villan.db"
MESES_ORD = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
              "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
MESES = {
    "01":"Enero","02":"Febrero","03":"Marzo","04":"Abril",
    "05":"Mayo","06":"Junio","07":"Julio","08":"Agosto",
    "09":"Septiembre","10":"Octubre","11":"Noviembre","12":"Diciembre"
}
PRENDAS = ["Pantalón", "Polo", "Polera"]
TALLAS  = ["XS", "S", "M", "L", "XL", "XXL"]
COMPONENTES_COSTO = ["Mat. Prima", "Confección", "Etiquetas", "Empaque", "Transporte", "Otros"]
CATS_FLUJO = {
    "ingresos": ["Ventas Pantalones","Ventas Polos","Ventas Poleras","Otros Ingresos"],
    "costos":   ["Costo Pantalones","Costo Polos","Costo Poleras","Otros Costos Prod."],
    "gastos_op":["Gamarra / Compras","Transporte","Marketing / Meta Ads",
                 "Hospedaje / Viáticos","Suministros","Otros Gastos"],
}

# =====================================================================
# 3. HASH DE CONTRASEÑAS
# =====================================================================
def hashear_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode()).hexdigest()

# =====================================================================
# 4. BASE DE DATOS — INICIALIZACIÓN Y TABLAS NUEVAS
# =====================================================================
def inicializar_base_datos():
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        c = conn.cursor()

        # ── Tablas existentes ────────────────────────────────────────
        c.execute("""CREATE TABLE IF NOT EXISTS ventas(
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, mes TEXT,
            mes_nombre TEXT, anio INTEGER, sku TEXT, producto TEXT,
            categoria TEXT, talla TEXT, canal TEXT, cliente TEXT,
            precio REAL, costo REAL, utilidad REAL, vendedor TEXT DEFAULT 'admin')""")

        c.execute("""CREATE TABLE IF NOT EXISTS gastos(
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, mes TEXT,
            mes_nombre TEXT, anio INTEGER, concepto TEXT, categoria TEXT,
            responsable TEXT, monto REAL)""")

        c.execute("""CREATE TABLE IF NOT EXISTS inventario(
            id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT,
            categoria TEXT, talla TEXT, stock INTEGER, costo_base REAL DEFAULT 0.0)""")

        c.execute("""CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, clave TEXT)""")

        # ── NUEVA: Flujo de Caja mensual editable ───────────────────
        # Cada fila = concepto × mes × año con monto ingresado por socio
        c.execute("""CREATE TABLE IF NOT EXISTS flujo_caja(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anio INTEGER,
            mes_nombre TEXT,
            seccion TEXT,
            concepto TEXT,
            monto REAL DEFAULT 0.0,
            UNIQUE(anio, mes_nombre, concepto))""")

        # ── NUEVA: Costo de producción por prenda/talla ──────────────
        # Cada fila = prenda × talla × componente con costo unitario
        c.execute("""CREATE TABLE IF NOT EXISTS costo_produccion(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prenda TEXT,
            talla TEXT,
            componente TEXT,
            costo REAL DEFAULT 0.0,
            precio_venta REAL DEFAULT 0.0,
            UNIQUE(prenda, talla, componente))""")

        # ── Migraciones defensivas ───────────────────────────────────
        for sql in [
            "ALTER TABLE ventas ADD COLUMN vendedor TEXT DEFAULT 'admin'",
            "ALTER TABLE ventas ADD COLUMN mes_nombre TEXT DEFAULT ''",
            "ALTER TABLE gastos ADD COLUMN mes_nombre TEXT DEFAULT ''",
            "ALTER TABLE inventario ADD COLUMN costo_base REAL DEFAULT 0.0",
        ]:
            try: c.execute(sql)
            except sqlite3.OperationalError: pass

        # ── Migración contraseñas planas → hash ─────────────────────
        c.execute("SELECT id, clave FROM usuarios")
        for uid, clave in c.fetchall():
            if len(clave) != 64:
                c.execute("UPDATE usuarios SET clave=? WHERE id=?", (hashear_clave(clave), uid))

        clave_def = hashear_clave("1234")
        for socio in SOCIOS:
            c.execute("INSERT OR IGNORE INTO usuarios(usuario,clave) VALUES(?,?)", (socio, clave_def))

        conn.commit()

inicializar_base_datos()

# =====================================================================
# 5. HELPERS DE BASE DE DATOS — FINANZAS
# =====================================================================
def guardar_flujo(anio, mes_nombre, seccion, concepto, monto):
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        conn.execute("""INSERT INTO flujo_caja(anio,mes_nombre,seccion,concepto,monto)
            VALUES(?,?,?,?,?)
            ON CONFLICT(anio,mes_nombre,concepto) DO UPDATE SET monto=excluded.monto""",
            (anio, mes_nombre, seccion, concepto, monto))
        conn.commit()

def cargar_flujo(anio):
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        rows = conn.execute(
            "SELECT mes_nombre,seccion,concepto,monto FROM flujo_caja WHERE anio=?", (anio,)
        ).fetchall()
    # Devuelve dict: {(mes, concepto): monto}
    return {(r[0], r[2]): r[3] for r in rows}

def guardar_costo_prod(prenda, talla, componente, costo, precio_venta):
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        conn.execute("""INSERT INTO costo_produccion(prenda,talla,componente,costo,precio_venta)
            VALUES(?,?,?,?,?)
            ON CONFLICT(prenda,talla,componente) DO UPDATE SET costo=excluded.costo, precio_venta=excluded.precio_venta""",
            (prenda, talla, componente, costo, precio_venta))
        conn.commit()

def cargar_costos_prod():
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        rows = conn.execute(
            "SELECT prenda,talla,componente,costo,precio_venta FROM costo_produccion"
        ).fetchall()
    # {(prenda, talla, componente): (costo, precio_venta)}
    return {(r[0],r[1],r[2]): (r[3],r[4]) for r in rows}

# =====================================================================
# 6. CARGA DE DATOS GENERALES EN MEMORIA
# =====================================================================
def cargar_ventas_db():
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        rows = conn.execute("""SELECT id,fecha,mes,mes_nombre,anio,sku,producto,
            categoria,talla,canal,cliente,precio,costo,utilidad,vendedor FROM ventas""").fetchall()
    st.session_state.ventas = [
        {"id":x[0],"Fecha":x[1],"Mes":x[2],"Mes_Nombre":x[3],"Año":x[4],"SKU":x[5],
         "Producto":x[6],"Categoría":x[7],"Talla":x[8],"Canal":x[9],"Cliente":x[10],
         "Precio":x[11],"Costo":x[12],"Utilidad":x[13],"Vendedor":x[14]} for x in rows]

def cargar_gastos_db():
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        rows = conn.execute("""SELECT id,fecha,mes,mes_nombre,anio,concepto,
            categoria,responsable,monto FROM gastos""").fetchall()
    st.session_state.gastos = [
        {"id":x[0],"Fecha":x[1],"Mes":x[2],"Mes_Nombre":x[3],"Año":x[4],
         "Concepto":x[5],"Categoría":x[6],"Responsable":x[7],"Monto":x[8]} for x in rows]

def cargar_inventario_db():
    with sqlite3.connect(DB_NAME, timeout=20) as conn:
        rows = conn.execute("SELECT id,producto,categoria,talla,stock,costo_base FROM inventario").fetchall()
    st.session_state.inventario = [
        {"id":x[0],"Producto":x[1],"Categoría":x[2],"Talla":x[3],"Stock":x[4],"Costo_Base":x[5]}
        for x in rows]

def cargar_datos_memoria():
    if "ventas"     not in st.session_state: cargar_ventas_db()
    if "gastos"     not in st.session_state: cargar_gastos_db()
    if "inventario" not in st.session_state: cargar_inventario_db()

# =====================================================================
# 7. GESTIÓN DE SESIÓN
# =====================================================================
cookie_manager = stx.CookieManager(key="villan_manager")

if "logueado"       not in st.session_state: st.session_state.logueado       = False
if "usuario_actual" not in st.session_state: st.session_state.usuario_actual = ""

cookie_usuario = cookie_manager.get(cookie="villan_user")
if cookie_usuario and not st.session_state.logueado:
    st.session_state.logueado       = True
    st.session_state.usuario_actual = cookie_usuario.lower()

# =====================================================================
# 8. MÓDULO FINANZAS — FLUJO DE CAJA
# =====================================================================
def modulo_flujo_caja():
    st.title("💰 Flujo de Caja Mensual")
    st.caption("Llena cada celda con el monto real del mes. Los totales y utilidad se calculan solos.")

    anio_sel = st.selectbox("Año", [datetime.now().year, datetime.now().year - 1,
                                     datetime.now().year + 1], key="fc_anio")
    datos_db = cargar_flujo(anio_sel)

    # ── Formulario de edición por sección ────────────────────────────
    todos_los_cambios = {}  # {(mes, seccion, concepto): monto}

    SECCION_LABELS = {
        "ingresos":  ("📥 INGRESOS",           "#1B5E20"),
        "costos":    ("🏭 COSTOS PRODUCCIÓN",   "#BF360C"),
        "gastos_op": ("💸 GASTOS OPERATIVOS",   "#1A237E"),
    }

    # Acumular totales por mes para calcular utilidad
    totales_mes = {m: {"ingresos":0.0,"costos":0.0,"gastos_op":0.0} for m in MESES_ORD}

    with st.form("form_flujo_caja"):
        for seccion, (label, color) in SECCION_LABELS.items():
            st.markdown(f"<h4 style='color:{color};margin-top:1.2rem'>{label}</h4>",
                        unsafe_allow_html=True)

            conceptos = CATS_FLUJO[seccion]
            # Construir tabla: filas=conceptos, columnas=meses
            cols_header = st.columns([2] + [1]*12)
            cols_header[0].markdown("**Concepto**")
            for i, m in enumerate(MESES_ORD):
                cols_header[i+1].markdown(f"**{m[:3]}**")

            for concepto in conceptos:
                cols_row = st.columns([2] + [1]*12)
                cols_row[0].markdown(concepto)
                for i, mes in enumerate(MESES_ORD):
                    val_actual = datos_db.get((mes, concepto), 0.0)
                    nuevo_val  = cols_row[i+1].number_input(
                        label="S/", value=float(val_actual), min_value=0.0,
                        step=1.0, label_visibility="collapsed",
                        key=f"fc_{seccion}_{concepto}_{mes}_{anio_sel}"
                    )
                    todos_los_cambios[(mes, seccion, concepto)] = nuevo_val
                    totales_mes[mes][seccion] += nuevo_val

            st.divider()

        guardar_btn = st.form_submit_button("💾 Guardar Flujo de Caja", use_container_width=True)

    if guardar_btn:
        for (mes, seccion, concepto), monto in todos_los_cambios.items():
            guardar_flujo(anio_sel, mes, seccion, concepto, monto)
        st.success("✅ Flujo de caja guardado correctamente.")
        time.sleep(0.4)
        st.rerun()

    # ── Tabla resumen de resultados ───────────────────────────────────
    st.subheader("📊 Resumen Anual")

    filas_resumen = []
    for mes in MESES_ORD:
        t = totales_mes[mes]
        ing  = t["ingresos"]
        cos  = t["costos"]
        gas  = t["gastos_op"]
        ut_b = ing - cos
        ut_n = ut_b - gas
        margen = (ut_n / ing * 100) if ing > 0 else 0.0
        filas_resumen.append({
            "Mes": mes[:3], "Ingresos": ing, "Costos Prod.": cos,
            "Gastos Op.": gas, "Util. Bruta": ut_b,
            "Util. Neta": ut_n, "Margen %": margen
        })

    df_res = pd.DataFrame(filas_resumen)

    # Fila de totales anuales
    total_row = {
        "Mes": "TOTAL AÑO",
        "Ingresos":    df_res["Ingresos"].sum(),
        "Costos Prod.":df_res["Costos Prod."].sum(),
        "Gastos Op.":  df_res["Gastos Op."].sum(),
        "Util. Bruta": df_res["Util. Bruta"].sum(),
        "Util. Neta":  df_res["Util. Neta"].sum(),
        "Margen %":    (df_res["Util. Neta"].sum() / df_res["Ingresos"].sum() * 100)
                       if df_res["Ingresos"].sum() > 0 else 0.0,
    }
    df_res = pd.concat([df_res, pd.DataFrame([total_row])], ignore_index=True)

    # Formato de moneda
    fmt_cols = ["Ingresos","Costos Prod.","Gastos Op.","Util. Bruta","Util. Neta"]
    def estilo_utilidad(val):
        if isinstance(val, (int, float)):
            if val > 0: return "color:#69DB7C;font-weight:bold"
            elif val < 0: return "color:#FF5252;font-weight:bold"
        return ""
    
    styled = df_res.style\
        .format({c: "S/ {:,.2f}" for c in fmt_cols})\
        .format({"Margen %": "{:.1f}%"})\
        .map(estilo_utilidad, subset=["Util. Neta"])
    st.dataframe(styled, use_container_width=True, height=460)

    # ── Dividendos por socio ─────────────────────────────────────────
    utilidad_total_anual = df_res.loc[df_res["Mes"]=="TOTAL AÑO","Util. Neta"].values[0]
    st.subheader("🤝 Dividendos por Socio")
    d1, d2, d3 = st.columns(3)
    for col, nombre in zip([d1,d2,d3], ["Cesar","Larry","Jahairo"]):
        col.metric(f"💰 {nombre}", f"S/ {utilidad_total_anual/3:,.2f}")

    # ── Gráfico de utilidad neta mensual ─────────────────────────────
    st.subheader("📈 Utilidad Neta por Mes")
    df_chart = df_res[df_res["Mes"] != "TOTAL AÑO"][["Mes","Util. Neta"]].set_index("Mes")
    st.bar_chart(df_chart)

    # ── Exportar a Excel ─────────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_res.to_excel(writer, index=False, sheet_name=f"Flujo_Caja_{anio_sel}")
    buf.seek(0)
    st.download_button("📥 Exportar Flujo de Caja (Excel)", data=buf,
        file_name=f"FlujoCaja_Villan_{anio_sel}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# =====================================================================
# 9. MÓDULO FINANZAS — COSTO DE PRODUCCIÓN
# =====================================================================
def modulo_costo_produccion():
    st.title("🏭 Costo de Producción por Prenda")
    st.caption("Ingresa el costo de cada componente por prenda y talla. El margen se calcula automáticamente.")

    datos_db = cargar_costos_prod()

    tabs = st.tabs([f"👕 {p}" for p in PRENDAS])

    for tab, prenda in zip(tabs, PRENDAS):
        with tab:
            st.markdown(f"#### {prenda} — Costos unitarios por talla (S/)")

            with st.form(f"form_costo_{prenda}"):
                # Cabecera
                cols_h = st.columns([1.2] + [1]*len(TALLAS))
                cols_h[0].markdown("**Componente**")
                for i, talla in enumerate(TALLAS):
                    cols_h[i+1].markdown(f"**{talla}**")

                cambios_prenda = {}

                for comp in COMPONENTES_COSTO:
                    cols_r = st.columns([1.2] + [1]*len(TALLAS))
                    cols_r[0].markdown(comp)
                    for i, talla in enumerate(TALLAS):
                        val = datos_db.get((prenda, talla, comp), (0.0, 0.0))[0]
                        nuevo = cols_r[i+1].number_input(
                            "S/", value=float(val), min_value=0.0, step=0.5,
                            label_visibility="collapsed",
                            key=f"cp_{prenda}_{talla}_{comp}"
                        )
                        cambios_prenda[(talla, comp)] = nuevo

                # Precio de venta por talla
                st.markdown("---")
                cols_pv = st.columns([1.2] + [1]*len(TALLAS))
                cols_pv[0].markdown("**💲 Precio Venta**")
                precios_venta = {}
                for i, talla in enumerate(TALLAS):
                    val_pv = datos_db.get((prenda, talla, COMPONENTES_COSTO[0]), (0.0, 0.0))[1]
                    pv = cols_pv[i+1].number_input(
                        "S/", value=float(val_pv), min_value=0.0, step=1.0,
                        label_visibility="collapsed",
                        key=f"pv_{prenda}_{talla}"
                    )
                    precios_venta[talla] = pv

                guardar_cp = st.form_submit_button(f"💾 Guardar costos de {prenda}", use_container_width=True)

            if guardar_cp:
                for (talla, comp), costo in cambios_prenda.items():
                    guardar_costo_prod(prenda, talla, comp, costo, precios_venta[talla])
                st.success(f"✅ Costos de {prenda} guardados.")
                time.sleep(0.3)
                st.rerun()

            # ── Tabla de resumen de márgenes ─────────────────────────
            st.markdown(f"#### Resumen de Rentabilidad — {prenda}")
            datos_actualizados = cargar_costos_prod()
            filas_margen = []
            for talla in TALLAS:
                costo_total = sum(
                    datos_actualizados.get((prenda, talla, c), (0.0, 0.0))[0]
                    for c in COMPONENTES_COSTO
                )
                precio_venta = datos_actualizados.get((prenda, talla, COMPONENTES_COSTO[0]), (0.0, 0.0))[1]
                margen_s    = precio_venta - costo_total
                margen_pct  = (margen_s / precio_venta * 100) if precio_venta > 0 else 0.0
                filas_margen.append({
                    "Talla": talla,
                    "Costo Total": costo_total,
                    "Precio Venta": precio_venta,
                    "Margen S/": margen_s,
                    "Margen %": margen_pct,
                })

            df_m = pd.DataFrame(filas_margen)
            
            def estilo_margen(val):
                if isinstance(val, (int, float)):
                    if val > 0: return "color:#69DB7C;font-weight:bold"
                    elif val < 0: return "color:#FF5252;font-weight:bold"
                return ""
            
            styled_m = df_m.style\
                .format({"Costo Total":"S/ {:.2f}","Precio Venta":"S/ {:.2f}",
                         "Margen S/":"S/ {:.2f}","Margen %":"{:.1f}%"})\
                .map(estilo_margen, subset=["Margen S/","Margen %"])
            st.dataframe(styled_m, use_container_width=True, hide_index=True)


# =====================================================================
# 10. MÓDULO FINANZAS — DASHBOARD SOCIOS
# =====================================================================
def modulo_dashboard_socios():
    st.title("📊 Dashboard Ejecutivo — Socios")

    anio_sel = st.selectbox("Año a analizar", [datetime.now().year, datetime.now().year-1,
                                                datetime.now().year+1], key="dash_anio")
    datos_flujo   = cargar_flujo(anio_sel)
    datos_costos  = cargar_costos_prod()

    # ── Calcular totales anuales desde flujo de caja ─────────────────
    def total_seccion(seccion):
        return sum(v for (mes, conc), v in datos_flujo.items()
                   if any(conc in CATS_FLUJO[seccion] for _ in [1]))

    # Recalcular correctamente por sección
    tot_ing  = sum(v for (m,c),v in datos_flujo.items() if c in CATS_FLUJO["ingresos"])
    tot_cos  = sum(v for (m,c),v in datos_flujo.items() if c in CATS_FLUJO["costos"])
    tot_gas  = sum(v for (m,c),v in datos_flujo.items() if c in CATS_FLUJO["gastos_op"])
    ut_bruta = tot_ing - tot_cos
    ut_neta  = ut_bruta - tot_gas
    margen   = (ut_neta / tot_ing * 100) if tot_ing > 0 else 0.0
    dividendo = ut_neta / 3

    # ── KPI Cards ────────────────────────────────────────────────────
    st.markdown("### 💡 Indicadores Clave del Año")
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("Ventas Totales",      f"S/ {tot_ing:,.2f}")
    k2.metric("Costos Producción",   f"S/ {tot_cos:,.2f}")
    k3.metric("Gastos Operativos",   f"S/ {tot_gas:,.2f}")
    k4.metric("Utilidad Neta",       f"S/ {ut_neta:,.2f}")
    k5.metric("Margen Neto",         f"{margen:.1f}%")
    k6.metric("Dividendo x Socio",   f"S/ {dividendo:,.2f}")

    st.divider()

    # ── Dividendos individuales ───────────────────────────────────────
    st.markdown("### 🤝 Dividendos por Socio")
    dc1,dc2,dc3 = st.columns(3)
    for col, nombre in zip([dc1,dc2,dc3],["Cesar","Larry","Jahairo"]):
        col.metric(f"💰 {nombre}", f"S/ {dividendo:,.2f}",
                   delta=f"{margen:.1f}% margen")

    st.divider()

    # ── Gráficos en dos columnas ──────────────────────────────────────
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("### 📈 Utilidad Neta por Mes")
        meses_chart = []
        for mes in MESES_ORD:
            ing_m  = sum(v for (m,c),v in datos_flujo.items() if m==mes and c in CATS_FLUJO["ingresos"])
            cos_m  = sum(v for (m,c),v in datos_flujo.items() if m==mes and c in CATS_FLUJO["costos"])
            gas_m  = sum(v for (m,c),v in datos_flujo.items() if m==mes and c in CATS_FLUJO["gastos_op"])
            meses_chart.append({"Mes": mes[:3], "Utilidad Neta": ing_m - cos_m - gas_m,
                                 "Ingresos": ing_m})
        df_g1 = pd.DataFrame(meses_chart).set_index("Mes")
        st.bar_chart(df_g1[["Ingresos","Utilidad Neta"]])

    with col_g2:
        st.markdown("### 🥧 Distribución de Egresos")
        if tot_cos > 0 or tot_gas > 0:
            df_pie = pd.DataFrame({
                "Categoría": ["Costos Producción","Gastos Operativos","Utilidad"],
                "Monto":     [tot_cos, tot_gas, max(ut_neta,0)]
            }).set_index("Categoría")
            st.bar_chart(df_pie)
        else:
            st.info("Sin datos de egresos para el año seleccionado.")

    st.divider()

    # ── Rentabilidad por prenda ───────────────────────────────────────
    st.markdown("### 👕 Rentabilidad por Prenda (Promedio todas las tallas)")
    filas_rent = []
    for prenda in PRENDAS:
        costos_prenda = []
        precios_prenda = []
        for talla in TALLAS:
            costo_t = sum(datos_costos.get((prenda,talla,c),(0.0,0.0))[0] for c in COMPONENTES_COSTO)
            precio_t = datos_costos.get((prenda,talla,COMPONENTES_COSTO[0]),(0.0,0.0))[1]
            if costo_t > 0 or precio_t > 0:
                costos_prenda.append(costo_t)
                precios_prenda.append(precio_t)
        if costos_prenda:
            cp = sum(costos_prenda)/len(costos_prenda)
            pp = sum(precios_prenda)/len(precios_prenda)
            ms = pp - cp
            mp = (ms/pp*100) if pp > 0 else 0.0
        else:
            cp = pp = ms = mp = 0.0
        filas_rent.append({"Prenda":prenda,"Costo Prom.":cp,
                            "Precio Prom.":pp,"Margen S/":ms,"Margen %":mp})

    df_rent = pd.DataFrame(filas_rent)
    
    def estilo_rent(val):
        if isinstance(val, (int, float)):
            if val > 0: return "color:#69DB7C;font-weight:bold"
            elif val < 0: return "color:#FF5252;font-weight:bold"
        return ""
    
    styled_rent = df_rent.style\
        .format({"Costo Prom.":"S/ {:.2f}","Precio Prom.":"S/ {:.2f}",
                 "Margen S/":"S/ {:.2f}","Margen %":"{:.1f}%"})\
        .map(estilo_rent, subset=["Margen S/","Margen %"])
    st.dataframe(styled_rent, use_container_width=True, hide_index=True)

    st.divider()

    # ── Tallas más rentables por prenda ──────────────────────────────
    st.markdown("### 📐 Margen por Talla (detalle)")
    tabs_t = st.tabs([f"👕 {p}" for p in PRENDAS])
    for tab, prenda in zip(tabs_t, PRENDAS):
        with tab:
            filas_t = []
            for talla in TALLAS:
                ct = sum(datos_costos.get((prenda,talla,c),(0.0,0.0))[0] for c in COMPONENTES_COSTO)
                pt = datos_costos.get((prenda,talla,COMPONENTES_COSTO[0]),(0.0,0.0))[1]
                mt = pt - ct
                pct = (mt/pt*100) if pt > 0 else 0.0
                filas_t.append({"Talla":talla,"Costo":ct,"Precio":pt,"Margen S/":mt,"Margen %":pct})
            df_t = pd.DataFrame(filas_t)
            
            def estilo_t(val):
                if isinstance(val, (int, float)):
                    if val > 0: return "color:#69DB7C;font-weight:bold"
                    elif val < 0: return "color:#FF5252;font-weight:bold"
                return ""
            
            st.dataframe(
                df_t.style
                .format({"Costo":"S/ {:.2f}","Precio":"S/ {:.2f}",
                         "Margen S/":"S/ {:.2f}","Margen %":"{:.1f}%"})
                .map(estilo_t, subset=["Margen S/","Margen %"]),
                use_container_width=True, hide_index=True
            )


# =====================================================================
# 11. ESTRUCTURA PRINCIPAL DE LA APP
# =====================================================================
if not st.session_state.logueado:
    st.title("🔐 ERP VILLAN")
    st.write("Por favor, identifícate para ingresar al sistema.")
    usuario_input = st.text_input("Usuario")
    clave         = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        u_limpio   = usuario_input.strip().lower()
        clave_hash = hashear_clave(clave)
        with sqlite3.connect(DB_NAME, timeout=20) as conn:
            resultado = conn.execute(
                "SELECT usuario FROM usuarios WHERE LOWER(usuario)=? AND clave=?",
                (u_limpio, clave_hash)
            ).fetchone()
        if resultado:
            st.session_state.logueado       = True
            st.session_state.usuario_actual = resultado[0].lower()
            cookie_manager.set(cookie="villan_user", val=resultado[0].lower(), max_age=2592000)
            st.success("Acceso correcto. Preparando entorno...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

else:
    cargar_datos_memoria()
    es_socio = st.session_state.usuario_actual in SOCIOS

    if es_socio:
        opciones_menu = ["Dashboard", "Ventas", "Inventario", "Gastos",
                         "── FINANZAS SOCIOS ──",
                         "Flujo de Caja", "Costo de Producción", "Dashboard Socios",
                         "── ADMIN ──",
                         "Gestionar Usuarios"]
    else:
        opciones_menu = ["Ventas", "Inventario"]

    menu = st.sidebar.selectbox("Menú de Navegación", opciones_menu)

    if st.sidebar.button("🔄 Actualizar Datos"):
        cargar_ventas_db(); cargar_gastos_db(); cargar_inventario_db()
        st.rerun()

    if st.sidebar.button("❌ Cerrar Sesión"):
        try: cookie_manager.delete(cookie="villan_user")
        except: pass
        st.session_state.logueado       = False
        st.session_state.usuario_actual = ""
        for k in ["ventas","gastos","inventario"]:
            if k in st.session_state: del st.session_state[k]
        time.sleep(1.0)
        st.rerun()

    # ================================================================
    # MÓDULO: DASHBOARD GENERAL
    # ================================================================
    if menu == "Dashboard" and es_socio:
        st.title("📊 Balance General Financiero")
        st.write(f"👋 ¡Bienvenido Socio, **{st.session_state.usuario_actual.title()}**!")

        años_disponibles = sorted(set(v["Año"] for v in st.session_state.ventas), reverse=True) \
                           if st.session_state.ventas else [datetime.now().year]
        col_f1, col_f2 = st.columns([1,3])
        with col_f1:
            año_sel = st.selectbox("Filtrar por Año", ["Todos"]+[str(a) for a in años_disponibles])
        with col_f2:
            mes_sel = st.selectbox("Filtrar por Mes", ["Todos"]+list(MESES.values()))

        ventas_f = st.session_state.ventas
        gastos_f = st.session_state.gastos
        if año_sel != "Todos":
            ventas_f = [v for v in ventas_f if str(v["Año"])==año_sel]
            gastos_f = [g for g in gastos_f if str(g["Año"])==año_sel]
        if mes_sel != "Todos":
            ventas_f = [v for v in ventas_f if v.get("Mes_Nombre")==mes_sel]
            gastos_f = [g for g in gastos_f if g.get("Mes_Nombre")==mes_sel]

        tv = sum(float(x["Precio"])  for x in ventas_f)
        tc = sum(float(x["Costo"])   for x in ventas_f)
        tg = sum(float(x["Monto"])   for x in gastos_f)
        ut = tv - tc - tg
        mg = (ut/tv*100) if tv > 0 else 0.0

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Ventas Totales",   f"S/ {tv:,.2f}")
        c2.metric("Costos Producción",f"S/ {tc:,.2f}")
        c3.metric("Gastos Operativos",f"S/ {tg:,.2f}")
        c4.metric("Utilidad Neta",    f"S/ {ut:,.2f}")
        c5.metric("Margen Beneficio", f"{mg:.2f}%")
        st.divider()

        if ventas_f:
            df_v = pd.DataFrame(ventas_f)
            col_ch1, col_ch2 = st.columns(2)
            with col_ch1:
                st.subheader("🏆 Prendas Más Vendidas por SKU")
                st.bar_chart(df_v["Producto"].value_counts())
            with col_ch2:
                st.subheader("📅 Ventas por Mes")
                ventas_mes = df_v.groupby("Mes_Nombre")["Precio"].sum()
                ventas_mes = ventas_mes.reindex([m for m in MESES_ORD if m in ventas_mes.index])
                st.bar_chart(ventas_mes)

    # ================================================================
    # MÓDULO: VENTAS
    # ================================================================
    elif menu == "Ventas":
        st.title("🛒 Registro de Transacciones de Venta")
        st.write(f"👤 Atendido por: **{st.session_state.usuario_actual.title()}**")

        inv_disp = [i for i in st.session_state.inventario if i["Stock"] > 0]
        if not inv_disp:
            st.info("⚠️ No hay productos con stock disponible.")
        else:
            with st.form("form_ventas"):
                st.subheader("Nueva Venta")
                opciones = [f"{i['Producto']} (Talla {i['Talla']}) - Disponibles: {i['Stock']} und"
                            for i in inv_disp]
                sel = st.selectbox("Selecciona el artículo:", opciones)
                col1,col2 = st.columns(2)
                with col1:
                    fecha = st.date_input("Fecha de Venta", datetime.now())
                    canal = st.selectbox("Canal", ["Tienda Física","Instagram","WhatsApp","TikTok","Otro"])
                    cliente = st.text_input("Cliente", "Cliente General")
                with col2:
                    precio = st.number_input("Precio (S/)", min_value=1.0, value=89.90, step=1.0)
                btn = st.form_submit_button("🚀 Registrar y Descontar Stock")

            if btn:
                obj = inv_disp[opciones.index(sel)]
                if obj["Stock"] <= 0:
                    st.error("❌ Sin stock.")
                else:
                    nuevo_stk  = obj["Stock"] - 1
                    costo_real = float(obj.get("Costo_Base", 0.0))
                    ut_calc    = float(precio) - costo_real
                    ts         = datetime.now().strftime("%H%M%S")
                    sku        = f"{obj['Producto'][:3].upper()}-{obj['Talla']}-{ts}"
                    vendedor   = st.session_state.usuario_actual
                    fecha_str  = fecha.strftime("%d/%m/%Y")
                    mes_str    = fecha.strftime("%m")
                    mes_nom    = MESES[mes_str]
                    anio       = fecha.year

                    with sqlite3.connect(DB_NAME, timeout=20) as conn:
                        conn.execute("UPDATE inventario SET stock=? WHERE id=?", (nuevo_stk, obj["id"]))
                        conn.execute("""INSERT INTO ventas(fecha,mes,mes_nombre,anio,sku,producto,
                            categoria,talla,canal,cliente,precio,costo,utilidad,vendedor)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (fecha_str,mes_str,mes_nom,anio,sku,obj["Producto"],obj["Categoría"],
                             obj["Talla"],canal,cliente,precio,costo_real,ut_calc,vendedor))
                        nid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        conn.commit()

                    obj["Stock"] = nuevo_stk
                    st.session_state.ventas.append({
                        "id":nid,"Fecha":fecha_str,"Mes":mes_str,"Mes_Nombre":mes_nom,
                        "Año":anio,"SKU":sku,"Producto":obj["Producto"],"Categoría":obj["Categoría"],
                        "Talla":obj["Talla"],"Canal":canal,"Cliente":cliente,
                        "Precio":precio,"Costo":costo_real,"Utilidad":ut_calc,"Vendedor":vendedor
                    })
                    st.success("✅ Venta registrada.")
                    time.sleep(0.5); st.rerun()

        st.divider()
        if st.session_state.ventas:
            df_v = pd.DataFrame(st.session_state.ventas)
            st.subheader("📋 Historial de Ventas")
            mostrar_todo = st.toggle("Mostrar todas", value=False)
            df_disp = (df_v if mostrar_todo else df_v.tail(100)).copy()
            df_disp.index = range(1, len(df_disp)+1)
            ocultar = ["id","Mes"] + ([] if es_socio else ["Costo","Utilidad"])
            st.dataframe(df_disp.drop(columns=ocultar, errors="ignore"), use_container_width=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_disp.drop(columns=ocultar, errors="ignore").to_excel(w, index=False, sheet_name="Ventas")
            buf.seek(0)
            st.download_button("📥 Exportar Ventas (Excel)", data=buf,
                file_name=f"Ventas_Villan_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            st.subheader("🗑 Anular Venta")
            mapa_v = {v["id"]:f"ID:{v['id']} | {v['Fecha']} | {v['SKU']} | {v['Vendedor'].title()} | S/ {v['Precio']}"
                      for v in st.session_state.ventas}
            id_sel = st.selectbox("Transacción a cancelar:", list(mapa_v.keys()), format_func=lambda x: mapa_v[x])
            v_sel  = next((v for v in st.session_state.ventas if v["id"]==id_sel), None)
            if v_sel and (es_socio or st.session_state.usuario_actual==v_sel["Vendedor"]):
                if st.button("⚠️ Confirmar Anulación"):
                    with sqlite3.connect(DB_NAME, timeout=20) as conn:
                        for item in st.session_state.inventario:
                            if item["Producto"]==v_sel["Producto"] and item["Talla"]==v_sel["Talla"]:
                                item["Stock"] += 1
                                conn.execute("UPDATE inventario SET stock=? WHERE id=?", (item["Stock"],item["id"]))
                                break
                        conn.execute("DELETE FROM ventas WHERE id=?", (v_sel["id"],))
                        conn.commit()
                    st.session_state.ventas = [v for v in st.session_state.ventas if v["id"]!=id_sel]
                    st.success("Venta anulada y stock devuelto."); time.sleep(0.8); st.rerun()

    # ================================================================
    # MÓDULO: INVENTARIO
    # ================================================================
    elif menu == "Inventario":
        st.title("📦 Almacén Central e Inventario")
        if es_socio:
            with st.expander("➕ Ingreso de Mercadería", expanded=False):
                prod  = st.text_input("Nombre de la Prenda").strip().title()
                cat   = st.selectbox("Categoría", ["Pantalón","Polo","Polera","Casaca","Short","Otro"])
                tll   = st.selectbox("Talla", TALLAS)
                stk   = st.number_input("Unidades", min_value=1, step=1)
                c_b   = st.number_input("Costo Unitario (S/)", min_value=0.0, value=40.0, step=1.0)
                if st.button("💾 Guardar Ingreso"):
                    if prod:
                        with sqlite3.connect(DB_NAME, timeout=20) as conn:
                            existe = False
                            for item in st.session_state.inventario:
                                if item["Producto"]==prod and item["Talla"]==tll:
                                    item["Stock"] += stk; item["Costo_Base"] = c_b
                                    conn.execute("UPDATE inventario SET stock=?,costo_base=? WHERE id=?",
                                                 (item["Stock"],c_b,item["id"]))
                                    existe = True; break
                            if not existe:
                                conn.execute("INSERT INTO inventario(producto,categoria,talla,stock,costo_base) VALUES(?,?,?,?,?)",
                                             (prod,cat,tll,stk,c_b))
                                nid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                                st.session_state.inventario.append({"id":nid,"Producto":prod,"Categoría":cat,
                                                                     "Talla":tll,"Stock":stk,"Costo_Base":c_b})
                            conn.commit()
                        st.success("✅ Inventario actualizado."); time.sleep(0.5); st.rerun()
                    else:
                        st.error("Escribe el nombre de la prenda.")

        if st.session_state.inventario:
            df_inv = pd.DataFrame(st.session_state.inventario)
            df_inv.index = range(1, len(df_inv)+1)
            ocultar_inv = ["id"] + ([] if es_socio else ["Costo_Base"])
            st.subheader("📋 Estado del Almacén")
            df_inv_m = df_inv.drop(columns=ocultar_inv, errors="ignore")
            st.dataframe(df_inv_m, use_container_width=True)
            bajo = df_inv_m[df_inv_m["Stock"] <= 3]
            st.subheader("⚠ Alertas de Stock Crítico")
            if not bajo.empty:
                st.error("Requieren reposición inmediata:")
                st.dataframe(bajo, use_container_width=True)
            else:
                st.success("Almacén estable. Todo sobre el margen crítico.")

    # ================================================================
    # MÓDULO: GASTOS
    # ================================================================
    elif menu == "Gastos" and es_socio:
        st.title("💸 Control de Gastos y Egresos")
        with st.form("form_gastos"):
            f_g  = st.date_input("Fecha", datetime.now())
            con  = st.text_input("Concepto").strip().title()
            cat  = st.selectbox("Clasificación", ["Viaje Gamarra","Hospedaje","Comida","Marketing",
                                                   "Meta Ads","Transporte","Suministros","Otro"])
            resp = st.text_input("Responsable").strip().title()
            mon  = st.number_input("Monto (S/)", min_value=0.0, step=1.0)
            btn_g = st.form_submit_button("Registrar Egreso")

        if btn_g:
            if con and resp and mon > 0:
                fs = f_g.strftime("%d/%m/%Y"); ms = f_g.strftime("%m")
                mn = MESES[ms]; ai = f_g.year
                with sqlite3.connect(DB_NAME, timeout=20) as conn:
                    conn.execute("INSERT INTO gastos(fecha,mes,mes_nombre,anio,concepto,categoria,responsable,monto) VALUES(?,?,?,?,?,?,?,?)",
                                 (fs,ms,mn,ai,con,cat,resp,mon))
                    nid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.commit()
                st.session_state.gastos.append({"id":nid,"Fecha":fs,"Mes":ms,"Mes_Nombre":mn,
                    "Año":ai,"Concepto":con,"Categoría":cat,"Responsable":resp,"Monto":mon})
                st.success("✅ Gasto guardado."); time.sleep(0.5); st.rerun()
            else:
                st.error("⚠️ Completa todos los campos y monto > 0.")

        st.divider()
        if st.session_state.gastos:
            df_g = pd.DataFrame(st.session_state.gastos)
            st.subheader("📋 Libro de Egresos")
            st.dataframe(df_g.drop(columns=["id","Mes"],errors="ignore"), use_container_width=True)
            mapa_g = {g["id"]:f"ID:{g['id']} | {g['Fecha']} | {g['Concepto']} | S/ {g['Monto']}"
                      for g in st.session_state.gastos}
            id_g = st.selectbox("Egreso a anular:", list(mapa_g.keys()), format_func=lambda x: mapa_g[x])
            if st.button("⚠️ Confirmar Anulación de Egreso"):
                with sqlite3.connect(DB_NAME, timeout=20) as conn:
                    conn.execute("DELETE FROM gastos WHERE id=?", (id_g,)); conn.commit()
                st.session_state.gastos = [g for g in st.session_state.gastos if g["id"]!=id_g]
                st.success("Egreso eliminado."); time.sleep(0.5); st.rerun()

    # ================================================================
    # MÓDULOS DE FINANZAS — SOLO SOCIOS
    # ================================================================
    elif menu == "Flujo de Caja" and es_socio:
        modulo_flujo_caja()

    elif menu == "Costo de Producción" and es_socio:
        modulo_costo_produccion()

    elif menu == "Dashboard Socios" and es_socio:
        modulo_dashboard_socios()

    elif menu in ("── FINANZAS SOCIOS ──", "── ADMIN ──"):
        st.info("Selecciona una opción del menú.")

    # ================================================================
    # MÓDULO: GESTIONAR USUARIOS
    # ================================================================
    elif menu == "Gestionar Usuarios" and es_socio:
        st.title("👥 Panel de Usuarios")
        with sqlite3.connect(DB_NAME, timeout=20) as conn:
            lista_u = conn.execute("SELECT id,usuario FROM usuarios").fetchall()
        df_u = pd.DataFrame(lista_u, columns=["ID","Usuario"])
        df_u.index = range(1, len(df_u)+1)
        st.dataframe(df_u, use_container_width=True)
        st.divider()
        st.subheader("➕ Nuevo Usuario")
        cu1,cu2 = st.columns(2)
        with cu1: nu = st.text_input("Usuario").strip().lower()
        with cu2: nc = st.text_input("Contraseña", type="password")
        if st.button("Registrar"):
            if nu and nc:
                try:
                    with sqlite3.connect(DB_NAME, timeout=20) as conn:
                        conn.execute("INSERT INTO usuarios(usuario,clave) VALUES(?,?)", (nu, hashear_clave(nc)))
                        conn.commit()
                    st.success(f"✅ Usuario '{nu}' creado."); time.sleep(0.5); st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ El usuario ya existe.")
            else:
                st.error("❌ Completa ambos campos.")
        st.divider()
        st.subheader("🗑 Revocar Acceso")
        eliminables = [u for u in lista_u if u[1] not in SOCIOS]
        if eliminables:
            mapa_u = {u[0]: u[1].title() for u in eliminables}
            id_u = st.selectbox("Usuario a eliminar:", list(mapa_u.keys()), format_func=lambda x: mapa_u[x])
            if st.button("⚠️ Ejecutar Baja"):
                with sqlite3.connect(DB_NAME, timeout=20) as conn:
                    conn.execute("DELETE FROM usuarios WHERE id=?", (id_u,)); conn.commit()
                st.success(f"🗑 '{mapa_u[id_u]}' eliminado."); time.sleep(0.5); st.rerun()
        else:
            st.info("No hay vendedores eliminables. Los socios están protegidos.")