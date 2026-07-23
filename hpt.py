import streamlit as st
import pandas as pd
import datetime
import os
import time
import smtplib
import imaplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import uuid
import urllib.request
import zipfile
import io
from supabase import create_client, Client

st.set_page_config(
    page_title="Plataforma TechTrident",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #000511 0%, #00122c 50%, #002353 100%);
    }
    h1, h2, h3, p, label, .stMarkdown, span, .stCheckbox label span {
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
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
        border-radius: 6px;
        border: 1px solid #00a8cc;
        color: #1a202c !important;
        background-color: #f8fafc !important;
        font-weight: 500;
    }
    .stTextInput>div>div>input:disabled {
        background-color: #1e293b !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
        border: 1px solid #475569;
    }
    ::placeholder {
        color: #64748b !important;
        opacity: 1;
    }
    </style>
    """,
    unsafe_allow_html=True
)

CLAVE_ADMIN = "9926"

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ==========================================
# CONFIGURACIÓN MODO PRUEBAS (CERO SPAM)
# ==========================================
USUARIOS = {
    "Ntorres": "17909926", 
    "admin": "admin"
}

CENTROS_AREAS = {
    "Centro Punta Vergara": "Area Austral"
}

# TODO LISTO PARA INICIAR PRUEBAS.
CENTROS_CORREOS = {"Centro Punta Vergara": "centro.puntavergara@blumar.com"}
CORREOS_PREVENCION = ["franco.vidal@blumar.com", "jonathan.romero@blumar.com"]
CORREOS_OCULTOS = ["calarcon@incinel.cl", "ealvarez@incinel.cl"]

¡Haz tu prueba nomás, genera la HPT, firma con el dedo y me avisas cómo te va! 🚢⚓

RANGOS_INICIO = [f"{str(h).zfill(2)}:{str(m).zfill(2)}" for h in range(6, 12) for m in (0, 30)]  
RANGO_TERMINO = [f"{str(h).zfill(2)}:{str(m).zfill(2)}" for h in range(16, 21) for m in (0, 30)] 
RANGO_DURACION = ["5 minutos", "10 minutos", "15 minutos", "20 minutos", "25 minutos", "30 minutos"]
RANGO_HORA_DIFUSION = [f"{str(h).zfill(2)}:{str(m).zfill(2)}" for h in range(6, 13) for m in (0, 15, 30, 45) if not (h == 12 and m > 0)]

try:
    # Solo inicializamos la conexión para el Historial, NO sobrescribimos usuarios/centros.
    supabase = init_connection()
except Exception as e:
    st.sidebar.warning("Advertencia: Conexión Supabase inactiva.")

if 'local_hpt_history' not in st.session_state: st.session_state.local_hpt_history = []
if 'local_reportes_history' not in st.session_state: st.session_state.local_reportes_history = []
if 'local_entrega_history' not in st.session_state: st.session_state.local_entrega_history = []

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_user' not in st.session_state: st.session_state.current_user = ""
if 'current_page' not in st.session_state: st.session_state.current_page = 'login'
if 'hpt_step' not in st.session_state: st.session_state.hpt_step = 1

if 'hpt_pdf_generado' not in st.session_state: st.session_state.hpt_pdf_generado = None
if 'rd_pdf_generado' not in st.session_state: st.session_state.rd_pdf_generado = None

if 'hpt_data' not in st.session_state:
    st.session_state.hpt_data = {
        "empresa": "Salmones Blumar Magallanes", "fecha": datetime.date.today(), "hora_inicio": RANGOS_INICIO[2],
        "hora_termino": RANGO_TERMINO[2], "centro": list(CENTROS_AREAS.keys())[0] if CENTROS_AREAS else "",
        "correo": "", "encargado": "", "ponton": "", "condicion_puerto": "Abierto", "tarea": "",
        "epp": [False]*7, "faena": "Inspeccion Red pecera", "erc": [False]*6, "tc_duracion": "15 minutos"
    }
if 'admin_acceso_historial' not in st.session_state: st.session_state.admin_acceso_historial = False
if 'admin_acceso_graficos' not in st.session_state: st.session_state.admin_acceso_graficos = False

def set_page(page_name): st.session_state.current_page = page_name
def set_step(step_number): st.session_state.hpt_step = step_number

def procesar_firma(canvas_obj, filename):
    if canvas_obj.image_data is not None:
        img_data = canvas_obj.image_data
        firma_img = Image.fromarray((img_data).astype('uint8'), mode='RGBA')
        fondo_blanco = Image.new("RGB", firma_img.size, (255, 255, 255))
        fondo_blanco.paste(firma_img, mask=firma_img.split()[3])
        fondo_blanco.save(filename)
        return True
    return False

def generar_pdf_entrega(datos, logo_filename, nombre_archivo, firma_path=None, imagenes_subidas=None):
    pdf = FPDF()
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=15) 
    pdf.add_page()
    if os.path.exists(logo_filename):
        pdf.image(logo_filename, x=10, y=10, h=25)
        pdf.set_y(40) 
    else: pdf.set_y(15)
        
    pdf.set_font("Helvetica", 'B', 15)
    pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255) 
    pdf.cell(190, 10, "REPORTE FORMAL DE ENTREGA DE TURNO - ROV", border=1, ln=True, align='C', fill=True)
    pdf.set_font("Helvetica", 'I', 10); pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 7, f"Documento generado el {datetime.date.today().strftime('%d/%m/%Y')}", border=1, ln=True, align='C')
    pdf.ln(4)
    
    for seccion, campos in datos.items():
        if pdf.get_y() > 250: pdf.add_page()
        pdf.ln(3); pdf.set_font("Helvetica", 'B', 12); pdf.set_fill_color(200, 215, 230) 
        pdf.cell(190, 8, f"  {seccion.upper()}", border=1, ln=True, fill=True)
        for clave, valor in campos.items():
            nombre_campo = clave.replace('_', ' ')
            if pdf.get_y() > 265: pdf.add_page()
            pdf.set_font("Helvetica", 'B', 10); pdf.set_fill_color(240, 240, 240)
            pdf.cell(190, 6, f" {nombre_campo}:", border=1, ln=True, fill=True)
            pdf.set_font("Helvetica", '', 10)
            if isinstance(valor, list):
                for i in range(0, len(valor), 2):
                    item1 = f" - {valor[i]}".encode('latin-1', 'replace').decode('latin-1')
                    item2 = f" - {valor[i+1]}".encode('latin-1', 'replace').decode('latin-1') if i+1 < len(valor) else ""
                    pdf.cell(95, 6, item1, border="L", ln=0)
                    pdf.cell(95, 6, item2, border="R", ln=1)
                x = pdf.get_x(); y = pdf.get_y()
                pdf.line(x, y, x+190, y); pdf.ln(1)
            else:
                valor_seguro = str(valor).strip() if str(valor).strip() != "" else "Sin registro o sin novedades."
                valor_seguro = valor_seguro.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(190, 6, txt=f" {valor_seguro}", border=1); pdf.ln(1) 

    if imagenes_subidas:
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 12); pdf.set_fill_color(200, 215, 230)
        pdf.cell(190, 8, "  EVIDENCIA FOTOGRAFICA", border=1, ln=True, fill=True); pdf.ln(5)
        col_img = 0; row_y = pdf.get_y(); max_h_row = 0
        for img_file in imagenes_subidas:
            temp_path = f"temp_{uuid.uuid4().hex[:6]}_{img_file.name}"
            with open(temp_path, "wb") as f: f.write(img_file.getbuffer())
            with Image.open(temp_path) as pil_img:
                if pil_img.mode in ('RGBA', 'LA') or (pil_img.mode == 'P' and 'transparency' in pil_img.info):
                    pil_img = pil_img.convert('RGB')
                    pil_img.save(temp_path)
                w_px, h_px = pil_img.size; aspect = h_px / w_px
                if aspect > (80 / 85): h_mm = 80; w_mm = 80 / aspect
                else: w_mm = 85; h_mm = 85 * aspect
            if col_img == 2: col_img = 0; row_y += max_h_row + 10; max_h_row = 0
            if row_y + 85 > 280: pdf.add_page(); row_y = pdf.get_y(); col_img = 0; max_h_row = 0
            x_pos = 15 if col_img == 0 else 110
            pdf.rect(x_pos - 1, row_y - 1, w_mm + 2, h_mm + 2)
            pdf.image(temp_path, x=x_pos, y=row_y, w=w_mm, h=h_mm)
            max_h_row = max(max_h_row, h_mm); col_img += 1
            os.remove(temp_path) 
        pdf.set_y(row_y + max_h_row + 10)

    if pdf.get_y() > 230: pdf.add_page()
    y_img = pdf.get_y() + 10
    if firma_path and os.path.exists(firma_path): pdf.image(firma_path, x=65, y=y_img, w=60, h=25)
    pdf.set_y(y_img + 25); pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(190, 5, "_______________________", border=0, ln=1, align='C')
    pdf.cell(190, 5, "Firma Piloto ROV Saliente", border=0, ln=1, align='C')

    # Pie de página / Marca de Agua
    pdf.set_auto_page_break(auto=False)
    pdf.set_y(-12)
    pdf.set_font("Helvetica", 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(190, 10, "TridenTech 2026©".encode('latin-1', 'replace').decode('latin-1'), border=0, align='C')

    pdf.output(nombre_archivo)
    return nombre_archivo

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        
        st.markdown("<h3 style='text-align: center; color: white; margin-bottom: 20px;'>Portal Operativo ROV</h3>", unsafe_allow_html=True)
        
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

elif st.session_state.current_page == 'main_menu':
    st.title("Sistema de Gestión Operativa")
    st.write(f"Operador en turno: **{st.session_state.current_user}**")
    
    if st.session_state.current_user == 'admin':
        st.markdown("---")
        st.subheader("📊 Panel de Control en Tiempo Real")
        
        try:
            res_hpt = supabase.table('hpt_history').select('*').execute()
            res_rd = supabase.table('reportes_history').select('*').execute()
            df_hpt = pd.DataFrame(res_hpt.data)
            df_rd = pd.DataFrame(res_rd.data)
        except:
            df_hpt = pd.DataFrame(st.session_state.local_hpt_history)
            df_rd = pd.DataFrame(st.session_state.local_reportes_history)
        
        total_hpt = len(df_hpt) if not df_hpt.empty else 0
        total_rd = len(df_rd) if not df_rd.empty else 0
        total_reportes = total_hpt + total_rd
        
        hoy_str = str(datetime.date.today())
        
        hpt_hoy = df_hpt[df_hpt['fecha'] == hoy_str] if not df_hpt.empty and 'fecha' in df_hpt.columns else pd.DataFrame()
        rd_hoy = df_rd[df_rd['fecha'] == hoy_str] if not df_rd.empty and 'fecha' in df_rd.columns else pd.DataFrame()
        
        reportes_hoy_total = len(hpt_hoy) + len(rd_hoy)
        pilotos_activos = ["Ntorres"] # Solo tu piloto activo para el dashboard
        
        pilotos_con_hpt = hpt_hoy['usuario'].unique().tolist() if not hpt_hoy.empty else []
        pilotos_con_rd = rd_hoy['usuario'].unique().tolist() if not rd_hoy.empty else []
        
        pendientes_hpt = [p for p in pilotos_activos if p not in pilotos_con_hpt]
        pendientes_rd = [p for p in pilotos_activos if p not in pilotos_con_rd]
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Reportes Totales (Históricos)", total_reportes)
        m2.metric("Reportes Enviados Hoy", reportes_hoy_total)
        m3.metric("Pilotos Operativos Plataforma", len(pilotos_activos))
        
        st.markdown("**Estado de Reportabilidad del Día:**")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if pendientes_hpt:
                st.warning(f"⚠️ **HPT Pendientes:** {', '.join(pendientes_hpt)}")
            else:
                st.success("✅ Todas las HPT del día enviadas.")
        with col_p2:
            if pendientes_rd:
                st.warning(f"⚠️ **Reportes Diarios Pendientes:** {', '.join(pendientes_rd)}")
            else:
                st.success("✅ Todos los Reportes Diarios enviados.")
                
        hora_chile = (datetime.datetime.utcnow() - datetime.timedelta(hours=4)).time()
        limite_hpt = datetime.time(9, 30)
        limite_rd = datetime.time(20, 0)
        
        if hora_chile > limite_hpt and pendientes_hpt:
            st.error("🚨 **ALERTA CRÍTICA:** Son pasadas las 09:30 AM y existen HPT pendientes por envío.")
        
        if hora_chile > limite_rd and pendientes_rd:
            st.error("🚨 **ALERTA CRÍTICA:** Son pasadas las 20:00 Hrs y existen Reportes Diarios pendientes por envío.")
            
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⚓ MÓDULO HPT", use_container_width=True): set_page('hpt_menu'); st.rerun()
        if st.button("📋 ENTREGA DE TURNO", use_container_width=True): set_page('entrega_turno'); st.rerun()
        if st.button("📈 GRÁFICOS GERENCIALES", use_container_width=True): set_page('panel_graficos'); st.rerun()
    with c2:
        if st.button("🚢 REPORTE DIARIO", use_container_width=True): set_page('reporte_diario'); st.rerun()
        if st.button("📊 HISTORIAL / AUDITORÍA", use_container_width=True): set_page('modulo_busqueda'); st.rerun()
        if st.button("🔒 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = ""
            st.session_state.admin_acceso_historial = False
            st.session_state.admin_acceso_graficos = False
            set_page('login')
            st.rerun()

elif st.session_state.current_page == 'hpt_menu':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("Módulo HPT")
    st.divider()
    if st.button("➕ CREAR NUEVA HPT", use_container_width=True): 
        set_step(1)
        st.session_state.hpt_pdf_generado = None 
        set_page('hpt_nuevo')
        st.rerun()

elif st.session_state.current_page == 'hpt_nuevo':
    st.button("⬅️ Cancelar y Volver al Menú HPT", on_click=set_page, args=('hpt_menu',))
    st.title("Nueva HPT - Paso " + str(st.session_state.hpt_step))
    st.progress(st.session_state.hpt_step / 4.0)
    
    if st.session_state.hpt_step == 1:
        st.subheader("Datos Operativos")
        opciones_empresa = ["Salmones Blumar Magallanes", "Salmones Blumar"]
        idx_empresa = opciones_empresa.index(st.session_state.hpt_data.get("empresa", opciones_empresa[0])) if st.session_state.hpt_data.get("empresa") in opciones_empresa else 0
        empresa = st.selectbox("Empresa", opciones_empresa, index=idx_empresa)
        
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", value=st.session_state.hpt_data.get("fecha", datetime.date.today()))
            idx_hi = RANGOS_INICIO.index(st.session_state.hpt_data["hora_inicio"]) if st.session_state.hpt_data["hora_inicio"] in RANGOS_INICIO else 0
            hora_inicio = st.selectbox("Hora de Inicio", RANGOS_INICIO, index=idx_hi)
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
            
        opciones_faena = ["Inspeccion Red Lobera", "Inspeccion Red pecera", "Inspeccion Tensores", "Recuperacion inorganico", "Apoyo Centro de cultivo", "Extraccion de mortalidad", "Mantencion equipos", "Sin faena"]
        
        if condicion_puerto == "Cerrado total":
            st.warning("⚠️ **Puerto Cerrado Total:** Se saltarán los pasos de EPP y ERC. La faena se registra como 'Sin faena'.")
            faena = "Sin faena"
        else:
            idx_faena = opciones_faena.index(st.session_state.hpt_data.get("faena", opciones_faena[0])) if st.session_state.hpt_data.get("faena") in opciones_faena else 0
            faena = st.selectbox("Faena a realizar", opciones_faena, index=idx_faena)
        
        if st.button("SIGUIENTE ➡️", use_container_width=True):
            st.session_state.hpt_data.update({"empresa": empresa, "fecha": fecha, "hora_inicio": hora_inicio, "hora_termino": hora_termino, "centro": centro, "area": area_asignada, "correo": correo, "encargado": encargado, "ponton": ponton, "condicion_puerto": condicion_puerto, "faena": faena})
            if condicion_puerto == "Cerrado total":
                set_step(4) 
            else:
                set_step(2)
            st.rerun()

    elif st.session_state.hpt_step == 2:
        st.subheader("Checklist EPP")
        st.markdown("<p style='color: #00a8cc !important;'>⚠️ Los elementos con (*) son strictly obligatorios.</p>", unsafe_allow_html=True)
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
                set_step(1); st.rerun()
        with col_btn2:
            if st.button("SIGUIENTE ➡️", key="next2", use_container_width=True):
                if not (epp_chaleco and epp_termica and epp_comunicacion and epp_botiquin): st.error("⚠️ No cumple con EPP mínimos.")
                else: st.session_state.hpt_data["epp"] = [epp_guantes, epp_chaleco, epp_zapatos, epp_termica, epp_traje, epp_comunicacion, epp_botiquin]; set_step(3); st.rerun()

    elif st.session_state.hpt_step == 3:
        st.subheader("Detalles de Faena y Checklist ERC")
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
                set_step(2); st.rerun()
        with col_btn2:
            if st.button("SIGUIENTE ➡️", key="next3", use_container_width=True):
                st.session_state.hpt_data.update({"tarea": tarea, "erc": [erc_izaje, erc_buceo, erc_electricos, erc_caidas, erc_navegacion, erc_atrapamiento]})
                set_step(4); st.rerun()

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
                if st.session_state.hpt_data.get("condicion_puerto") == "Cerrado total":
                    set_step(1)
                else:
                    set_step(3)
                st.rerun()
                
        with col_btn2:
            if st.button("GENERAR Y ENVIAR HPT", type="primary", use_container_width=True):
                data = st.session_state.hpt_data
                barra_carga = st.progress(0, text="⚙️ Generando PDF...")
                
                try:
                    pdf = FPDF(); pdf.add_page()
                    if os.path.exists("logo.png"): pdf.image("logo.png", x=10, y=8, h=20)
                    pdf.set_y(32); pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 10, "HERRAMIENTA DE PREVENCION EN TERRENO (HPT) - ROV", border=1, ln=True, align="C"); pdf.ln(2)
                    pdf.set_fill_color(200, 220, 255); pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "1. DATOS OPERATIVOS", border=1, ln=True, fill=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Empresa / Mandante:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('empresa', '')[:35], border=1)
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
                    
                    pdf.set_font("Arial", "B", 8)
                    pdf.cell(190, 6, "Faena Primaria y Detalles Especificos:", border=1, ln=True, fill=True)
                    pdf.set_font("Arial", "", 8)
                    texto_tarea = f"FAENA: {data.get('faena', '')}\nDETALLES: {data.get('tarea', '')}"
                    pdf.multi_cell(190, 5, texto_tarea, border=1)

                    pdf.ln(3); pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "2. EQUIPO DE PROTECCION PERSONAL SELECCIONADO", border=1, ln=True, fill=True); pdf.set_font("Arial", "", 8)
                    epp_labels = ["Guantes", "Chaleco", "Zapatos", "Ropa Termica", "Traje Agua", "Comunicacion", "Botiquin"]
                    epp_vals = data.get('epp', []); epp_seleccionados = [epp_labels[i] for i in range(len(epp_labels)) if i < len(epp_vals) and epp_vals[i]]
                    if not epp_seleccionados: pdf.cell(190, 6, "Ningun EPP registrado o Aplica (Puerto Cerrado Total).", border=1, ln=True)
                    else:
                        for i, epp in enumerate(epp_seleccionados): pdf.cell(190/3, 6, f"[ X ] {epp}", border=1, ln=1 if (i + 1) % 3 == 0 or i == len(epp_seleccionados) - 1 else 0)

                    pdf.ln(3); pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "3. RIESGOS CRITICOS EVALUADOS (ERC)", border=1, ln=True, fill=True); pdf.set_font("Arial", "", 8)
                    erc_labels = ["Izaje", "Buceo", "Eq. Electricos", "Caidas", "Navegacion", "Atrapamiento"]
                    erc_vals = data.get('erc', []); erc_seleccionados = [erc_labels[i] for i in range(len(erc_labels)) if i < len(erc_vals) and erc_vals[i]]
                    if not erc_seleccionados: pdf.cell(190, 6, "Ningun Riesgo seleccionado o Aplica (Puerto Cerrado Total).", border=1, ln=True)
                    else:
                        for i, erc in enumerate(erc_seleccionados): pdf.cell(190/2, 6, f"[ X ] {erc}", border=1, ln=1 if (i + 1) % 2 == 0 or i == len(erc_seleccionados) - 1 else 0)

                    pdf.ln(3); pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "4. DIFUSION Y TOMA DE CONOCIMIENTO", border=1, ln=True, fill=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Relator / Piloto:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, tc_relator[:35], border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Cargo Relator:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, "Piloto ROV", border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Tema Difundido:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, tc_nombre[:80], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Fecha y Hora:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, f"{tc_fecha} {tc_hora}", border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Duracion Rango:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, tc_duracion, border=1, ln=True)

                    pdf.ln(2); pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "5. CUADRO DE FIRMAS RESPONSABLES", border=1, ln=True, fill=True)
                    pdf.cell(95, 18, "", border=1); pdf.cell(95, 18, "", border=1, ln=True)
                    id_firmas = uuid.uuid4().hex[:8]; f_serv = f"f_serv_{id_firmas}.jpg"; f_enc = f"f_encargado_{id_firmas}.jpg"
                    if procesar_firma(firma_sup_serv, f_serv): pdf.image(f_serv, x=35, y=pdf.get_y()-17, w=45, h=15)
                    if procesar_firma(firma_encargado, f_enc): pdf.image(f_enc, x=130, y=pdf.get_y()-17, w=45, h=15)
                    pdf.set_font("Arial", "B", 8); pdf.cell(95, 6, "Firma Supervisor Servicio", border=1, align="C"); pdf.cell(95, 6, "Firma Encargado de Centro", border=1, ln=True, align="C")

                    # Pie de página / Marca de Agua
                    pdf.set_auto_page_break(auto=False)
                    pdf.set_y(-12)
                    pdf.set_font("Arial", "I", 8)
                    pdf.set_text_color(128, 128, 128)
                    pdf.cell(190, 10, "TridenTech 2026©".encode('latin-1', 'replace').decode('latin-1'), border=0, align="C")

                    identificador_unico = str(uuid.uuid4())[:8]
                    archivo_pdf = f"HPT_{data.get('centro','').replace(' ', '_')}_{data.get('fecha')}_{identificador_unico}.pdf"
                    pdf.output(archivo_pdf)
                    
                    st.session_state.hpt_pdf_generado = archivo_pdf

                    url_pdf_nube = ""
                    for intento in range(3):
                        try:
                            time.sleep(0.5) 
                            with open(archivo_pdf, "rb") as f:
                                supabase.storage.from_("documentos").upload(path=archivo_pdf, file=f, file_options={"content-type": "application/pdf"})
                            url_pdf_nube = supabase.storage.from_("documentos").get_public_url(archivo_pdf)
                            break 
                        except Exception as upload_error:
                            if intento == 2: st.error(f"⚠️ Error al subir PDF: {upload_error}")
                            time.sleep(1) 

                    row_data = {
                        "fecha": str(data.get('fecha')), "usuario": st.session_state.current_user,
                        "empresa": data.get('empresa'), "centro": data.get('centro'), "area": data.get('area'),
                        "ponton": data.get('ponton'), "condicion_puerto": data.get('condicion_puerto'),
                        "hora_inicio": data.get('hora_inicio'), "hora_termino": data.get('hora_termino'), 
                        "faena": data.get('faena'), "tarea": data.get('tarea'), "url_documento": url_pdf_nube
                    }
                    try: supabase.table('hpt_history').insert(row_data).execute()
                    except Exception as db_err: st.error(f"⚠️ Error al guardar en BD: {db_err}"); st.session_state.local_hpt_history.append(row_data)

                    barra_carga.progress(60, text="📧 Enviando PDF...")
                    remitente = st.secrets["EMAIL_USER"]
                    password = st.secrets["EMAIL_PASS"]
                    servidor_smtp = st.secrets.get("SMTP_SERVER", "mail.incinel.cl")
                    puerto_smtp = st.secrets.get("SMTP_PORT", 587)
                    
                    correo_centro = data.get('correo', remitente)
                    lista_destinatarios = [correo_centro, CORREOS_PREVENCION[0], CORREOS_PREVENCION[1]]
                    
                    msg = MIMEMultipart()
                    msg['From'] = remitente
                    msg['To'] = ", ".join(lista_destinatarios)
                    msg['Bcc'] = ", ".join(CORREOS_OCULTOS + [remitente])
                    msg['Subject'] = f"Reporte HPT - {data.get('centro')}"
                    msg.attach(MIMEText("Estimados muy buen dia, junto con saludar se adjunta HPT.", 'plain'))
                    
                    with open(archivo_pdf, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream"); part.set_payload(attachment.read())
                    encoders.encode_base64(part); part.add_header("Content-Disposition", f"attachment; filename={archivo_pdf}"); msg.attach(part)
                    
                    server = smtplib.SMTP(servidor_smtp, puerto_smtp)
                    server.starttls()
                    server.login(remitente, password)
                    server.send_message(msg)
                    server.quit()

                    try:
                        imap = imaplib.IMAP4_SSL(servidor_smtp, 993)
                        imap.login(remitente, password)
                        imap.append('INBOX.Sent', '\\Seen', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                        imap.logout()
                    except Exception:
                        pass

                    if os.path.exists(f_serv): os.remove(f_serv)
                    if os.path.exists(f_enc): os.remove(f_enc)

                    barra_carga.progress(100, text="✅ ¡LISTO!")
                    time.sleep(0.5); barra_carga.empty()
                except Exception as e:
                    barra_carga.empty(); st.error(f"Falla: {e}")
        
        if st.session_state.hpt_pdf_generado and os.path.exists(st.session_state.hpt_pdf_generado):
            st.success("✅ HPT Generada, Guardada y Enviada con éxito.")
            
            if st.button("📝 CREAR NUEVA HPT", type="secondary", use_container_width=True):
                st.session_state.hpt_pdf_generado = None
                st.session_state.hpt_step = 1
                st.session_state.hpt_data = {
                    "empresa": "Salmones Blumar Magallanes", "fecha": datetime.date.today(), "hora_inicio": RANGOS_INICIO[2],
                    "hora_termino": RANGO_TERMINO[2], "centro": list(CENTROS_AREAS.keys())[0] if CENTROS_AREAS else "",
                    "correo": "", "encargado": "", "ponton": "", "condicion_puerto": "Abierto", "tarea": "",
                    "epp": [False]*7, "faena": "Inspeccion Red pecera", "erc": [False]*6, "tc_duracion": "15 minutos"
                }
                st.rerun()
                
            with open(st.session_state.hpt_pdf_generado, "rb") as pdf_file:
                st.download_button(label="📥 Descargar Copia Local PDF", data=pdf_file, file_name=st.session_state.hpt_pdf_generado, mime="application/pdf", use_container_width=True)

elif st.session_state.current_page == 'reporte_diario':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("Reporte Diario Operativo")
    st.divider()

    st.subheader("Datos Operacionales de Faena")
    opciones_centros = list(CENTROS_AREAS.keys()); centro_rd = st.selectbox("Centro de Cultivo", opciones_centros)
    area_rd = CENTROS_AREAS.get(centro_rd, "Desconocida"); correo_asignado_rd = CENTROS_CORREOS.get(centro_rd, "sin_correo@blumar.com")
    st.info(f"⚓ Área Asignada: **{area_rd}** | 📬 Correo Central: **{correo_asignado_rd}**")

    estado_turno = st.radio("Estado Operativo del Piloto", ["Operativo (Faena Normal)", "Detenido por Salud / Licencia", "Día de Descanso"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        fecha_rd = st.date_input("Fecha", value=datetime.date.today())
        piloto_rd = st.text_input("Nombre de Piloto", value=st.session_state.current_user)
        condicion_puerto_rd = st.selectbox("Condición de Puerto", ["Abierto", "Cerrado para naves menores", "Cerrado total"])
        ponton_rd = st.text_input("Nombre Pontón")

    if estado_turno != "Operativo (Faena Normal)" or condicion_puerto_rd == "Cerrado total":
        st.warning("⚠️ **Modo Express Activado:** Se omitirán los detalles de faena por inactividad. Solo firme y envíe para mantener la trazabilidad.")
        with col2:
            st.text_input("Jaula / Balsa", value="N/A (Sin operaciones)", disabled=True)
            st.text_input("Rango Horario", value="N/A", disabled=True)
            correo_adicional_rd = st.text_input("Correos Adicionales (Separados por coma)", placeholder="correo1@blumar.com")
        
        jaula_rd = "N/A"
        hora_inicio_rd = "08:00"
        hora_termino_rd = "18:00"
        motivo = "Condición de Puerto Cerrado Total" if condicion_puerto_rd == "Cerrado total" else estado_turno
        tarea_rd = f"Jornada sin operaciones submarinas. Motivo de inactividad: {motivo}."
        st.info(f"📝 **Descripción Automática generada para el PDF:** {tarea_rd}")
    else:
        with col2:
            jaula_rd = st.text_input("Jaula / Balsa Trabajada")
            hora_inicio_rd = st.selectbox("Hora Inicio Rango", RANGOS_INICIO)
            hora_termino_rd = st.selectbox("Hora Término Rango", RANGO_TERMINO)
            correo_adicional_rd = st.text_input("Correos Adicionales (Separados por coma)", placeholder="correo1@blumar.com")
            
        tarea_rd = st.text_area("Descripción de la Tarea Realizada")
        
    st.subheader("Firmas de Responsabilidad")
    col_f_rd1, col_f_rd2 = st.columns(2)
    with col_f_rd1:
        st.write("Firma Piloto ROV")
        firma_piloto_rd = st_canvas(stroke_width=2, stroke_color="#000", background_color="#FFF", height=150, width=300, key="firma_p_rd")
    with col_f_rd2:
        st.write("Firma Encargado de Centro")
        firma_encargado_rd = st_canvas(stroke_width=2, stroke_color="#000", background_color="#FFF", height=150, width=300, key="firma_e_rd")

    submit_rd = st.button("GENERAR Y ENVIAR REPORTE DIARIO", type="primary", use_container_width=True)

    if submit_rd:
        barra_rd = st.progress(0, text="⚙️ Generando PDF...")
        try:
            pdf_rd = FPDF(); pdf_rd.add_page()
            if os.path.exists("logo.png"): pdf_rd.image("logo.png", x=10, y=8, h=20)
            pdf_rd.set_y(32); pdf_rd.set_font("Arial", "B", 14); pdf_rd.cell(0, 10, "REPORTE DIARIO DE OPERACIONES - ROV", border=1, ln=True, align="C"); pdf_rd.ln(3)
            
            pdf_rd.set_fill_color(200, 220, 255); pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(190, 6, "1. DATOS GENERALES", border=1, ln=True, fill=True)
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(30, 6, "Fecha:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(65, 6, str(fecha_rd), border=1)
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(30, 6, "Rango Horario:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(65, 6, f"{hora_inicio_rd} - {hora_termino_rd}", border=1, ln=True)
            
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(30, 6, "Piloto ROV:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(65, 6, piloto_rd, border=1)
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(30, 6, "Nombre Ponton:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(65, 6, ponton_rd, border=1, ln=True)
            
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(30, 6, "Centro Cultivo:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(65, 6, centro_rd, border=1)
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(30, 6, "Area Asignada:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(65, 6, area_rd, border=1, ln=True)
            
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(35, 6, "Condicion Puerto:", border=1); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(155, 6, condicion_puerto_rd, border=1, ln=True)

            pdf_rd.ln(5); pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(190, 6, "2. DETALLE OPERATIVO", border=1, ln=True, fill=True)
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(190, 6, "Estructura Intervenida:", border=1, ln=True, fill=True); pdf_rd.set_font("Arial", "", 8); pdf_rd.cell(190, 6, jaula_rd, border=1, ln=True)
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(190, 6, "Descripcion de la Tarea Realizada:", border=1, ln=True, fill=True); pdf_rd.set_font("Arial", "", 8)
            pdf_rd.multi_cell(190, 6, tarea_rd, border=1)
            
            pdf_rd.ln(4); pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(190, 6, "3. CUADRO DE FIRMAS RESPONSABLES", border=1, ln=True, fill=True)
            pdf_rd.cell(95, 18, "", border=1); pdf_rd.cell(95, 18, "", border=1, ln=True)
            id_firmas_rd = uuid.uuid4().hex[:8]; f_pil_rd = f"f_p_rd_{id_firmas_rd}.jpg"; f_enc_rd = f"f_e_rd_{id_firmas_rd}.jpg"
            if procesar_firma(firma_piloto_rd, f_pil_rd): pdf_rd.image(f_pil_rd, x=35, y=pdf_rd.get_y()-17, w=45, h=15)
            if procesar_firma(firma_encargado_rd, f_enc_rd): pdf_rd.image(f_enc_rd, x=130, y=pdf_rd.get_y()-17, w=45, h=15)
            pdf_rd.set_font("Arial", "B", 8); pdf_rd.cell(95, 6, "Firma Piloto ROV", border=1, align="C"); pdf_rd.cell(95, 6, "Firma Encargado de Centro", border=1, ln=True, align="C")
            
            # Pie de página / Marca de Agua
            pdf_rd.set_auto_page_break(auto=False)
            pdf_rd.set_y(-12)
            pdf_rd.set_font("Arial", "I", 8)
            pdf_rd.set_text_color(128, 128, 128)
            pdf_rd.cell(190, 10, "TridenTech 2026©".encode('latin-1', 'replace').decode('latin-1'), border=0, align="C")

            identificador_unico_rd = str(uuid.uuid4())[:8]
            archivo_pdf_rd = f"Reporte_Diario_{centro_rd.replace(' ', '_')}_{fecha_rd}_{identificador_unico_rd}.pdf"
            pdf_rd.output(archivo_pdf_rd)
            
            st.session_state.rd_pdf_generado = archivo_pdf_rd

            url_pdf_rd_nube = ""
            for intento in range(3):
                try:
                    time.sleep(0.5) 
                    with open(archivo_pdf_rd, "rb") as f:
                        supabase.storage.from_("documentos").upload(path=archivo_pdf_rd, file=f, file_options={"content-type": "application/pdf"})
                    url_pdf_rd_nube = supabase.storage.from_("documentos").get_public_url(archivo_pdf_rd)
                    break 
                except Exception as upload_error_rd:
                    if intento == 2: st.error(f"⚠️ Error al subir Reporte a Supabase: {upload_error_rd}")
                    time.sleep(1)

            datos_rd = {
                "fecha": str(fecha_rd), "usuario": piloto_rd, "centro": centro_rd, "area": area_rd,
                "jaula": jaula_rd, "ponton": ponton_rd, "hora_inicio": str(hora_inicio_rd),
                "hora_termino": str(hora_termino_rd), "condicion_puerto": condicion_puerto_rd, "tarea": tarea_rd, "url_documento": url_pdf_rd_nube
            }
            try: supabase.table('reportes_history').insert(datos_rd).execute()
            except Exception as db_err: st.error(f"⚠️ Error al guardar en BD: {db_err}"); st.session_state.local_reportes_history.append(datos_rd)

            barra_rd.progress(60, text="📧 Enviando PDF...")
            remitente = st.secrets["EMAIL_USER"]
            password = st.secrets["EMAIL_PASS"]
            servidor_smtp = st.secrets.get("SMTP_SERVER", "mail.incinel.cl")
            puerto_smtp = st.secrets.get("SMTP_PORT", 587)

            lista_destinatarios_rd = [correo_asignado_rd]
            if correo_adicional_rd.strip(): lista_destinatarios_rd.extend([e.strip() for e in correo_adicional_rd.split(',') if e.strip()])
            
            msg = MIMEMultipart()
            msg['From'] = remitente
            msg['To'] = ", ".join(lista_destinatarios_rd)
            msg['Bcc'] = ", ".join(CORREOS_OCULTOS + [remitente])
            msg['Subject'] = f"Reporte Diario ROV - {centro_rd}"
            msg.attach(MIMEText("Estimados muy buenas tardes, junto con saludar se adjunta reporte diario.", 'plain'))
            
            with open(archivo_pdf_rd, "rb") as attachment:
                part = MIMEBase("application", "octet-stream"); part.set_payload(attachment.read())
            encoders.encode_base64(part); part.add_header("Content-Disposition", f"attachment; filename={archivo_pdf_rd}"); msg.attach(part)
            
            server = smtplib.SMTP(servidor_smtp, puerto_smtp)
            server.starttls()
            server.login(remitente, password)
            server.send_message(msg)
            server.quit()

            try:
                imap = imaplib.IMAP4_SSL(servidor_smtp, 993)
                imap.login(remitente, password)
                imap.append('INBOX.Sent', '\\Seen', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                imap.logout()
            except Exception:
                pass
            
            if os.path.exists(f_pil_rd): os.remove(f_pil_rd)
            if os.path.exists(f_enc_rd): os.remove(f_enc_rd)

            barra_rd.progress(100, text="✅ ¡LISTO!")
            time.sleep(0.5); barra_rd.empty(); 
        except Exception as e:
            barra_rd.empty(); st.error(f"Error técnico: {e}")
            
    if st.session_state.rd_pdf_generado and os.path.exists(st.session_state.rd_pdf_generado):
        st.success("✅ Reporte Diario Generado y Enviado con éxito.")
        if st.button("📝 CREAR NUEVO REPORTE DIARIO", type="secondary", use_container_width=True):
            st.session_state.rd_pdf_generado = None
            st.rerun()
            
        with open(st.session_state.rd_pdf_generado, "rb") as pdf_file: 
            st.download_button(label="📥 Descargar Copia Local PDF", data=pdf_file, file_name=st.session_state.rd_pdf_generado, mime="application/pdf", use_container_width=True)

elif st.session_state.current_page == 'entrega_turno':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("Panel de Entrega de Turno Operativo")
    st.divider()

    st.header("1. Información General")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: piloto_entrante = st.text_input("Piloto Entrante")
    with c2: piloto_saliente = st.text_input("Piloto Saliente", value=st.session_state.current_user)
    with c3: fecha_et = st.date_input("Fecha", datetime.date.today())
    with c4: opciones_centros_et = list(CENTROS_AREAS.keys()); centro_et = st.selectbox("Centro", opciones_centros_et)
    with c5: area_et = CENTROS_AREAS.get(centro_et, "Desconocida"); st.text_input("Área Asignada", value=area_et, disabled=True)

    st.markdown("---"); st.header("2. Equipos en Terreno (ROV)")
    c6, c7, c8, c9 = st.columns(4)
    with c6: equipo_rov = st.selectbox("Modelo de Equipo", ["DTG3", "MC Petrohue", "Chasing Promax", "Chasing Promax 2", "Fifish vs xpert"])
    with c7: estado_equipo = st.selectbox("Estado General del ROV", ["Bueno", "Regular", "Requiere cambio"])
    with c8: estado_controlador = st.selectbox("Estado del Controlador", ["Bueno", "Regular", "Requiere cambio"])
    with c9: estado_umbilical = st.selectbox("Estado del Cable Umbilical", ["Bueno", "Regular", "Requiere cambio"])
    obs_equipos = st.text_area("Observaciones de los Equipos", placeholder="Detalle fallas...")

    st.markdown("---"); st.header("3. Equipamiento de Terreno"); st.write("Seleccione los elementos presentes en terreno:")
    c10, c11, c12, c13, c14 = st.columns(5)
    with c10: carpa = st.checkbox("Carpa plegable")
    with c11: caseta = st.checkbox("Caseta rígida")
    with c12: silla = st.checkbox("Silla plegable")
    with c13: lona = st.checkbox("Lona")
    with c14: estado_equipamiento = st.selectbox("Estado del Equipamiento", ["Bueno", "Regular", "Requiere cambio"])
    obs_equipamiento = st.text_area("Observaciones del Equipamiento", placeholder="Detalle daños...")

    st.markdown("---"); st.header("4. Inventario de Terreno")
    herramientas_base = {"Cuchillo de maniobra con funda (Bahco)": 1, "Cuchillo de maniobra sin funda (Bahco)": 1, "Araña de recuperación de acero inoxidable": 1, "Juego de llaves Allen": 1, "Pelacables": 1, "Alicate de corte diagonal": 1, "Alicate de punta fina (mangos rojo/azul)": 1, "Alicate para anillos de retención (circlips)": 1, "Alicate universal": 1, "Alicate de punta fina pequeño": 1, "Destornilladores": 6}
    materiales_base = {"Frasco de vaselina": 1, "Tubos de grasa dieléctrica (Loctite)": 3, "Paquete de hisopos": 1, "Tapones o conectores cilíndricos negros": 3, "Adhesivo industrial B-7000": 1, "Lata de lubricante penetrante (Afloja Todo)": 1, "WD-40": 1, "Limpia contacto": 1, "Tapones para puerto de carga": 2, "Tapón o cubierta cuadrada pequeña": 1, "Protectores de sensor": 3, "Rollo de cinta de empalme (Splicing tape)": 1, "Cartucho de cuchillas de repuesto": 1, "Repuestos de brazo manipulador grabber": 4}

    resultados_inventario = {}; st.subheader("Herramientas")
    col_h1, col_h2 = st.columns(2); items_herr = list(herramientas_base.items())
    for i, (item, cant_esperada) in enumerate(items_herr):
        col = col_h1 if i < (len(items_herr) // 2 + len(items_herr) % 2) else col_h2
        with col:
            c_check, c_num = st.columns([3, 1])
            with c_check: presente = st.checkbox(item, value=False, key=f"h_{i}")
            with c_num: cantidad = st.number_input("Cant.", min_value=0, max_value=50, value=cant_esperada if presente else 0, step=1, key=f"nh_{i}", disabled=not presente, label_visibility="collapsed")
            resultados_inventario[item] = {"presente": presente, "cantidad": cantidad}

    st.subheader("Materiales de Mantención"); col_m1, col_m2 = st.columns(2); items_mat = list(materiales_base.items())
    for i, (item, cant_esperada) in enumerate(items_mat):
        col = col_m1 if i < (len(items_mat) // 2 + len(items_mat) % 2) else col_m2
        with col:
            c_check, c_num = st.columns([3, 1])
            with c_check: presente = st.checkbox(item, value=False, key=f"m_{i}")
            with c_num: cantidad = st.number_input("Cant.", min_value=0, max_value=50, value=cant_esperada if presente else 0, step=1, key=f"nm_{i}", disabled=not presente, label_visibility="collapsed")
            resultados_inventario[item] = {"presente": presente, "cantidad": cantidad}

    st.markdown("---"); st.header("5. Registro Operativo")
    faena_et = st.text_area("Faena realizada durante el turno de 14 días", height=80)
    alertas_et = st.text_area("Alertas del centro", placeholder="Ej: Rotura en jaula 104...", height=80)
    pendientes_et = st.text_area("Tareas pendientes o a realizar", height=80)
    obs_generales_et = st.text_area("Observaciones Generales", height=80)

    st.markdown("---"); st.header("6. Evidencia Fotográfica y Firmas")
    imagenes_cargadas = st.file_uploader("Cargar imágenes de equipos/terreno (Opcional)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    st.write("✍️ Firma Piloto ROV Saliente"); canvas_piloto = st_canvas(fill_color="rgba(255, 255, 255, 0)", stroke_width=2, stroke_color="#000", background_color="#FFF", height=120, width=300, drawing_mode="freedraw", key="canvas_et")
    correo_destino_et = st.text_input("Correo electrónico del destinatario (Jefatura o Piloto Entrante)", placeholder="jefatura@blumar.com")

    if st.button("Guardar, Generar PDF y Enviar", type="primary", use_container_width=True):
        if not piloto_saliente or not piloto_entrante: st.error("Error: Los campos 'Piloto Entrante' y 'Piloto Saliente' son obligatorios.")
        elif not correo_destino_et: st.error("Error: Ingrese el correo del destinatario.")
        else:
            barra_et = st.progress(0, text="⚙️ Compilando Entrega de Turno...")
            lista_equipamiento = [item for item, selected in zip(["Carpa plegable", "Caseta rígida", "Silla plegable", "Lona"], [carpa, caseta, silla, lona]) if selected]
            txt_equipamiento = ", ".join(lista_equipamiento) if lista_equipamiento else "Ninguno"
            herr_presentes = [f"{item} ({datos['cantidad']})" for item, datos in resultados_inventario.items() if item in herramientas_base and datos['presente'] and datos['cantidad'] > 0]
            herr_faltantes = [item for item, datos in resultados_inventario.items() if item in herramientas_base and (not datos['presente'] or datos['cantidad'] == 0)]
            mat_presentes = [f"{item} ({datos['cantidad']})" for item, datos in resultados_inventario.items() if item in materiales_base and datos['presente'] and datos['cantidad'] > 0]
            mat_faltantes = [item for item, datos in resultados_inventario.items() if item in materiales_base and (not datos['presente'] or datos['cantidad'] == 0)]

            datos_pdf = {
                "1. Información General": {"Piloto_Entrante": piloto_entrante, "Piloto_Saliente": piloto_saliente, "Fecha": str(fecha_et), "Centro": centro_et, "Área": area_et},
                "2. Estado del Equipo": {"Modelo_ROV": equipo_rov, "Estado_ROV": estado_equipo, "Estado_Controlador": estado_controlador, "Cable_Umbilical": estado_umbilical, "Observaciones_Equipos": obs_equipos},
                "3. Terreno": {"Equipamiento_Presente": txt_equipamiento, "Estado_del_Equipamiento": estado_equipamiento, "Observaciones_Equipamiento": obs_equipamiento},
                "4. Herramientas": {"Herramientas_Presentes": herr_presentes if herr_presentes else ["Ninguna"], "Herramientas_Faltantes": herr_faltantes if herr_faltantes else ["Ninguna"]},
                "5. Materiales de Mantención": {"Materiales_Presentes": mat_presentes if mat_presentes else ["Ninguno"], "Materiales_Faltantes": mat_faltantes if mat_faltantes else ["Ninguno"]},
                "6. Operativa de Turno (14 días)": {"Faena_Realizada": faena_et, "Alertas_del_Centro": alertas_et, "Tareas_Pendientes": pendientes_et, "Observaciones_Generales": obs_generales_et}
            }
            firma_path_et = f"firma_et_{uuid.uuid4().hex[:6]}.png"
            if canvas_piloto.image_data is not None: Image.fromarray(canvas_piloto.image_data.astype(np.uint8)).convert("RGB").save(firma_path_et)
            nombre_base_et = f"Entrega_Turno_{centro_et.replace(' ', '_')}_{fecha_et}_{uuid.uuid4().hex[:6]}.pdf"
            
            try:
                archivo_pdf_et = generar_pdf_entrega(datos_pdf, "logo.png", nombre_base_et, firma_path=firma_path_et, imagenes_subidas=imagenes_cargadas)
                barra_et.progress(50, text="☁️ Subiendo a la Nube...")
                url_pdf_et_nube = ""
                for intento in range(3):
                    try:
                        time.sleep(0.5) 
                        with open(archivo_pdf_et, "rb") as f: supabase.storage.from_("documentos").upload(path=archivo_pdf_et, file=f, file_options={"content-type": "application/pdf"})
                        url_pdf_et_nube = supabase.storage.from_("documentos").get_public_url(archivo_pdf_et)
                        break 
                    except Exception as upload_err:
                        if intento == 2: st.error(f"Aviso de subida nube: {upload_err}")
                        time.sleep(1)

                datos_historial_et = {"fecha": str(fecha_et), "usuario": piloto_saliente, "centro": centro_et, "area": area_et, "tipo_reporte": "Entrega de Turno", "url_documento": url_pdf_et_nube}
                try: supabase.table('entrega_history').insert(datos_historial_et).execute()
                except Exception as db_err: st.error(f"⚠️ Error BD: {db_err}"); st.session_state.local_entrega_history.append(datos_historial_et)

                barra_et.progress(80, text="📧 Transmitiendo Correo...")
                remitente = st.secrets["EMAIL_USER"]
                password = st.secrets["EMAIL_PASS"]
                servidor_smtp = st.secrets.get("SMTP_SERVER", "mail.incinel.cl")
                puerto_smtp = st.secrets.get("SMTP_PORT", 587)

                msg = MIMEMultipart()
                msg['From'] = remitente
                msg['To'] = correo_destino_et
                msg['Bcc'] = ", ".join(CORREOS_OCULTOS + [remitente])
                msg['Subject'] = f"INFO: Entrega de Turno ROV - {centro_et}"
                msg.attach(MIMEText("Estimados muy buenas tardes, junto con saludar se adjunta entrega formal de turno.", 'plain'))
                
                with open(archivo_pdf_et, "rb") as attachment: part = MIMEBase("application", "octet-stream"); part.set_payload(attachment.read())
                encoders.encode_base64(part); part.add_header("Content-Disposition", f"attachment; filename={archivo_pdf_et}"); msg.attach(part)
                
                server = smtplib.SMTP(servidor_smtp, puerto_smtp)
                server.starttls()
                server.login(remitente, password)
                server.send_message(msg)
                server.quit()

                try:
                    import imaplib
                    imap = imaplib.IMAP4_SSL(servidor_smtp, 993)
                    imap.login(remitente, password)
                    imap.append('INBOX.Sent', '\\Seen', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                    imap.logout()
                except Exception:
                    pass
                
                if os.path.exists(firma_path_et): os.remove(firma_path_et)
                
                barra_et.progress(100, text="✅ Turno Entregado.")
                time.sleep(0.5); barra_et.empty(); st.success(f"Reporte de Entrega de Turno enviado exitosamente.")
                with open(archivo_pdf_et, "rb") as f: st.download_button("📥 Descargar Copia Local PDF", data=f.read(), file_name=archivo_pdf_et, mime="application/pdf")
            except Exception as e:
                barra_et.empty(); st.error(f"Error Técnico: {e}")

elif st.session_state.current_page == 'modulo_busqueda':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("Historial de Documentación y Descargas")
    st.divider()
    
    col_rol, col_modulo = st.columns(2)
    with col_rol: 
        idx_rol = 1 if st.session_state.current_user == 'admin' else 0
        rol_busqueda = st.radio("Seleccione Perfil de Búsqueda", ["Usuario Común", "Administrador"], index=idx_rol)
    with col_modulo: modulo_consulta = st.selectbox("Módulo a Consultar", ["HPT", "Reportes Diarios", "Entregas de Turno"])
    
    tabla_map = {"HPT": "hpt_history", "Reportes Diarios": "reportes_history", "Entregas de Turno": "entrega_history"}
    tabla_actual = tabla_map[modulo_consulta]
    registros_hist = []
    
    if rol_busqueda == "Administrador":
        admin_autorizado = st.session_state.admin_acceso_historial or st.session_state.current_user == 'admin'
        if not admin_autorizado:
            clave_ingresada = st.text_input("Ingrese Pin de Seguridad Administrador", type="password")
            if st.button("Ingresar"):
                if clave_ingresada == CLAVE_ADMIN: st.session_state.admin_acceso_historial = True; st.rerun()
                else: st.error("Código de seguridad incorrecto.")
        else:
            st.success("Acceso Gerencial Desbloqueado.")
            if st.session_state.current_user != 'admin':
                if st.button("Cerrar Vista Administrador"): st.session_state.admin_acceso_historial = False; st.rerun()
            try:
                res = supabase.table(tabla_actual).select('*').order('id', desc=True).execute()
                registros_hist = res.data
            except Exception:
                if modulo_consulta == "HPT": registros_hist = st.session_state.local_hpt_history
                elif modulo_consulta == "Reportes Diarios": registros_hist = st.session_state.local_reportes_history
                else: registros_hist = st.session_state.local_entrega_history
    else:
        user_actual = st.session_state.current_user
        st.info(f"Mostrando únicamente registros del Piloto: **{user_actual}**")
        try:
            res = supabase.table(tabla_actual).select('*').filter('usuario', 'eq', user_actual).order('id', desc=True).execute()
            registros_hist = res.data
        except Exception:
            if modulo_consulta == "HPT": registros_hist = [r for r in st.session_state.local_hpt_history if r['usuario'] == user_actual]
            elif modulo_consulta == "Reportes Diarios": registros_hist = [r for r in st.session_state.local_reportes_history if r['usuario'] == user_actual]
            else: registros_hist = [r for r in st.session_state.local_entrega_history if r['usuario'] == user_actual]

    if (rol_busqueda == "Usuario Común") or (rol_busqueda == "Administrador" and (st.session_state.admin_acceso_historial or st.session_state.current_user == 'admin')):
        if registros_hist:
            df = pd.DataFrame(registros_hist)
            if 'url_documento' in df.columns:
                df['url_documento'] = df['url_documento'].apply(lambda x: x if pd.notnull(x) and str(x).strip() != "" else None)
            
            if 'fecha' in df.columns:
                df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
                df['Año'] = df['fecha_dt'].dt.year.fillna(0).astype(int).astype(str).replace('0', 'Desc.')
                df['Mes'] = df['fecha_dt'].dt.month.fillna(0).astype(int).astype(str).replace('0', 'Desc.')
            else: df['Año'] = "Desc."; df['Mes'] = "Desc."

            df_filtro = df.copy()
            if rol_busqueda == "Administrador":
                st.markdown("### 🔍 Filtros de Búsqueda Avanzada")

                c_f1, c_f2, c_f3, c_f4, c_f5 = st.columns(5)
                with c_f1: filtro_op = st.selectbox("Operador", ["Todos"] + list(df['usuario'].dropna().unique())) if 'usuario' in df.columns else "Todos"
                with c_f2: filtro_cen = st.selectbox("Centro", ["Todos"] + list(df['centro'].dropna().unique())) if 'centro' in df.columns else "Todos"
                with c_f3: filtro_anio = st.selectbox("Año", ["Todos"] + list(df['Año'].unique()))
                with c_f4: filtro_mes = st.selectbox("Mes", ["Todos"] + list(df['Mes'].unique()))
                with c_f5:
                    if 'condicion_puerto' in df.columns:
                        filtro_puerto = st.selectbox("Condición Puerto", ["Todos", "Solo Puerto Cerrado Total"])
                    else:
                        filtro_puerto = "Todos"

                if filtro_op != "Todos": df_filtro = df_filtro[df_filtro['usuario'] == filtro_op]
                if filtro_cen != "Todos": df_filtro = df_filtro[df_filtro['centro'] == filtro_cen]
                if filtro_anio != "Todos": df_filtro = df_filtro[df_filtro['Año'] == filtro_anio]
                if filtro_mes != "Todos": df_filtro = df_filtro[df_filtro['Mes'] == filtro_mes]
                if filtro_puerto == "Solo Puerto Cerrado Total" and 'condicion_puerto' in df_filtro.columns:
                    df_filtro = df_filtro[df_filtro['condicion_puerto'] == 'Cerrado total']

            if modulo_consulta == "HPT": cols_mostrar = ['fecha', 'usuario', 'centro', 'area', 'ponton', 'condicion_puerto', 'url_documento']
            elif modulo_consulta == "Reportes Diarios": cols_mostrar = ['fecha', 'usuario', 'centro', 'area', 'jaula', 'tarea', 'url_documento']
            else: cols_mostrar = ['fecha', 'usuario', 'centro', 'area', 'tipo_reporte', 'url_documento']
            cols_mostrar = [c for c in cols_mostrar if c in df_filtro.columns]
            
            st.dataframe(df_filtro[cols_mostrar], column_config={"url_documento": st.column_config.LinkColumn("Enlace PDF", display_text="📥 Descargar PDF")}, use_container_width=True)

            if rol_busqueda == "Administrador":
                st.markdown("### 📦 Exportación Masiva")
                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    csv_export = df_filtro.to_csv(index=False).encode('utf-8')
                    st.download_button("📊 Exportar Tabla a Excel (CSV)", data=csv_export, file_name=f"historial_{modulo_consulta}.csv", mime="text/csv", use_container_width=True)
                with col_exp2:
                    if st.button("🗂️ Preparar ZIP con Documentos Filtrados", use_container_width=True):
                        with st.spinner("Descargando PDFs desde Supabase y comprimiendo... Esto tomará unos segundos."):
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                                for idx, row in df_filtro.iterrows():
                                    url = row.get('url_documento')
                                    if pd.notnull(url) and str(url).startswith('http'):
                                        try:
                                            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                                            with urllib.request.urlopen(req) as response:
                                                nombre_doc = f"Doc_{row.get('centro', 'Centro')}_{row.get('fecha', 'Fecha')}_{idx}.pdf".replace("/", "-").replace(" ", "_")
                                                zip_file.writestr(nombre_doc, response.read())
                                        except Exception: pass
                            st.session_state[f'zip_{modulo_consulta}'] = zip_buffer.getvalue()
                        
                    if f'zip_{modulo_consulta}' in st.session_state:
                        st.success("✅ Paquete ZIP listo para descargar.")
                        st.download_button("📥 Descargar Archivo ZIP", data=st.session_state[f'zip_{modulo_consulta}'], file_name=f"Documentos_{modulo_consulta}.zip", mime="application/zip", use_container_width=True)
        else:
            st.info(f"No se registran datos en el historial de {modulo_consulta}.")

elif st.session_state.current_page == 'panel_graficos':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.title("📈 Métricas e Inteligencia de Negocio")
    st.divider()
    
    admin_autorizado_graf = st.session_state.admin_acceso_graficos or st.session_state.current_user == 'admin'
    if not admin_autorizado_graf:
        clave_dash = st.text_input("Autenticación Gerencial (Pin)", type="password", key="dash_pin")
        if st.button("Ingresar"):
            if clave_dash == CLAVE_ADMIN: st.session_state.admin_acceso_graficos = True; st.rerun()
            else: st.error("Código inválido.")
    else:
        st.success("Acceso Gerencial Desbloqueado.")
        if st.session_state.current_user != 'admin':
            if st.button("Cerrar Vista Administrador"): st.session_state.admin_acceso_graficos = False; st.rerun()

        try:
            res_hpt = supabase.table('hpt_history').select('*').execute()
            df_hpt = pd.DataFrame(res_hpt.data)
        except:
            df_hpt = pd.DataFrame(st.session_state.local_hpt_history)
            
        if not df_hpt.empty:
            c_graf1, c_graf2 = st.columns(2)
            with c_graf1:
                st.subheader("📊 Operaciones por Centro")
                centro_counts = df_hpt['centro'].value_counts()
                st.bar_chart(centro_counts)
                
                st.subheader("⚠️ Puertos Cerrados por Área")
                df_cerrados = df_hpt[df_hpt['condicion_puerto'] != 'Abierto']
                if not df_cerrados.empty:
                    puertos_cerrados = df_cerrados['area'].value_counts()
                    st.bar_chart(puertos_cerrados, color="#ff4b4b")
                else: st.info("Fantástico: Ningún registro de puerto cerrado.")
            with c_graf2:
                st.subheader("🛠️ Top Faenas más Realizadas")
                if 'faena' in df_hpt.columns:
                    faena_counts = df_hpt['faena'].value_counts()
                    st.bar_chart(faena_counts, color="#00ff99")
                else: st.info("Sin registros de tipología de faenas.")
                
                st.subheader("💼 Distribución por Piloto ROV")
                piloto_counts = df_hpt['usuario'].value_counts()
                st.bar_chart(piloto_counts, color="#f5b841")
        else:
            st.info("No existen suficientes registros en Supabase para estructurar gráficos estadísticos.")
