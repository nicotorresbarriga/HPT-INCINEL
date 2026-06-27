import streamlit as st
import pandas as pd
import datetime
import os
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

# 2. Inyección CSS (Estilo Marino Moderno)
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #001f3f 0%, #003366 50%, #00509e 100%);
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
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #007a99;
        box-shadow: 0 6px 8px rgba(0,0,0,0.4);
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        border-radius: 6px;
        border: 1px solid #cbd5e0;
        color: #1a202c !important;
        background-color: #f8fafc !important;
    }
    /* Excepción para checkbox labels si no toman el color */
    div[data-testid="stCheckbox"] label span {
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Conexión a Supabase y Carga de Datos
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

USUARIOS = {}
CENTROS_AREAS = {}

# Diccionario de correos automáticos por centro
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

try:
    supabase = init_connection()
    res_usuarios = supabase.table('usuarios').select('*').execute()
    USUARIOS = {row['usuario']: row['contrasena'] for row in res_usuarios.data}
    
    res_centros = supabase.table('centros').select('*').execute()
    CENTROS_AREAS = {row['nombre']: row['area'] for row in res_centros.data}
except Exception as e:
    USUARIOS = {
        "Ntorres": "17909926",
        "Imuñoz": "12345678",
        "Pasencio": "98765432"
    }
    CENTROS_AREAS = {
        "Centro Ninualac": "Area Sur", "Centro Dring 3": "Area Sur", "Centro Punta cola": "Area Sur",
        "Centro Midhurst": "Area Norte", "Centro Bobe": "Area Norte", "Centro Ceres": "Area Norte",
        "Centro Cordoba 1": "Area Austral", "Centro Cordoba 2": "Area Austral", "Centro Perez de Arce": "Area Austral"
    }
    st.sidebar.warning("Advertencia: Operando con base de datos de contingencia (Local).")

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
        "empresa": "Salmones Blumar", "fecha": datetime.date.today(), "hora_inicio": datetime.datetime.now().time(),
        "hora_termino": datetime.datetime.now().time(), "centro": list(CENTROS_AREAS.keys())[0] if CENTROS_AREAS else "",
        "correo": "", "encargado": "", "apr1": "", "apr2": "", "tarea": "",
        "epp": [False]*7, "faena": "Inspeccion Red pecera", "erc": [False]*6
    }

def set_page(page_name):
    st.session_state.current_page = page_name

def set_step(step_number):
    st.session_state.hpt_step = step_number

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
                    st.error("Credenciales inválidas o usuario no registrado.")

# ---------------------------------------------------------
# MÓDULO 2: MENÚ PRINCIPAL
# ---------------------------------------------------------
elif st.session_state.current_page == 'main_menu':
    st.title("Sistema de Gestión Operativa")
    st.write(f"Operador en turno: **{st.session_state.current_user}**")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⚓ HPT", use_container_width=True):
            set_page('hpt_menu')
            st.rerun()
    with col2:
        if st.button("🤿 REPORTE DIARIO", use_container_width=True):
            set_page('reporte_diario')
            st.rerun()
    with col3:
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
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚢 NUEVO", use_container_width=True):
            set_step(1)
            set_page('hpt_nuevo')
            st.rerun()
    with col2:
        st.button("🔭 BÚSQUEDA", use_container_width=True)
    with col3:
        st.button("⬇️ EXPORTAR", use_container_width=True)

# ---------------------------------------------------------
# MÓDULO 4: FLUJO DE CREACIÓN HPT (WIZARD)
# ---------------------------------------------------------
elif st.session_state.current_page == 'hpt_nuevo':
    st.button("⬅️ Cancelar y Volver al Menú HPT", on_click=set_page, args=('hpt_menu',))
    st.title("Nueva HPT - Paso " + str(st.session_state.hpt_step))
    st.progress(st.session_state.hpt_step / 4.0)
    
    # --- PASO 1: DATOS GENERALES ---
    if st.session_state.hpt_step == 1:
        st.subheader("Datos Operativos")
        
        opciones_empresa = ["Salmones Blumar", "Salmones Blumar Magallanes"]
        idx_empresa = opciones_empresa.index(st.session_state.hpt_data.get("empresa", opciones_empresa[0])) if st.session_state.hpt_data.get("empresa") in opciones_empresa else 0
        empresa = st.selectbox("Empresa", opciones_empresa, index=idx_empresa)
        
        # Agrupación 1: Fechas y Horas alineadas
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", value=st.session_state.hpt_data.get("fecha", datetime.date.today()))
            hora_inicio = st.time_input("Hora de Inicio", value=st.session_state.hpt_data.get("hora_inicio", datetime.datetime.now().time()))
            
        with col2:
            opciones_centros = list(CENTROS_AREAS.keys())
            idx_centro = opciones_centros.index(st.session_state.hpt_data.get("centro", opciones_centros[0])) if st.session_state.hpt_data.get("centro") in opciones_centros else 0
            centro = st.selectbox("Centro de Cultivo", opciones_centros, index=idx_centro)
            hora_termino = st.time_input("Hora de Término", value=st.session_state.hpt_data.get("hora_termino", datetime.datetime.now().time()))
            
        # Variables Autocompletadas
        area_asignada = CENTROS_AREAS.get(centro, "Desconocida")
        correo_asignado = CENTROS_CORREOS.get(centro, "sin_correo@blumar.com")
        st.info(f"🌊 Área Asignada: **{area_asignada}** | 📬 Correo Automático: **{correo_asignado}**")
        correo = correo_asignado 
        
        # Agrupación 2: Personal y Prevención Alineados
        st.markdown("⚓ **Personal y Prevención**")
        col3, col4 = st.columns(2)
        with col3:
            encargado = st.text_input("Encargado del Centro", value=st.session_state.hpt_data.get("encargado", ""))
            apr1 = st.text_input("Asesor Prev. 1 (Nombre y Correo)", value=st.session_state.hpt_data.get("apr1", "Prevencionista 1 - prev1@incinel.cl"))
        with col4:
            tarea = st.text_input("Tarea a Realizar", value=st.session_state.hpt_data.get("tarea", ""))
            apr2 = st.text_input("Asesor Prev. 2 (Nombre y Correo)", value=st.session_state.hpt_data.get("apr2", "Prevencionista 2 - prev2@incinel.cl"))
            
        if st.button("SIGUIENTE ➡️", use_container_width=True):
            st.session_state.hpt_data.update({
                "empresa": empresa, "fecha": fecha, "hora_inicio": hora_inicio,
                "hora_termino": hora_termino, "centro": centro, "area": area_asignada, "correo": correo,
                "encargado": encargado, "apr1": apr1, "apr2": apr2, "tarea": tarea
            })
            set_step(2)
            st.rerun()

    # --- PASO 2: EPP CHECKLIST ---
    elif st.session_state.hpt_step == 2:
        st.subheader("Checklist EPP")
        estado_epp = st.session_state.hpt_data["epp"]
        
        col1, col2 = st.columns(2)
        with col1:
            epp_guantes = st.checkbox("Guantes", value=estado_epp[0])
            epp_chaleco = st.checkbox("Chaleco Salvavidas", value=estado_epp[1])
            epp_zapatos = st.checkbox("Zapatos de seguridad / Botas", value=estado_epp[2])
            epp_termica = st.checkbox("Ropa Térmica", value=estado_epp[3])
        with col2:
            epp_traje = st.checkbox("Traje de Agua", value=estado_epp[4])
            epp_comunicacion = st.checkbox("Medios de Comunicación", value=estado_epp[5])
            epp_botiquin = st.checkbox("Botiquín", value=estado_epp[6])
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⬅️ ATRÁS", key="back2", use_container_width=True):
                st.session_state.hpt_data["epp"] = [epp_guantes, epp_chaleco, epp_zapatos, epp_termica, epp_traje, epp_comunicacion, epp_botiquin]
                set_step(1)
                st.rerun()
        with col_btn2:
            if st.button("SIGUIENTE ➡️", key="next2", use_container_width=True):
                st.session_state.hpt_data["epp"] = [epp_guantes, epp_chaleco, epp_zapatos, epp_termica, epp_traje, epp_comunicacion, epp_botiquin]
                set_step(3)
                st.rerun()

    # --- PASO 3: ERC CHECKLIST Y FAENA ---
    elif st.session_state.hpt_step == 3:
        st.subheader("Faena a Realizar y Checklist ERC")
        
        opciones_faena = [
            "Inspeccion Red Lobera", "Inspeccion Red pecera", "Inspeccion Tensores", 
            "Recuperacion inorganico", "Apoyo Centro de cultivo", 
            "Extraccion de mortalidad", "Mantencion equipos"
        ]
        idx_faena = opciones_faena.index(st.session_state.hpt_data["faena"]) if st.session_state.hpt_data["faena"] in opciones_faena else 0
        faena = st.selectbox("Faena a realizar", opciones_faena, index=idx_faena)
        
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
                st.session_state.hpt_data.update({
                    "faena": faena,
                    "erc": [erc_izaje, erc_buceo, erc_electricos, erc_caidas, erc_navegacion, erc_atrapamiento]
                })
                set_step(2)
                st.rerun()
        with col_btn2:
            if st.button("SIGUIENTE ➡️", key="next3", use_container_width=True):
                st.session_state.hpt_data.update({
                    "faena": faena,
                    "erc": [erc_izaje, erc_buceo, erc_electricos, erc_caidas, erc_navegacion, erc_atrapamiento]
                })
                set_step(4)
                st.rerun()

    # --- PASO 4: TOMA DE CONOCIMIENTO Y FIRMAS ---
    elif st.session_state.hpt_step == 4:
        st.subheader("Validación Final")
        
        with st.expander("Toma de Conocimiento", expanded=True):
            tc_nombre = st.text_input("Nombre Difusión")
            col1, col2 = st.columns(2)
            with col1:
                tc_fecha = st.date_input("Fecha Difusión")
                tc_relator = st.text_input("Nombre Relator")
            with col2:
                tc_hora = st.time_input("Hora Difusión")
                tc_duracion = st.text_input("Duración Difusión")
                tc_cargo = st.text_input("Cargo Relator")
            
            st.write("Firma Relator (o Piloto)")
            firma_relator = st_canvas(stroke_width=2, stroke_color="#000", background_color="#FFF", height=150, width=300, key="firma_relator")

        with st.expander("Firmas", expanded=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                sup_servicio = st.text_input("Nombre Supervisor del Servicio (Piloto)")
                st.write("Firma Supervisor Servicio")
                firma_sup_serv = st_canvas(stroke_width=2, stroke_color="#000", background_color="#FFF", height=150, width=300, key="firma_serv")
            with col_f2:
                empresa_sel = st.session_state.hpt_data.get('empresa', 'Salmonera')
                sup_salmonera = st.text_input(f"Nombre Supervisor {empresa_sel}")
                st.write(f"Firma Supervisor {empresa_sel}")
                firma_sup_sal = st_canvas(stroke_width=2, stroke_color="#000", background_color="#FFF", height=150, width=300, key="firma_sal")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⬅️ ATRÁS", key="back4", use_container_width=True):
                set_step(3)
                st.rerun()
        with col_btn2:
            if st.button("GENERAR Y ENVIAR HPT", type="primary", use_container_width=True):
                data = st.session_state.hpt_data
                
                with st.spinner("Compilando arquitectura PDF tabular y transmitiendo..."):
                    try:
                        pdf = FPDF()
                        pdf.add_page()
                        
                        if os.path.exists("logo.png"):
                            pdf.image("logo.png", x=10, y=8, w=30)
                        
                        pdf.set_font("Arial", "B", 12)
                        pdf.cell(0, 10, "HERRAMIENTA DE PREVENCION EN TERRENO (HPT) - ROV", border=1, ln=True, align="C")
                        pdf.ln(3)
                        
                        # --- TABLA 1: DATOS OPERATIVOS ---
                        pdf.set_fill_color(200, 220, 255)
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(190, 6, "1. DATOS OPERATIVOS", border=1, ln=True, fill=True)
                        
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Empresa:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, data.get('empresa', '')[:35], border=1)
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Centro:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, data.get('centro', '')[:35], border=1, ln=True)
                        
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Fecha:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, str(data.get('fecha', '')), border=1)
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Area:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, data.get('area', '')[:35], border=1, ln=True)

                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Hora Inicio:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, str(data.get('hora_inicio', '')), border=1)
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Hora Termino:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, str(data.get('hora_termino', '')), border=1, ln=True)

                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Encargado:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(160, 6, data.get('encargado', '')[:80], border=1, ln=True)
                        
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Prevencion 1:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(160, 6, data.get('apr1', '')[:80], border=1, ln=True)

                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Prevencion 2:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(160, 6, data.get('apr2', '')[:80], border=1, ln=True)
                        
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Faena:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(160, 6, data.get('faena', '')[:80], border=1, ln=True)
                        
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Tarea:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(160, 6, data.get('tarea', '')[:80], border=1, ln=True)

                        pdf.ln(3)
                        
                        # --- TABLA 2: EPP ---
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(190, 6, "2. EQUIPO DE PROTECCION PERSONAL (EPP)", border=1, ln=True, fill=True)
                        pdf.set_font("Arial", "", 8)
                        epp_labels = ["Guantes", "Chaleco", "Zapatos/Botas", "Ropa Termica", "Traje Agua", "Comunicacion", "Botiquin"]
                        epp_vals = data.get('epp', [])
                        
                        col_w = 190 / 3
                        for i in range(len(epp_labels)):
                            check = "[ X ]" if i < len(epp_vals) and epp_vals[i] else "[   ]"
                            text = f"{check} {epp_labels[i]}"
                            ln_val = 1 if (i + 1) % 3 == 0 or i == len(epp_labels) - 1 else 0
                            pdf.cell(col_w, 6, text, border=1, ln=ln_val)

                        pdf.ln(3)

                        # --- TABLA 3: ERC ---
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(190, 6, "3. EVALUACION DE RIESGOS CRITICOS (ERC)", border=1, ln=True, fill=True)
                        pdf.set_font("Arial", "", 8)
                        erc_labels = ["Izaje", "Buceo", "Eq. Electricos", "Caidas", "Nav. Diurna/Nocturna", "Atrapamiento"]
                        erc_vals = data.get('erc', [])
                        
                        col_w = 190 / 2
                        for i in range(len(erc_labels)):
                            check = "[ X ]" if i < len(erc_vals) and erc_vals[i] else "[   ]"
                            text = f"{check} {erc_labels[i]}"
                            ln_val = 1 if (i + 1) % 2 == 0 or i == len(erc_labels) - 1 else 0
                            pdf.cell(col_w, 6, text, border=1, ln=ln_val)

                        pdf.ln(3)
                        
                        # --- TABLA 4: TOMA DE CONOCIMIENTO ---
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(190, 6, "4. TOMA DE CONOCIMIENTO Y DIFUSION", border=1, ln=True, fill=True)
                        
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Relator:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, tc_relator[:35], border=1)
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Cargo:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, tc_cargo[:35], border=1, ln=True)

                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Tema/Difusion:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(160, 6, tc_nombre[:80], border=1, ln=True)

                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Fecha/Hora:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, f"{tc_fecha} {tc_hora}", border=1)
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(30, 6, "Duracion:", border=1)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(65, 6, tc_duracion[:35], border=1, ln=True)

                        pdf.ln(3)

                        # --- TABLA 5: FIRMAS ---
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(190, 6, "5. FIRMAS DE RESPONSABILIDAD", border=1, ln=True, fill=True)
                        
                        y_firmas = pdf.get_y() + 2
                        ancho_firma = 38
                        
                        pdf.cell(63.3, 25, "", border=1)
                        pdf.cell(63.3, 25, "", border=1)
                        pdf.cell(63.3, 25, "", border=1, ln=True)

                        def procesar_firma(canvas_obj, filename):
                            if canvas_obj.image_data is not None:
                                img_data = canvas_obj.image_data
                                firma_img = Image.fromarray((img_data).astype('uint8'), mode='RGBA')
                                fondo_blanco = Image.new("RGB", firma_img.size, (255, 255, 255))
                                fondo_blanco.paste(firma_img, mask=firma_img.split()[3])
                                fondo_blanco.save(filename)
                                return True
                            return False
                        
                        if procesar_firma(firma_relator, "f_relator.jpg"):
                            pdf.image("f_relator.jpg", x=20, y=y_firmas, w=ancho_firma)
                        if procesar_firma(firma_sup_serv, "f_serv.jpg"):
                            pdf.image("f_serv.jpg", x=83, y=y_firmas, w=ancho_firma)
                        if procesar_firma(firma_sup_sal, "f_sal.jpg"):
                            pdf.image("f_sal.jpg", x=146, y=y_firmas, w=ancho_firma)
                            
                        pdf.set_font("Arial", "B", 7)
                        empresa_nombre = data.get('empresa', '')
                        if len(empresa_nombre) > 22: 
                            empresa_nombre = empresa_nombre[:20] + "..."
                            
                        pdf.cell(63.3, 6, "Firma Relator", border=1, align="C")
                        pdf.cell(63.3, 6, "Firma Sup. Servicio", border=1, align="C")
                        pdf.cell(63.3, 6, f"Firma {empresa_nombre}", border=1, ln=True, align="C")

                        archivo_pdf = f"HPT_{data.get('centro','').replace(' ', '_')}_{data.get('fecha')}.pdf"
                        pdf.output(archivo_pdf)

                        # Rutina SMTP HPT
                        remitente = st.secrets["EMAIL_USER"]
                        password = st.secrets["EMAIL_PASS"]
                        
                        correo_prevencion_1 = "prevencion1@incinel.cl"
                        correo_prevencion_2 = "prevencion2@incinel.cl"
                        
                        correo_centro = data.get('correo', remitente)
                        lista_destinatarios = [correo_centro, correo_prevencion_1, correo_prevencion_2]
                        
                        msg = MIMEMultipart()
                        msg['From'] = remitente
                        msg['To'] = ", ".join(lista_destinatarios)
                        msg['Subject'] = f"Reporte HPT - {data.get('centro')} - {data.get('fecha')}"
                        msg.attach(MIMEText("Se adjunta el reporte de Prevención de Riesgos (HPT) generado desde la plataforma TechTrident.", 'plain'))

                        with open(archivo_pdf, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename={archivo_pdf}")
                        msg.attach(part)

                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(remitente, password)
                        server.sendmail(remitente, lista_destinatarios, msg.as_string())
                        server.quit()

                        st.success(f"HPT Compilada y Transmitida con éxito a: {', '.join(lista_destinatarios)}")
                        
                        with open(archivo_pdf, "rb") as pdf_file:
                            st.download_button(label="📥 Descargar PDF", data=pdf_file, file_name=archivo_pdf, mime="application/pdf")
                            
                    except Exception as e:
                        st.error(f"Falla de ejecución técnica: {e}")

# ---------------------------------------------------------
# MÓDULO 5: REPORTE DIARIO (NUEVO Y AISLADO)
# ---------------------------------------------------------
elif st.session_state.current_page == 'reporte_diario':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("Reporte Diario Operativo")
    st.divider()

    with st.form("form_reporte_diario"):
        st.subheader("Datos Operacionales")
        
        col1, col2 = st.columns(2)
        with col1:
            fecha_rd = st.date_input("Fecha", value=datetime.date.today())
            piloto_rd = st.text_input("Nombre de Piloto", value=st.session_state.current_user)
            
            opciones_centros = list(CENTROS_AREAS.keys())
            centro_rd = st.selectbox("Centro de Cultivo", opciones_centros)
            jaula_rd = st.text_input("Jaula / Balsa Trabajada (Ej: Balsa 104)")
            
        with col2:
            hora_rd = st.time_input("Hora de Emisión", value=datetime.datetime.now().time())
            
            area_rd = CENTROS_AREAS.get(centro_rd, "Desconocida")
            correo_asignado_rd = CENTROS_CORREOS.get(centro_rd, "sin_correo@blumar.com")
            
            st.info(f"🌊 Área Asignada: **{area_rd}** | 📬 Correo Automático: **{correo_asignado_rd}**")
            
            condicion_puerto = st.selectbox("Condición de Puerto", ["Abierto", "Cerrado para naves menores", "Cerrado total"])
            
            correo_principal_rd = st.text_input("Correo del Centro (Bloqueado)", value=correo_asignado_rd, disabled=True)
            correo_adicional_rd = st.text_input("Correos Adicionales (Opcional - Separados por coma)")
            
        tarea_rd = st.text_area("Descripción de la Tarea Realizada")
        
        submit_rd = st.form_submit_button("GENERAR Y ENVIAR REPORTE DIARIO", type="primary", use_container_width=True)

        if submit_rd:
            with st.spinner("Procesando Reporte Diario..."):
                try:
                    pdf_rd = FPDF()
                    pdf_rd.add_page()
                    
                    if os.path.exists("logo.png"):
                        pdf_rd.image("logo.png", x=10, y=8, w=30)
                    
                    pdf_rd.set_font("Arial", "B", 14)
                    pdf_rd.cell(0, 10, "REPORTE DIARIO DE OPERACIONES - ROV", border=1, ln=True, align="C")
                    pdf_rd.ln(5)
                    
                    pdf_rd.set_fill_color(200, 220, 255)
                    pdf_rd.set_font("Arial", "B", 9)
                    pdf_rd.cell(190, 6, "1. DATOS GENERALES", border=1, ln=True, fill=True)
                    
                    pdf_rd.set_font("Arial", "B", 8)
                    pdf_rd.cell(30, 6, "Fecha:", border=1)
                    pdf_rd.set_font("Arial", "", 8)
                    pdf_rd.cell(65, 6, str(fecha_rd), border=1)
                    pdf_rd.set_font("Arial", "B", 8)
                    pdf_rd.cell(30, 6, "Hora:", border=1)
                    pdf_rd.set_font("Arial", "", 8)
                    pdf_rd.cell(65, 6, str(hora_rd), border=1, ln=True)

                    pdf_rd.set_font("Arial", "B", 8)
                    pdf_rd.cell(30, 6, "Piloto ROV:", border=1)
                    pdf_rd.set_font("Arial", "", 8)
                    pdf_rd.cell(160, 6, piloto_rd[:80], border=1, ln=True)
                    
                    pdf_rd.set_font("Arial", "B", 8)
                    pdf_rd.cell(30, 6, "Centro:", border=1)
                    pdf_rd.set_font("Arial", "", 8)
                    pdf_rd.cell(65, 6, centro_rd[:35], border=1)
                    pdf_rd.set_font("Arial", "B", 8)
                    pdf_rd.cell(30, 6, "Area:", border=1)
                    pdf_rd.set_font("Arial", "", 8)
                    pdf_rd.cell(65, 6, area_rd[:35], border=1, ln=True)

                    pdf_rd.set_font("Arial", "B", 8)
                    pdf_rd.cell(40, 6, "Condicion Puerto:", border=1)
                    pdf_rd.set_font("Arial", "", 8)
                    pdf_rd.cell(150, 6, condicion_puerto[:70], border=1, ln=True)

                    pdf_rd.ln(5)
                    
                    pdf_rd.set_font("Arial", "B", 9)
                    pdf_rd.cell(190, 6, "2. DETALLE OPERATIVO", border=1, ln=True, fill=True)
                    
                    pdf_rd.set_font("Arial", "B", 8)
                    pdf_rd.cell(40, 6, "Estructura Intervenida:", border=1)
                    pdf_rd.set_font("Arial", "", 8)
                    pdf_rd.cell(150, 6, jaula_rd[:80], border=1, ln=True)

                    pdf_rd.set_font("Arial", "B", 8)
                    pdf_rd.cell(190, 6, "Descripcion de la Tarea:", border=1, ln=True)
                    pdf_rd.set_font("Arial", "", 8)
                    
                    x = pdf_rd.get_x()
                    y = pdf_rd.get_y()
                    pdf_rd.multi_cell(190, 5, tarea_rd[:1000]) # Límite preventivo de caracteres
                    pdf_rd.rect(x, y, 190, pdf_rd.get_y() - y)
                    
                    archivo_pdf_rd = f"Reporte_Diario_{centro_rd.replace(' ', '_')}_{fecha_rd}.pdf"
                    pdf_rd.output(archivo_pdf_rd)

                    remitente = st.secrets["EMAIL_USER"]
                    password = st.secrets["EMAIL_PASS"]
                    
                    lista_destinatarios_rd = [correo_principal_rd]
                    if correo_adicional_rd.strip():
                        correos_limpios = [email.strip() for email in correo_adicional_rd.split(',') if email.strip()]
                        lista_destinatarios_rd.extend(correos_limpios)
                    
                    msg = MIMEMultipart()
                    msg['From'] = remitente
                    msg['To'] = ", ".join(lista_destinatarios_rd)
                    msg['Subject'] = f"Reporte Diario ROV - {centro_rd} - {fecha_rd}"
                    msg.attach(MIMEText("Se adjunta el Reporte Diario de operaciones ROV.", 'plain'))

                    with open(archivo_pdf_rd, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={archivo_pdf_rd}")
                    msg.attach(part)

                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(remitente, password)
                    server.sendmail(remitente, lista_destinatarios_rd, msg.as_string())
                    server.quit()

                    st.success(f"Reporte Diario emitido exitosamente a: {', '.join(lista_destinatarios_rd)}")
                    
                    with open(archivo_pdf_rd, "rb") as pdf_file:
                        st.download_button(label="📥 Descargar Copia PDF", data=pdf_file, file_name=archivo_pdf_rd, mime="application/pdf")

                except Exception as e:
                    st.error(f"Error en la ejecución técnica: {e}")
