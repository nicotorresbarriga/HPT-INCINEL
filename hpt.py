import streamlit as st
import pandas as pd
import datetime
import os
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from supabase import create_client, Client

# 1. Configuración de página
st.set_page_config(
    page_title="Plataforma TechTrident",
    page_icon="⚓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Inyección CSS (Diseño Marino Oscuro Profundo de Alta Visibilidad)
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #000511 0%, #00122c 50%, #002353 100%);
    }
    h1, h2, h3, p, label, .stMarkdown, span {
        color: #ffffff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stButton>button {
        background-color: #00a8cc;
        color: white;
        border-radius: 8px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.4);
        transition: all 0.3s ease;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #007a99;
        box-shadow: 0 6px 8px rgba(0,0,0,0.5);
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        border-radius: 6px;
        border: 1px solid #00a8cc;
        color: #1a202c !important;
        background-color: #f8fafc !important;
        font-weight: 500;
    }
    div[data-testid="stCheckbox"] label span {
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# CLAVE MAESTRA ADMINISTRADOR
CLAVE_ADMIN = "9926"

# 3. Conexión a Supabase y Variables Globales de Enrutamiento
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

USUARIOS = {}
CENTROS_AREAS = {}

CENTROS_CORREOS = {
    "Centro Ninualac": "ninualac@blumar.com", 
    "Centro Dring 3": "centro.dring@blumar.com", 
    "Centro Punta cola": "puntacola@blumar.com",
    "Centro Midhurst": "midhurst@blumar.com", 
    "Centro Bobe": "bobe@blumar.com", 
    "Centro Ceres": "ceres@blumar.com",
    "Centro Cordoba 1": "cordoba11@blumar.com", 
    "Centro Cordoba 2": "cordoba22@blumar.com", 
    "Centro Perez de Arce": "perez@blumar.com"
}

# CORREOS UNIFICADOS (Operaciones y Prevención)
CORREOS_PREVENCION = ["reportesrovincinel@gmail.com", "reportesrovincinel@gmail.com"]

# RANGOS HORARIOS ESTANDARIZADOS
RANGO_INICIO = [f"{str(h).zfill(2)}:{str(m).zfill(2)}" for h in range(6, 12) for m in (0, 30)]  
RANGO_TERMINO = [f"{str(h).zfill(2)}:{str(m).zfill(2)}" for h in range(16, 21) for m in (0, 30)] 
RANGO_DURACION = ["5 minutos", "10 minutos", "15 minutos", "20 minutos", "25 minutos", "30 minutos"]
RANGO_HORA_DIFUSION = [f"{str(h).zfill(2)}:{str(m).zfill(2)}" for h in range(6, 13) for m in (0, 15, 30, 45) if not (h == 12 and m > 0)]

try:
    supabase = init_connection()
    res_usuarios = supabase.table('usuarios').select('*').execute()
    USUARIOS = {row['usuario']: row['contrasena'] for row in res_usuarios.data}
    
    res_centros = supabase.table('centros').select('*').execute()
    CENTROS_AREAS = {row['nombre']: row['area'] for row in res_centros.data}
except Exception as e:
    USUARIOS = {"Ntorres": "17909926", "Imuñoz": "12345678", "Pasencio": "98765432"}
    CENTROS_AREAS = {
        "Centro Ninualac": "Area Sur", "Centro Dring 3": "Area Sur", "Centro Punta cola": "Area Sur",
        "Centro Midhurst": "Area Norte", "Centro Bobe": "Area Norte", "Centro Ceres": "Area Norte",
        "Centro Cordoba 1": "Area Austral", "Centro Cordoba 2": "Area Austral", "Centro Perez de Arce": "Area Austral"
    }
    st.sidebar.warning("Advertencia: Conexión local activa.")

if 'local_hpt_history' not in st.session_state:
    st.session_state.local_hpt_history = []
if 'local_reportes_history' not in st.session_state:
    st.session_state.local_reportes_history = []

# 4. Inicialización del Administrador de Estados (Session State)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = ""
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'
if 'hpt_step' not in st.session_state:
    st.session_state.hpt_step = 1
if 'hpt_data' not in st.session_state:
    st.session_state.hpt_data = {
        "empresa": "Salmones Blumar", "fecha": datetime.date.today(), "hora_inicio": RANGO_INICIO[2],
        "hora_termino": RANGO_TERMINO[2], "centro": list(CENTROS_AREAS.keys())[0] if CENTROS_AREAS else "",
        "correo": "", "encargado": "", "ponton": "", "condicion_puerto": "Abierto", "tarea": "",
        "epp": [False]*7, "faena": "Inspeccion Red pecera", "erc": [False]*6, "tc_duracion": "15 minutos"
    }
if 'admin_acceso_historial' not in st.session_state:
    st.session_state.admin_acceso_historial = False
if 'admin_acceso_graficos' not in st.session_state:
    st.session_state.admin_acceso_graficos = False

# --- FUNCIONES GLOBALES ---
def set_page(page_name):
    st.session_state.current_page = page_name

def set_step(step_number):
    st.session_state.hpt_step = step_number

def procesar_firma(canvas_obj, filename):
    if canvas_obj.image_data is not None:
        img_data = canvas_obj.image_data
        firma_img = Image.fromarray((img_data).astype('uint8'), mode='RGBA')
        fondo_blanco = Image.new("RGB", firma_img.size, (255, 255, 255))
        fondo_blanco.paste(firma_img, mask=firma_img.split()[3])
        fondo_blanco.save(filename)
        return True
    return False

# ---------------------------------------------------------
# MÓDULO 1: SISTEMA DE AUTENTICACIÓN (LOGIN)
# ---------------------------------------------------------
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        st.markdown("<h2 style='text-align: center; color: white;'>Portal Operativo ROV</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("INGRESAR", use_container_width=True)
            
            if submitted:
                if user in USUARIOS and str(USUARIOS[user]) == str(password):
                    st.session_state.logged_in = True
                    st.session_state.current_user = user
                    st.session_state.current_page = 'main_menu'
                    st.rerun()
                else:
                    st.error("Credenciales inválidas.")

# ---------------------------------------------------------
# MÓDULO 2: MENÚ PRINCIPAL
# ---------------------------------------------------------
elif st.session_state.current_page == 'main_menu':
    st.title("Sistema de Gestión Operativa")
    st.write(f"Operador en turno: **{st.session_state.current_user}**")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⚓ MÓDULO HPT", use_container_width=True):
            set_page('hpt_menu')
            st.rerun()
    with col2:
        if st.button("🚢 REPORTE DIARIO", use_container_width=True):
            set_page('reporte_diario')
            st.rerun()
    with col3:
        if st.button("📊 HISTORIAL / AUDITORÍA", use_container_width=True):
            set_page('modulo_busqueda')
            st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)
    col_dash, col_logout = st.columns(2)
    with col_dash:
        if st.button("📈 GRÁFICOS GERENCIALES", use_container_width=True):
            set_page('panel_graficos')
            st.rerun()
    with col_logout:
        if st.button("🔒 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = ""
            set_page('login')
            st.rerun()

# ---------------------------------------------------------
# MÓDULO 3: SUBMENÚ HPT
# ---------------------------------------------------------
elif st.session_state.current_page == 'hpt_menu':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("Módulo HPT")
    st.divider()
    
    if st.button("➕ CREAR NUEVA HPT", use_container_width=True):
        set_step(1)
        set_page('hpt_nuevo')
        st.rerun()

# ---------------------------------------------------------
# MÓDULO 4: FLUJO DE CREACIÓN HPT
# ---------------------------------------------------------
elif st.session_state.current_page == 'hpt_nuevo':
    st.button("⬅️ Cancelar y Volver al Menú HPT", on_click=set_page, args=('hpt_menu',))
    st.title("Nueva HPT - Paso " + str(st.session_state.hpt_step))
    st.progress(st.session_state.hpt_step / 4.0)
    
    if st.session_state.hpt_step == 1:
        st.subheader("Datos Operativos")
        opciones_empresa = ["Salmones Blumar", "Salmones Blumar Magallanes"]
        idx_empresa = opciones_empresa.index(st.session_state.hpt_data.get("empresa", opciones_empresa[0])) if st.session_state.hpt_data.get("empresa") in opciones_empresa else 0
        empresa = st.selectbox("Empresa", opciones_empresa, index=idx_empresa)
        
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", value=st.session_state.hpt_data.get("fecha", datetime.date.today()))
            idx_hi = RANGO_INICIO.index(st.session_state.hpt_data["hora_inicio"]) if st.session_state.hpt_data["hora_inicio"] in RANGO_INICIO else 0
            hora_inicio = st.selectbox("Hora de Inicio", RANGO_INICIO, index=idx_hi)
            encargado = st.text_input("Encargado del Centro", value=st.session_state.hpt_data.get("encargado", ""))
            ponton = st.text_input("Nombre Pontón", value=st.session_state.hpt_data.get("ponton", ""))
        with col2:
            opciones_centros = list(CENTROS_AREAS.keys())
            idx_centro = opciones_centros.index(st.session_state.hpt_data.get("centro", opciones_centros[0])) if st.session_state.hpt_data.get("centro") in opciones_centros else 0
            centro = st.selectbox("Centro de Cultivo", opciones_centros, index=idx_centro)
            idx_ht = RANGO_TERMINO.index(st.session_state.hpt_data["hora_termino"]) if st.session_state.hpt_data["hora_termino"] in RANGO_TERMINO else 0
            hora_termino = st.selectbox("Hora de Término", RANGO_TERMINO, index=idx_ht)
            condicion_puerto = st.selectbox("Condición de Puerto", ["Abierto", "Cerrado para naves menores", "Cerrado total"])
            
        area_asignada = CENTROS_AREAS.get(centro, "Desconocida")
        correo_asignado = CENTROS_CORREOS.get(centro, "sin_correo@blumar.com")
        st.info(f"⚓ Área Asignada: **{area_asignada}** | 📬 Correo Destino: **{correo_asignado}**")
        correo = correo_asignado 
        
        st.markdown("🔒 **Asesores de Prevención y Operaciones**")
        col3, col4 = st.columns(2)
        with col3: st.text_input("Prevención 1", value=CORREOS_PREVENCION[0], disabled=True)
        with col4: st.text_input("Prevención 2", value=CORREOS_PREVENCION[1], disabled=True)
            
        # Reemplazo de campo texto por menú de faena
        opciones_faena = ["Inspeccion Red Lobera", "Inspeccion Red pecera", "Inspeccion Tensores", "Recuperacion inorganico", "Apoyo Centro de cultivo", "Extraccion de mortalidad", "Mantencion equipos"]
        idx_faena = opciones_faena.index(st.session_state.hpt_data.get("faena", opciones_faena[0])) if st.session_state.hpt_data.get("faena") in opciones_faena else 0
        faena = st.selectbox("Faena a realizar", opciones_faena, index=idx_faena)
        
        if st.button("SIGUIENTE ➡️", use_container_width=True):
            st.session_state.hpt_data.update({
                "empresa": empresa, "fecha": fecha, "hora_inicio": hora_inicio,
                "hora_termino": hora_termino, "centro": centro, "area": area_asignada, "correo": correo,
                "encargado": encargado, "ponton": ponton, "condicion_puerto": condicion_puerto, "faena": faena
            })
            set_step(2)
            st.rerun()

    elif st.session_state.hpt_step == 2:
        st.subheader("Checklist EPP")
        st.markdown("<p style='color: #00a8cc !important;'>⚠️ Los elementos con (*) son estrictamente obligatorios.</p>", unsafe_allow_html=True)
        estado_epp = st.session_state.hpt_data["epp"]
        col1, col2 = st.columns(2)
        with col1:
            epp_guantes = st.checkbox("Guantes", value=estado_epp[0])
            epp_chaleco = st.checkbox("Chaleco Salvavidas *", value=estado_epp[1])
            epp_zapatos = st.checkbox("Zapatos de seguridad / Botas", value=estado_epp[2])
            epp_termica = st.checkbox("Ropa Térmica *", value=estado_epp[3])
        with col2:
            epp_traje = st.checkbox("Traje de Agua", value=estado_epp[4])
            epp_comunicacion = st.checkbox("Medios de Comunicación *", value=estado_epp[5])
            epp_botiquin = st.checkbox("Botiquín *", value=estado_epp[6])
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⬅️ ATRÁS", key="back2", use_container_width=True):
                st.session_state.hpt_data["epp"] = [epp_guantes, epp_chaleco, epp_zapatos, epp_termica, epp_traje, epp_comunicacion, epp_botiquin]
                set_step(1)
                st.rerun()
        with col_btn2:
            if st.button("SIGUIENTE ➡️", key="next2", use_container_width=True):
                if not (epp_chaleco and epp_termica and epp_comunicacion and epp_botiquin):
                    st.error("⚠️ No cumple con EPP mínimos, revise su equipamiento y luego continúe.")
                else:
                    st.session_state.hpt_data["epp"] = [epp_guantes, epp_chaleco, epp_zapatos, epp_termica, epp_traje, epp_comunicacion, epp_botiquin]
                    set_step(3)
                    st.rerun()

    elif st.session_state.hpt_step == 3:
        st.subheader("Detalles de Faena y Checklist ERC")
        
        # Inserción de recuadro de detalles de faena (antes tarea en paso 1)
        tarea = st.text_area("Detalles de faena a realizar", value=st.session_state.hpt_data.get("tarea", ""))
        
        estado_erc = st.session_state.hpt_data["erc"]
        st.markdown("**Checklist ERC**")
        col1, col2 = st.columns(2)
        with col1:
            erc_izaje = st.checkbox("Izaje", value=estado_erc[0])
            erc_buceo = st.checkbox("Buceo", value=estado_erc[1])
            erc_electricos = st.checkbox("Intervención Equipos Eléctricos", value=estado_erc[2])
        with col2:
            erc_caidas = st.checkbox("Caídas al mismo/distinto nivel", value=estado_erc[3])
            erc_navegacion = st.checkbox("Navegación Diurna/Nocturna", value=estado_erc[4])
            erc_atrapamiento = st.checkbox("Atrapamiento", value=estado_erc[5])
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⬅️ ATRÁS", key="back3", use_container_width=True):
                st.session_state.hpt_data.update({"tarea": tarea, "erc": [erc_izaje, erc_buceo, erc_electricos, erc_caidas, erc_navegacion, erc_atrapamiento]})
                set_step(2)
                st.rerun()
        with col_btn2:
            if st.button("SIGUIENTE ➡️", key="next3", use_container_width=True):
                st.session_state.hpt_data.update({"tarea": tarea, "erc": [erc_izaje, erc_buceo, erc_electricos, erc_caidas, erc_navegacion, erc_atrapamiento]})
                set_step(4)
                st.rerun()

    elif st.session_state.hpt_step == 4:
        st.subheader("Validación Final")
        with st.expander("Toma de Conocimiento", expanded=True):
            tc_nombre = st.text_input("Nombre Difusión")
            col1, col2 = st.columns(2)
            with col1:
                tc_fecha = st.date_input("Fecha Difusión")
                tc_relator = st.text_input("Nombre Relator (Piloto)", value=st.session_state.current_user)
            with col2:
                tc_hora = st.selectbox("Hora Difusión", RANGO_HORA_DIFUSION)
                idx_dur = RANGO_DURACION.index(st.session_state.hpt_data["tc_duracion"]) if st.session_state.hpt_data["tc_duracion"] in RANGO_DURACION else 2
                tc_duracion = st.selectbox("Duración Difusión", RANGO_DURACION, index=idx_dur)
                
        with st.expander("Firmas de Responsabilidad", expanded=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.write("Firma Supervisor Servicio (Piloto)")
                firma_sup_serv = st_canvas(stroke_width=2, stroke_color="#000", background_color="#FFF", height=150, width=300, key="firma_serv")
            with col_f2:
                st.write("Firma Encargado de Centro")
                firma_encargado = st_canvas(stroke_width=2, stroke_color="#000", background_color="#FFF", height=150, width=300, key="firma_encargado")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⬅️ ATRÁS", key="back4", use_container_width=True):
                set_step(3)
                st.rerun()
        with col_btn2:
            if st.button("GENERAR Y ENVIAR HPT", type="primary", use_container_width=True):
                data = st.session_state.hpt_data
                barra_carga = st.progress(0, text="⚙️ Generando PDF...")
                
                try:
                    pdf = FPDF()
                    pdf.add_page()
                    if os.path.exists("logo.png"): pdf.image("logo.png", x=10, y=8, w=30)
                    pdf.set_y(35)
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 10, "HERRAMIENTA DE PREVENCION EN TERRENO (HPT) - ROV", border=1, ln=True, align="C")
                    pdf.ln(3)
                    
                    pdf.set_fill_color(200, 220, 255)
                    pdf.set_font("Arial", "B", 9)
                    pdf.cell(190, 6, "1. DATOS OPERATIVOS", border=1, ln=True, fill=True)
                    pdf.set_font("Arial", "B", 8)
                    pdf.cell(35, 6, "Empresa / Mandante:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('empresa', '')[:35], border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Centro de Cultivo:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('centro', '')[:35], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Fecha Maniobra:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, str(data.get('fecha', '')), border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Area Geografica:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('area', '')[:35], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Hora Inicio Rango:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, str(data.get('hora_inicio', '')), border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Hora Termino Rango:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, str(data.get('hora_termino', '')), border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Nombre Ponton:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('ponton', '')[:35], border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Condicion Puerto:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('condicion_puerto', '')[:35], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Encargado Centro:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, data.get('encargado', '')[:80], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Prevencionista 1:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, CORREOS_PREVENCION[0], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Prevencionista 2:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, CORREOS_PREVENCION[1], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Correo Centro:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, data.get('correo', '')[:80], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Faena Primaria:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, data.get('faena', '')[:80], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Detalles Especificos:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, data.get('tarea', '')[:80], border=1, ln=True)

                    pdf.ln(3)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "2. EQUIPO DE PROTECCION PERSONAL SELECCIONADO", border=1, ln=True, fill=True)
                    pdf.set_font("Arial", "", 8)
                    epp_labels = ["Guantes", "Chaleco", "Zapatos", "Ropa Termica", "Traje Agua", "Comunicacion", "Botiquin"]
                    epp_vals = data.get('epp', [])
                    epp_seleccionados = [epp_labels[i] for i in range(len(epp_labels)) if i < len(epp_vals) and epp_vals[i]]
                    
                    if not epp_seleccionados:
                        pdf.cell(190, 6, "Ningun EPP registrado.", border=1, ln=True)
                    else:
                        for i, epp in enumerate(epp_seleccionados):
                            pdf.cell(190/3, 6, f"[ X ] {epp}", border=1, ln=1 if (i + 1) % 3 == 0 or i == len(epp_seleccionados) - 1 else 0)

                    pdf.ln(3)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "3. RIESGOS CRITICOS EVALUADOS (ERC)", border=1, ln=True, fill=True)
                    pdf.set_font("Arial", "", 8)
                    erc_labels = ["Izaje", "Buceo", "Eq. Electricos", "Caidas", "Navegacion", "Atrapamiento"]
                    erc_vals = data.get('erc', [])
                    erc_seleccionados = [erc_labels[i] for i in range(len(erc_labels)) if i < len(erc_vals) and erc_vals[i]]
                    
                    if not erc_seleccionados:
                        pdf.cell(190, 6, "Ningun Riesgo seleccionado.", border=1, ln=True)
                    else:
                        for i, erc in enumerate(erc_seleccionados):
                            pdf.cell(190/2, 6, f"[ X ] {erc}", border=1, ln=1 if (i + 1) % 2 == 0 or i == len(erc_seleccionados) - 1 else 0)

                    pdf.ln(3)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "4. DIFUSION Y TOMA DE CONOCIMIENTO", border=1, ln=True, fill=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Relator / Piloto:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, tc_relator[:35], border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Cargo Relator:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, "Piloto ROV", border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Tema Difundido:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, tc_nombre[:80], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Fecha y Hora:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, f"{tc_fecha} {tc_hora}", border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Duracion Rango:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, tc_duracion, border=1, ln=True)

                    pdf.ln(3)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "5. CUADRO DE FIRMAS RESPONSABLES", border=1, ln=True, fill=True)
                    pdf.cell(95, 25, "", border=1); pdf.cell(95, 25, "", border=1, ln=True)
                    
                    if procesar_firma(firma_sup_serv, "f_serv.jpg"): pdf.image("f_serv.jpg", x=35, y=pdf.get_y()-24, w=45)
                    if procesar_firma(firma_encargado, "f_encargado.jpg"): pdf.image("f_encargado.jpg", x=130, y=pdf.get_y()-24, w=45)
                        
                    pdf.set_font("Arial", "B", 8)
                    pdf.cell(95, 6, "Firma Supervisor Servicio", border=1, align="C")
                    pdf.cell(95, 6, "Firma Encargado de Centro", border=1, ln=True, align="C")

                    archivo_pdf = f"HPT_{data.get('centro','').replace(' ', '_')}_{data.get('fecha')}.pdf"
                    pdf.output(archivo_pdf)

                    # SUBIDA DEL PDF A SUPABASE STORAGE Y OBTENCIÓN DE LINK
                    url_pdf_nube = ""
                    try:
                        with open(archivo_pdf, "rb") as f:
                            supabase.storage.from_("documentos").upload(path=archivo_pdf, file=f, file_options={"content-type": "application/pdf"})
                        url_pdf_nube = supabase.storage.from_("documentos").get_public_url(archivo_pdf)
                    except Exception as upload_error:
                        pass # Continúa si el bucket no está creado aún

                    row_data = {
                        "fecha": str(data.get('fecha')), "usuario": st.session_state.current_user,
                        "empresa": data.get('empresa'), "centro": data.get('centro'), "area": data.get('area'),
                        "ponton": data.get('ponton'), "condicion_puerto": data.get('condicion_puerto'),
                        "hora_inicio": data.get('hora_inicio'), "hora_termino": data.get('hora_termino'), 
                        "tarea": data.get('tarea'), "url_documento": url_pdf_nube
                    }
                    try:
                        supabase.table('hpt_history').insert(row_data).execute()
                    except Exception:
                        st.session_state.local_hpt_history.append(row_data)

                    barra_carga.progress(60, text="📧 Enviando PDF...")
                    
                    remitente = st.secrets["EMAIL_USER"]
                    password = st.secrets["EMAIL_PASS"]
                    correo_centro = data.get('correo', remitente)
                    lista_destinatarios = [correo_centro, CORREOS_PREVENCION[0], CORREOS_PREVENCION[1]]
                    
                    msg = MIMEMultipart(); msg['From'] = remitente; msg['To'] = ", ".join(lista_destinatarios); msg['Subject'] = f"Reporte HPT - {data.get('centro')}"
                    msg.attach(MIMEText("Se adjunta el reporte HPT.", 'plain'))
                    with open(archivo_pdf, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream"); part.set_payload(attachment.read())
                    encoders.encode_base64(part); part.add_header("Content-Disposition", f"attachment; filename={archivo_pdf}"); msg.attach(part)
                    
                    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(remitente, password)
                    server.sendmail(remitente, lista_destinatarios, msg.as_string()); server.quit()

                    barra_carga.progress(100, text="✅ ¡LISTO!")
                    time.sleep(0.5); barra_carga.empty()
                    st.success(f"HPT Guardada en la nube y Transmitida con éxito.")
                    with open(archivo_pdf, "rb") as pdf_file: st.download_button(label="📥 Descargar Copia Local PDF", data=pdf_file, file_name=archivo_pdf, mime="application/pdf")
                except Exception as e:
                    barra_carga.empty(); st.error(f"Falla: {e}")

# ---------------------------------------------------------
# MÓDULO 5: REPORTE DIARIO OPERATIVO
# ---------------------------------------------------------
elif st.session_state.current_page == 'reporte_diario':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("Reporte Diario Operativo")
    st.divider()

    st.subheader("Datos Operacionales de Faena")
    
    # SECTOR REACTIVO: Selector fuera del formulario para actualizar de inmediato
    opciones_centros = list(CENTROS_AREAS.keys())
    centro_rd = st.selectbox("Centro de Cultivo", opciones_centros)
    
    area_rd = CENTROS_AREAS.get(centro_rd, "Desconocida")
    correo_asignado_rd = CENTROS_CORREOS.get(centro_rd, "sin_correo@blumar.com")
    st.info(f"⚓ Área Asignada: **{area_rd}** | 📬 Correo Central: **{correo_asignado_rd}**")

    # Contenedor del Formulario
    with st.form("form_reporte_diario"):
        col1, col2 = st.columns(2)
        with col1:
            fecha_rd = st.date_input("Fecha", value=datetime.date.today())
            piloto_rd = st.text_input("Nombre de Piloto", value=st.session_state.current_user)
            jaula_rd = st.text_input("Jaula / Balsa Trabajada")
            ponton_rd = st.text_input("Nombre Pontón")
        with col2:
            hora_inicio_rd = st.selectbox("Hora Inicio Rango", RANGO_INICIO)
            hora_termino_rd = st.selectbox("Hora Término Rango", RANGO_TERMINO)
            condicion_puerto_rd = st.selectbox("Condición de Puerto", ["Abierto", "Cerrado para naves menores", "Cerrado total"])
            correo_adicional_rd = st.text_input("Correos Adicionales (Separados por coma)", value="reportesrovincinel@gmail.com")
            
        tarea_rd = st.text_area("Descripción de la Tarea Realizada")
        submit_rd = st.form_submit_button("GENERAR Y ENVIAR REPORTE DIARIO", type="primary", use_container_width=True)

        if submit_rd:
            barra_rd = st.progress(0, text="⚙️ Generando PDF...")
            try:
                pdf_rd = FPDF(); pdf_rd.add_page()
                if os.path.exists("logo.png"): pdf_rd.image("logo.png", x=10, y=8, w=30)
                pdf_rd.set_y(35); pdf_rd.set_font("Arial", "B", 14); pdf_rd.cell(0, 10, "REPORTE DIARIO DE OPERACIONES - ROV", border=1, ln=True, align="C"); pdf_rd.ln(5)
                
                pdf_rd.set_fill_color(200, 220, 255); pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(190, 6, "1. DATOS GENERALES", border=1, ln=True, fill=True)
                pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(30, 6, "Fecha:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(65, 6, str(fecha_rd), border=1)
                pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(30, 6, "Rango Horario:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(65, 6, f"{hora_inicio_rd} - {hora_termino_rd}", border=1, ln=True)
                pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(30, 6, "Piloto ROV:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(60, 6, piloto_rd, border=1)
                pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(35, 6, "Nombre Ponton:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(60, 6, ponton_rd, border=1, ln=True)
                pdf_rd.set_font("Arial", "B", 8); pdf.cell(30, 6, "Centro Cultivo:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, centro_rd, border=1)
                pdf_rd.set_font("Arial", "B", 8); pdf.cell(35, 6, "Area Asignada:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, area_rd, border=1, ln=True)
                pdf_rd.set_font("Arial", "B", 8); pdf.cell(35, 6, "Condicion Puerto:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, condicion_puerto_rd, border=1, ln=True)

                pdf_rd.ln(5); pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(190, 6, "2. DETALLE OPERATIVO", border=1, ln=True, fill=True)
                pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(40, 6, "Estructura Intervenida:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(150, 6, jaula_rd, border=1, ln=True)
                pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(190, 6, "Descripcion de la Tarea Realizada:", border=1, ln=True); pdf_rd.set_font("Arial", "", 8)
                pdf_rd.multi_cell(190, 5, tarea_rd[:1000])
                
                archivo_pdf_rd = f"Reporte_Diario_{centro_rd.replace(' ', '_')}_{fecha_rd}.pdf"
                pdf_rd.output(archivo_pdf_rd)

                url_pdf_rd_nube = ""
                try:
                    with open(archivo_pdf_rd, "rb") as f:
                        supabase.storage.from_("documentos").upload(path=archivo_pdf_rd, file=f, file_options={"content-type": "application/pdf"})
                    url_pdf_rd_nube = supabase.storage.from_("documentos").get_public_url(archivo_pdf_rd)
                except Exception as upload_error:
                    pass

                datos_rd = {
                    "fecha": str(fecha_rd), "usuario": piloto_rd, "centro": centro_rd, "area": area_rd,
                    "jaula": jaula_rd, "ponton": ponton_rd, "hora_inicio": str(hora_inicio_rd), "hora_termino": str(hora_termino_rd),
                    "condicion_puerto": condicion_puerto_rd, "tarea": tarea_rd, "url_documento": url_pdf_rd_nube
                }
                try:
                    supabase.table('reportes_history').insert(datos_rd).execute()
                except:
                    st.session_state.local_reportes_history.append(datos_rd)

                barra_rd.progress(60, text="📧 Enviando PDF...")
                
                remitente = st.secrets["EMAIL_USER"]
                password = st.secrets["EMAIL_PASS"]
                lista_destinatarios_rd = [correo_asignado_rd]
                if correo_adicional_rd.strip():
                    lista_destinatarios_rd.extend([e.strip() for e in correo_adicional_rd.split(',') if e.strip()])
                
                msg = MIMEMultipart(); msg['From'] = remitente; msg['To'] = ", ".join(lista_destinatarios_rd); msg['Subject'] = f"Reporte Diario ROV - {centro_rd}"
                msg.attach(MIMEText("Se adjunta el Reporte Diario.", 'plain'))
                with open(archivo_pdf_rd, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream"); part.set_payload(attachment.read())
                encoders.encode_base64(part); part.add_header("Content-Disposition", f"attachment; filename={archivo_pdf_rd}"); msg.attach(part)
                
                server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(remitente, password); server.send_message(msg); server.quit()

                barra_rd.progress(100, text="✅ ¡LISTO!")
                time.sleep(0.5)
                barra_rd.empty()
                st.success(f"Reporte Diario enviado a: {', '.join(lista_destinatarios_rd)}")
            except Exception as e:
                barra_rd.empty()
                st.error(f"Error técnico: {e}")

# ---------------------------------------------------------
# MÓDULO 6: HISTORIAL Y BÚSQUEDA (ADMINISTRADOR / USUARIO)
# ---------------------------------------------------------
elif st.session_state.current_page == 'modulo_busqueda':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("Historial de Documentación y Descargas")
    st.divider()
    
    rol_busqueda = st.radio("Seleccione Perfil de Búsqueda", ["Usuario Común", "Administrador"])
    
    registros_hpt = []
    
    if rol_busqueda == "Administrador":
        if not st.session_state.admin_acceso_historial:
            clave_ingresada = st.text_input("Ingrese Pin de Seguridad Administrador", type="password")
            if st.button("Ingresar"):
                if clave_ingresada == CLAVE_ADMIN:
                    st.session_state.admin_acceso_historial = True
                    st.rerun()
                else:
                    st.error("Código de seguridad incorrecto.")
        else:
            st.success("Acceso Gerencial Desbloqueado.")
            if st.button("Cerrar Vista Administrador"):
                st.session_state.admin_acceso_historial = False
                st.rerun()
                
            try:
                res = supabase.table('hpt_history').select('*').order('id', desc=True).execute()
                registros_hpt = res.data
            except:
                registros_hpt = st.session_state.local_hpt_history
    else:
        user_actual = st.session_state.current_user
        st.info(f"Mostrando únicamente registros del Piloto: **{user_actual}**")
        try:
            res = supabase.table('hpt_history').select('*').filter('usuario', 'eq', user_actual).order('id', desc=True).execute()
            registros_hpt = res.data
        except:
            registros_hpt = [r for r in st.session_state.local_hpt_history if r['usuario'] == user_actual]

    if (rol_busqueda == "Usuario Común") or (rol_busqueda == "Administrador" and st.session_state.admin_acceso_historial):
        if registros_hpt:
            df = pd.DataFrame(registros_hpt)
            
            # Limpieza de url_documento para evitar fallas visuales con string "none" o cadenas vacias
            if 'url_documento' in df.columns:
                df['url_documento'] = df['url_documento'].apply(lambda x: x if pd.notnull(x) and str(x).strip() != "" else None)
                
                st.dataframe(
                    df[['fecha', 'usuario', 'centro', 'area', 'ponton', 'condicion_puerto', 'url_documento']],
                    column_config={
                        "url_documento": st.column_config.LinkColumn("Enlace PDF", display_text="📥 Descargar PDF")
                    },
                    use_container_width=True
                )
            else:
                st.dataframe(df[['fecha', 'usuario', 'centro', 'area', 'ponton', 'condicion_puerto']], use_container_width=True)
        else:
            st.info("No se registran datos en el historial solicitado.")

# ---------------------------------------------------------
# MÓDULO 7: PANEL DE GRÁFICOS GERENCIALES (BI)
# ---------------------------------------------------------
elif st.session_state.current_page == 'panel_graficos':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("📈 Métricas e Inteligencia de Negocio")
    st.divider()
    
    if not st.session_state.admin_acceso_graficos:
        clave_dash = st.text_input("Autenticación Gerencial (Pin)", type="password", key="dash_pin")
        if st.button("Ingresar"):
            if clave_dash == CLAVE_ADMIN:
                st.session_state.admin_acceso_graficos = True
                st.rerun()
            else:
                st.error("Código inválido.")
    else:
        st.success("Acceso Gerencial Desbloqueado.")
        if st.button("Cerrar Vista Administrador"):
            st.session_state.admin_acceso_graficos = False
            st.rerun()

        try:
            res_hpt = supabase.table('hpt_history').select('*').execute()
            df_hpt = pd.DataFrame(res_hpt.data)
        except:
            df_hpt = pd.DataFrame(st.session_state.local_hpt_history)
            
        if not df_hpt.empty:
            st.subheader("📊 Frecuencia de Operaciones por Centro de Cultivo")
            centro_counts = df_hpt['centro'].value_counts()
            st.bar_chart(centro_counts)
            
            st.subheader("🚢 Estado y Restricciones de Puertos por Área")
            puerto_counts = df_hpt.groupby(['area', 'condicion_puerto']).size().unstack(fill_value=0)
            st.bar_chart(puerto_counts)
            
            st.subheader("💼 Distribución Operativa por Piloto ROV")
            piloto_counts = df_hpt['usuario'].value_counts()
            st.bar_chart(piloto_counts)
        else:
            st.info("No existen suficientes registros en Supabase para estructurar gráficos de control estadístico.")
