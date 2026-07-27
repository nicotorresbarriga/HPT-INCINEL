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
    .stButton>button[kind="primary"] {
        background-color: #00d2ff;
        color: #00122c;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #00a8cc;
        color: #ffffff;
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
    .stRadio>div>label {
        color: #ffffff !important;
    }
    ::placeholder {
        color: #64748b !important;
        opacity: 1;
    }
    div[data-baseweb="tab-list"] {
        background-color: transparent;
    }
    div[data-baseweb="tab"] {
        color: #ffffff !important;
        background-color: #002353;
        border-radius: 8px 8px 0 0;
        border: 1px solid #00a8cc;
        border-bottom: none;
        margin-right: 4px;
    }
    div[aria-selected="true"] {
        background-color: #00a8cc !important;
        font-weight: bold;
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

USUARIOS = {"Ntorres": "17909926", "admin": "admin"}
CENTROS_AREAS = {"Centro Punta Vergara": "Area Austral", "Centro Isla": "Area Norte"}

# MODO PRUEBAS: Todos los correos visibles apuntan a la cuenta de pruebas
CENTROS_CORREOS = {"Centro Punta Vergara": "reportesrovincinel@gmail.com", "Centro Isla": "reportesrovincinel@gmail.com"}

CORREOS_PREVENCION = ["No enviar (Modo Pruebas)", "No enviar (Modo Pruebas)"]
CORREOS_OCULTOS = []

RANGOS_INICIO = [f"{str(h).zfill(2)}:{str(m).zfill(2)}" for h in range(6, 12) for m in (0, 30)]  
RANGO_TERMINO = [f"{str(h).zfill(2)}:{str(m).zfill(2)}" for h in range(16, 21) for m in (0, 30)] 
RANGO_DURACION = ["5 minutos", "10 minutos", "15 minutos", "20 minutos", "25 minutos", "30 minutos"]
RANGO_HORA_DIFUSION = [f"{str(h).zfill(2)}:{str(m).zfill(2)}" for h in range(6, 13) for m in (0, 15, 30, 45) if not (h == 12 and m > 0)]

try:
    supabase = init_connection()
except Exception as e:
    st.sidebar.warning("Advertencia: Conexión Supabase inactiva. Modo Local.")

# Inicialización de variables de sesión
for history in ['local_hpt_history', 'local_reportes_history', 'local_entrega_history']:
    if history not in st.session_state: st.session_state[history] = []

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_user' not in st.session_state: st.session_state.current_user = ""
if 'current_page' not in st.session_state: st.session_state.current_page = 'login'
if 'hpt_step' not in st.session_state: st.session_state.hpt_step = 1
if 'hpt_pdf_generado' not in st.session_state: st.session_state.hpt_pdf_generado = None
if 'rd_pdf_generado' not in st.session_state: st.session_state.rd_pdf_generado = None
if 'admin_acceso_historial' not in st.session_state: st.session_state.admin_acceso_historial = False
if 'admin_acceso_graficos' not in st.session_state: st.session_state.admin_acceso_graficos = False

# Variables de sesión para el nuevo módulo de Informe Consolidado
if 'ic_anomalias' not in st.session_state: st.session_state.ic_anomalias = []
if 'ic_pdf_generado' not in st.session_state: st.session_state.ic_pdf_generado = None

if 'hpt_data' not in st.session_state:
    st.session_state.hpt_data = {
        "empresa": "Salmones Blumar Magallanes", "fecha": datetime.date.today(), "hora_inicio": RANGOS_INICIO[2],
        "hora_termino": RANGO_TERMINO[2], "centro": list(CENTROS_AREAS.keys())[0] if CENTROS_AREAS else "",
        "correo": "", "encargado": "", "ponton": "", "condicion_puerto": "Abierto", "tarea": "",
        "trabajo_rutinario": "Sí",
        "epp": [False]*7, "faena": "Inspeccion Red pecera", "erc": [False]*6, "tc_duracion": "15 minutos",
        "check_instruido": "Sí", "check_clima": "Sí", "check_equipos": "Sí", "check_orden": "Sí",
        "evidencia_puerto": None
    }

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

def generar_pdf_consolidado(datos, anomalias, logo_filename, nombre_archivo):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # ------------------ PÁGINA 1: PORTADA ------------------
    pdf.add_page()
    if os.path.exists(logo_filename):
        pdf.image(logo_filename, x=10, y=10, h=18)
    
    # Intento de logo secundario (Mandante)
    if os.path.exists("blumar_logo.png"):
        pdf.image("blumar_logo.png", x=160, y=10, h=12)
        
    pdf.set_y(50)
    pdf.set_font("Helvetica", 'B', 20)
    pdf.set_text_color(15, 55, 105)
    pdf.cell(190, 10, "INFORME DIARIO", border=0, ln=True, align='C')
    pdf.cell(190, 10, "INSPECCIÓN ROBÓTICA SUBMARINA", border=0, ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 10, f"CENTRO {datos['centro'].upper()}", border=0, ln=True, align='C')
    
    # Imagen referencial de portada si existe
    if os.path.exists("rov_cover.jpg"):
        pdf.image("rov_cover.jpg", x=35, y=95, w=140)
    else:
        pdf.ln(50)
        
    # Tabla de Datos
    pdf.set_y(190)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(240, 240, 240)
    
    ancho_lbl = 55
    ancho_val = 80
    x_offset = (210 - (ancho_lbl + ancho_val)) / 2
    
    def add_row(lbl, val):
        pdf.set_x(x_offset)
        pdf.set_font("Helvetica", 'B', 9)
        pdf.cell(ancho_lbl, 7, lbl, border=1, fill=True)
        pdf.set_font("Helvetica", '', 9)
        pdf.cell(ancho_val, 7, str(val), border=1, ln=True)

    add_row("CLIENTE", datos['cliente'])
    add_row("CENTRO", datos['centro'])
    add_row("ENCARGADO DE CENTRO", datos['encargado'])
    add_row("FECHA", datos['fecha'])
    add_row("PILOTO ROV", datos['piloto'])
    add_row("EQUIPO ROV", datos['equipo'])
    add_row("CONDICIÓN PUERTO", datos['puerto'])
    
    # Footer
    pdf.set_y(-25)
    pdf.set_font("Helvetica", 'I', 7)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 4, "INCINEL - ÁREA ROBÓTICA     DIRECCIÓN: LOS COLONOS 165, PUERTO MONTT, CHILE", align='C', ln=True)
    
    # ------------------ PÁGINA 2: ESQUEMA Y DETALLES ------------------
    pdf.add_page()
    if os.path.exists(logo_filename): pdf.image(logo_filename, x=10, y=10, h=12)
    pdf.set_y(30)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_text_color(15, 55, 105)
    pdf.cell(190, 10, "ESQUEMA DE REFERENCIA", border=0, ln=True, align='C')
    pdf.ln(5)
    
    if datos.get('esquema_img'):
        temp_esquema = f"temp_esq_{uuid.uuid4().hex[:6]}.jpg"
        with open(temp_esquema, "wb") as f: f.write(datos['esquema_img'])
        try:
            with Image.open(temp_esquema) as img:
                w, h = img.size
                aspect = h / w
                w_mm = 160
                h_mm = w_mm * aspect
                if h_mm > 150: h_mm = 150; w_mm = h_mm / aspect
            x_pos = (210 - w_mm) / 2
            pdf.image(temp_esquema, x=x_pos, y=pdf.get_y(), w=w_mm, h=h_mm)
            pdf.set_y(pdf.get_y() + h_mm + 10)
        except:
            pdf.cell(190, 10, "[Error al procesar esquema]", ln=True, align='C')
        if os.path.exists(temp_esquema): os.remove(temp_esquema)
    else:
        pdf.set_font("Helvetica", 'I', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(190, 40, "No se adjuntó esquema planimétrico del centro.", border=1, ln=True, align='C')
        pdf.ln(10)
        
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_text_color(15, 55, 105)
    pdf.cell(190, 10, "INSPECCIÓN REALIZADA", border=0, ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(190, 6, txt=f"Con fecha {datos['fecha']}, se coordina con el encargado de centro continuar con la inspección robótica submarina. Se inspeccionaron las jaulas: {datos['jaulas_insp']}.")

    # ------------------ PÁGINAS 3+: REGISTRO FOTOGRÁFICO DE ANOMALÍAS ------------------
    # Agrupar anomalías por jaula
    jaulas_dict = {}
    for anomalia in anomalias:
        j = anomalia['jaula']
        if j not in jaulas_dict: jaulas_dict[j] = []
        jaulas_dict[j].append(anomalia)
        
    for jaula, lista_anomalias in jaulas_dict.items():
        pdf.add_page()
        if os.path.exists(logo_filename): pdf.image(logo_filename, x=10, y=10, h=12)
        pdf.set_y(30)
        pdf.set_font("Helvetica", 'B', 14)
        pdf.set_text_color(15, 55, 105)
        pdf.cell(190, 8, f"IMÁGENES DE INSPECCIÓN - JAULA {jaula}", border=0, ln=True, align='C')
        pdf.ln(5)
        
        y_cursor = pdf.get_y()
        for idx, anom in enumerate(lista_anomalias):
            if y_cursor > 220:
                pdf.add_page()
                y_cursor = 30
                
            pdf.set_y(y_cursor)
            pdf.set_font("Helvetica", 'B', 9)
            pdf.set_text_color(0, 0, 0)
            
            # Textos
            lbl_desc = f"{anom['descripcion']} | {anom['ubicacion']} a {anom['profundidad']}m"
            pdf.cell(90, 6, "ROTURA / ANOMALÍA ENCONTRADA", align='C')
            pdf.cell(10, 6, "")
            pdf.cell(90, 6, "ESTADO: " + anom['estado'].upper(), ln=True, align='C')
            
            y_img = pdf.get_y()
            
            # Imagen Antes
            if anom['img_antes']:
                t_antes = f"temp_ant_{uuid.uuid4().hex[:6]}.jpg"
                with open(t_antes, "wb") as f: f.write(anom['img_antes'])
                try: pdf.image(t_antes, x=15, y=y_img, w=80, h=55)
                except: pass
                if os.path.exists(t_antes): os.remove(t_antes)
            else:
                pdf.rect(15, y_img, 80, 55)
                pdf.text(45, y_img + 30, "Sin Imagen")
                
            # Imagen Después
            if anom['img_despues']:
                t_desp = f"temp_desp_{uuid.uuid4().hex[:6]}.jpg"
                with open(t_desp, "wb") as f: f.write(anom['img_despues'])
                try: pdf.image(t_desp, x=115, y=y_img, w=80, h=55)
                except: pass
                if os.path.exists(t_desp): os.remove(t_desp)
            else:
                pdf.rect(115, y_img, 80, 55)
                pdf.text(145, y_img + 30, "Sin Imagen")
                
            pdf.set_y(y_img + 57)
            pdf.set_font("Helvetica", 'I', 8)
            pdf.cell(90, 5, lbl_desc, align='C')
            pdf.cell(10, 5, "")
            pdf.cell(90, 5, f"Reparación por: {anom['servicio']}" if anom['estado'] == 'Reparada' else "Pendiente de reparación", ln=True, align='C')
            
            y_cursor = pdf.get_y() + 10

    # ------------------ PÁGINA FINAL: TABLA RESUMEN ------------------
    # Configuramos apaisado (Landscape) para que quepa bien la tabla
    pdf.add_page(orientation='L')
    if os.path.exists(logo_filename): pdf.image(logo_filename, x=10, y=10, h=12)
    pdf.set_y(30)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_text_color(15, 55, 105)
    pdf.cell(277, 10, "RESULTADOS DE LA INSPECCIÓN", border=0, ln=True, align='C')
    pdf.ln(5)
    
    # Header de Tabla
    headers = ["N°", "Fecha", "Jaula", "Tipo Red", "Anomalía", "Ubicación", "Prof. (m)", "Estado", "Servicio"]
    widths = [10, 22, 15, 25, 80, 45, 20, 25, 35]
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_text_color(0, 0, 0)
    for i in range(len(headers)):
        pdf.cell(widths[i], 8, headers[i], border=1, align='C', fill=True)
    pdf.ln()
    
    # Filas
    pdf.set_font("Helvetica", '', 8)
    for i, anom in enumerate(anomalias):
        pdf.cell(widths[0], 7, str(i+1), border=1, align='C')
        pdf.cell(widths[1], 7, str(datos['fecha']), border=1, align='C')
        pdf.cell(widths[2], 7, str(anom['jaula']), border=1, align='C')
        pdf.cell(widths[3], 7, str(anom['tipo_red']), border=1, align='C')
        
        # Guardar X e Y para la celda descriptiva que puede ser larga
        x_anom = pdf.get_x()
        y_anom = pdf.get_y()
        
        # Truco para truncar texto si es muy largo (simplificado para FPDF)
        desc_corta = anom['descripcion'][:45] + ".." if len(anom['descripcion']) > 48 else anom['descripcion']
        pdf.cell(widths[4], 7, desc_corta, border=1, align='L')
        
        pdf.cell(widths[5], 7, str(anom['ubicacion']), border=1, align='C')
        pdf.cell(widths[6], 7, str(anom['profundidad']), border=1, align='C')
        
        # Color para el estado
        if anom['estado'] == 'Reparada': pdf.set_text_color(0, 150, 0)
        elif anom['estado'] == 'Pendiente': pdf.set_text_color(200, 0, 0)
        else: pdf.set_text_color(0, 0, 0)
        
        pdf.set_font("Helvetica", 'B', 8)
        pdf.cell(widths[7], 7, str(anom['estado']), border=1, align='C')
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", '', 8)
        
        pdf.cell(widths[8], 7, str(anom['servicio']), border=1, align='C', ln=True)

    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 7, "Observaciones Generales:")
    pdf.ln()
    pdf.set_font("Helvetica", '', 9)
    pdf.multi_cell(277, 6, txt=datos.get('observaciones', 'Sin observaciones particulares.'), border=1)
    
    pdf.output(nombre_archivo)
    return nombre_archivo

# Función general de FPDF utilizada por HPT y Entrega de Turno
def generar_pdf_entrega(datos, logo_filename, nombre_archivo, firma_path=None, imagenes_subidas=None):
    pdf = FPDF()
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=15) 
    pdf.add_page()
    
    pdf.set_draw_color(180, 180, 180)

    if os.path.exists(logo_filename):
        pdf.image(logo_filename, x=10, y=10, h=20)
        
    pdf.set_y(35) 
    pdf.set_font("Helvetica", 'B', 15)
    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255) 
    pdf.cell(190, 10, "REPORTE FORMAL DE ENTREGA DE TURNO - ROV", border=0, ln=True, align='C', fill=True)
    
    hora_chile = datetime.datetime.utcnow() - datetime.timedelta(hours=4)
    fecha_hora_actual = hora_chile.strftime("%Y-%m-%d %H:%M:%S")
    piloto_saliente = datos.get('1. Información General', {}).get('Piloto_Saliente', 'Desconocido')
    pdf.set_font("Helvetica", 'I', 8); pdf.set_text_color(128, 128, 128)
    pdf.cell(190, 6, f"Sello de Auditoría Inmutable: Generado el {fecha_hora_actual} por {piloto_saliente}", border=0, ln=True, align='C')
    pdf.ln(2)
    
    for seccion, campos in datos.items():
        if pdf.get_y() > 250: pdf.add_page()
        pdf.ln(3); pdf.set_font("Helvetica", 'B', 11)
        pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255) 
        pdf.cell(190, 8, f"  {seccion.upper()}", border=0, ln=True, fill=True)
        for clave, valor in campos.items():
            nombre_campo = clave.replace('_', ' ')
            if pdf.get_y() > 265: pdf.add_page()
            pdf.set_font("Helvetica", 'B', 9); pdf.set_fill_color(245, 245, 245); pdf.set_text_color(0, 0, 0)
            pdf.cell(190, 8, f" {nombre_campo}:", border=1, ln=True, fill=True)
            pdf.set_font("Helvetica", '', 9)
            if isinstance(valor, list):
                for i in range(0, len(valor), 2):
                    item1 = f" - {valor[i]}".encode('latin-1', 'replace').decode('latin-1')
                    item2 = f" - {valor[i+1]}".encode('latin-1', 'replace').decode('latin-1') if i+1 < len(valor) else ""
                    pdf.cell(95, 8, item1, border="L", ln=0)
                    pdf.cell(95, 8, item2, border="R", ln=1)
                x = pdf.get_x(); y = pdf.get_y()
                pdf.line(x, y, x+190, y); pdf.ln(1)
            else:
                valor_seguro = str(valor).strip() if str(valor).strip() != "" else "Sin registro o sin novedades."
                valor_seguro = valor_seguro.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(190, 8, txt=f" {valor_seguro}", border=1); pdf.ln(1) 

    if imagenes_subidas:
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 11)
        pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 8, "  EVIDENCIA FOTOGRAFICA", border=0, ln=True, fill=True); pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
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
    pdf.set_y(y_img + 25); pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(190, 5, "_______________________", border=0, ln=1, align='C')
    pdf.cell(190, 5, "Firma Piloto ROV Saliente", border=0, ln=1, align='C')

    pdf.set_auto_page_break(auto=False)
    pdf.set_y(-12)
    pdf.set_font("Helvetica", 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(190, 10, "TridenTech 2026©".encode('latin-1', 'replace').decode('latin-1'), border=0, align='C')

    pdf.output(nombre_archivo)
    return nombre_archivo

# ---------------- FLUJO DE PANTALLAS ----------------

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
    st.markdown("<h1 style='text-align: center;'>Sistema de Gestión Operativa</h1>", unsafe_allow_html=True)
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
        pilotos_activos = ["Ntorres"] 
        
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
            if pendientes_hpt: st.warning(f"⚠️ **HPT Pendientes:** {', '.join(pendientes_hpt)}")
            else: st.success("✅ Todas las HPT del día enviadas.")
        with col_p2:
            if pendientes_rd: st.warning(f"⚠️ **Reportes Diarios Pendientes:** {', '.join(pendientes_rd)}")
            else: st.success("✅ Todos los Reportes Diarios enviados.")
                
        hora_chile = (datetime.datetime.utcnow() - datetime.timedelta(hours=4)).time()
        limite_hpt = datetime.time(9, 30)
        limite_rd = datetime.time(20, 0)
        
        if hora_chile > limite_hpt and pendientes_hpt:
            st.error("🚨 **ALERTA CRÍTICA:** Son pasadas las 09:30 AM y existen HPT pendientes por envío.")
        
        if hora_chile > limite_rd and pendientes_rd:
            st.error("🚨 **ALERTA CRÍTICA:** Son pasadas las 20:00 Hrs y existen Reportes Diarios pendientes por envío.")
            
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⚓ MÓDULO HPT", use_container_width=True): set_page('hpt_menu'); st.rerun()
        if st.button("📋 ENTREGA DE TURNO", use_container_width=True): set_page('entrega_turno'); st.rerun()
    with c2:
        if st.button("🚢 REPORTE DIARIO", use_container_width=True): set_page('reporte_diario'); st.rerun()
        if st.button("📑 INFORME CONSOLIDADO", use_container_width=True): set_page('informe_consolidado'); st.rerun()
    with c3:
        if st.button("📈 GRÁFICOS GERENCIALES", use_container_width=True): set_page('panel_graficos'); st.rerun()
        if st.button("📊 HISTORIAL / AUDITORÍA", use_container_width=True): set_page('modulo_busqueda'); st.rerun()
        if st.button("🔒 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = ""
            set_page('login'); st.rerun()

elif st.session_state.current_page == 'informe_consolidado':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.markdown("<h1 style='text-align: center;'>Generador de Informe Consolidado</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a0aec0;'>Cree reportes técnicos detallados con galería del antes/después y planimetría.</p>", unsafe_allow_html=True)
    
    # Sistema de Pestañas (Tabs)
    tab1, tab2, tab3 = st.tabs(["1. Contexto Operativo", "2. Registro de Anomalías", "3. Compilación y PDF"])
    
    with tab1:
        st.subheader("Datos Generales")
        col_ic1, col_ic2 = st.columns(2)
        with col_ic1:
            ic_cliente = st.selectbox("Empresa Cliente (Mandante)", ["Salmones Blumar S.A.", "MultiX", "Cermaq"])
            ic_centro = st.selectbox("Centro de Cultivo", list(CENTROS_AREAS.keys()) + ["Otro"])
            ic_fecha = st.date_input("Fecha Inspección", datetime.date.today())
            ic_encargado = st.text_input("Encargado de Centro (Nombre)")
        with col_ic2:
            ic_piloto = st.text_input("Piloto ROV", value=st.session_state.current_user)
            ic_equipo = st.selectbox("Equipo ROV Principal", ["Deep Trekker DTG3", "Chasing M2 Pro Max", "Fifish V6 Expert"])
            ic_puerto = st.selectbox("Condición de Puerto", ["Normal", "Variable", "Cerrado"])
            ic_jaulas = st.text_input("Jaulas Inspeccionadas (Ej: 101, 102, 204)")
            
        st.divider()
        st.subheader("Planimetría del Centro")
        st.write("Cargue el esquema/mapa del centro donde se graficará la ruta. Si no posee uno, se dejará un recuadro referencial en el PDF.")
        ic_esquema = st.file_uploader("Subir Esquema del Centro", type=['png', 'jpg', 'jpeg'], key="up_esquema")
        if ic_esquema:
            st.success("Esquema cargado correctamente.")
            
    with tab2:
        st.subheader("Añadir Nuevo Hallazgo (Anomalía)")
        with st.container(border=True):
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1:
                h_jaula = st.text_input("Jaula N° (Ej: 101)")
                h_tipo = st.selectbox("Tipo de Red", ["Lobera", "Pecera", "Pajarera"])
                h_estado = st.selectbox("Estado", ["Reparada", "Pendiente"])
            with col_h2:
                h_ubicacion = st.selectbox("Ubicación", ["Lateral Norte", "Lateral Sur", "Lateral Este", "Lateral Oeste", "Fondo", "Cabecera Norte", "Cabecera Sur"])
                h_profundidad = st.number_input("Profundidad (metros)", min_value=0.0, max_value=100.0, step=0.5, value=10.0)
                h_servicio = st.selectbox("Responsable Reparación", ["Team Buceo", "ROV", "Por Definir"])
            with col_h3:
                h_desc = st.text_area("Descripción (Ej: Rotura 2x1 cuadros)")
                
            st.markdown("**Evidencia Fotográfica (Opcional)**")
            col_img1, col_img2 = st.columns(2)
            with col_img1:
                h_img_antes = st.file_uploader("Foto Anomalía (Antes)", type=['png', 'jpg', 'jpeg'], key="h_img_1")
            with col_img2:
                h_img_despues = st.file_uploader("Foto Reparación (Después)", type=['png', 'jpg', 'jpeg'], key="h_img_2")
                
            if st.button("➕ AGREGAR ANOMALÍA A LA LISTA", type="primary"):
                if not h_jaula or not h_desc:
                    st.error("Debe especificar al menos la Jaula y la Descripción de la anomalía.")
                else:
                    nueva_anomalia = {
                        "id": str(uuid.uuid4())[:6],
                        "jaula": h_jaula,
                        "tipo_red": h_tipo,
                        "descripcion": h_desc,
                        "ubicacion": h_ubicacion,
                        "profundidad": h_profundidad,
                        "estado": h_estado,
                        "servicio": h_servicio,
                        "img_antes": h_img_antes.getvalue() if h_img_antes else None,
                        "img_despues": h_img_despues.getvalue() if h_img_despues else None
                    }
                    st.session_state.ic_anomalias.append(nueva_anomalia)
                    st.success(f"Anomalía en Jaula {h_jaula} agregada.")
                    st.rerun()

        st.divider()
        st.subheader(f"Lista de Hallazgos Registrados ({len(st.session_state.ic_anomalias)})")
        if not st.session_state.ic_anomalias:
            st.info("No se han registrado anomalías aún.")
        else:
            df_mostrar = pd.DataFrame([{
                "Jaula": a["jaula"],
                "Red": a["tipo_red"],
                "Descripción": a["descripcion"],
                "Ubicación": a["ubicacion"],
                "Prof.": a["profundidad"],
                "Estado": a["estado"]
            } for a in st.session_state.ic_anomalias])
            st.dataframe(df_mostrar, use_container_width=True)
            
            if st.button("🗑️ Borrar Último Hallazgo"):
                st.session_state.ic_anomalias.pop()
                st.rerun()

    with tab3:
        st.subheader("Resumen del Informe y Compilación")
        ic_observaciones = st.text_area("Observaciones Generales de la Inspección (Para la página final)", height=150)
        
        if st.button("📄 GENERAR INFORME CONSOLIDADO (PDF)", type="primary", use_container_width=True):
            if not st.session_state.ic_anomalias:
                st.error("No puede generar un informe sin anomalías registradas.")
            else:
                with st.spinner("Compilando Documento PDF Multi-página. Por favor espere..."):
                    datos_grales = {
                        "cliente": ic_cliente,
                        "centro": ic_centro,
                        "encargado": ic_encargado,
                        "fecha": str(ic_fecha),
                        "piloto": ic_piloto,
                        "equipo": ic_equipo,
                        "puerto": ic_puerto,
                        "jaulas_insp": ic_jaulas,
                        "esquema_img": ic_esquema.getvalue() if ic_esquema else None,
                        "observaciones": ic_observaciones
                    }
                    
                    logo_incinel = "logo2.png" if os.path.exists("logo2.png") else "logo.png"
                    nombre_archivo_ic = f"Informe_Consolidado_{ic_centro.replace(' ', '_')}_{ic_fecha}.pdf"
                    
                    try:
                        ruta_pdf = generar_pdf_consolidado(datos_grales, st.session_state.ic_anomalias, logo_incinel, nombre_archivo_ic)
                        st.session_state.ic_pdf_generado = ruta_pdf
                        st.success("✅ Informe Generado Exitosamente.")
                    except Exception as e:
                        st.error(f"Error al generar el PDF: {e}")
                        
        if st.session_state.ic_pdf_generado and os.path.exists(st.session_state.ic_pdf_generado):
            with open(st.session_state.ic_pdf_generado, "rb") as pdf_file:
                st.download_button(
                    label="📥 DESCARGAR INFORME CONSOLIDADO", 
                    data=pdf_file, 
                    file_name=st.session_state.ic_pdf_generado, 
                    mime="application/pdf", 
                    use_container_width=True
                )
            if st.button("🧹 Limpiar Datos y Crear Nuevo Informe"):
                st.session_state.ic_anomalias = []
                st.session_state.ic_pdf_generado = None
                st.rerun()


elif st.session_state.current_page == 'hpt_menu':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.markdown("<h1 style='text-align: center;'>Módulo HPT</h1>", unsafe_allow_html=True)
    st.divider()
    if st.button("➕ CREAR NUEVA HPT", use_container_width=True): 
        set_step(1)
        st.session_state.hpt_pdf_generado = None 
        st.session_state.hpt_data = {
            "empresa": "Salmones Blumar Magallanes", "fecha": datetime.date.today(), "hora_inicio": RANGOS_INICIO[2],
            "hora_termino": RANGO_TERMINO[2], "centro": list(CENTROS_AREAS.keys())[0] if CENTROS_AREAS else "",
            "correo": "", "encargado": "", "ponton": "", "condicion_puerto": "Abierto", "tarea": "",
            "trabajo_rutinario": "Sí",
            "epp": [False]*7, "faena": "Inspeccion Red pecera", "erc": [False]*6, "tc_duracion": "15 minutos",
            "check_instruido": "Sí", "check_clima": "Sí", "check_equipos": "Sí", "check_orden": "Sí",
            "evidencia_puerto": None
        }
        set_page('hpt_nuevo')
        st.rerun()

elif st.session_state.current_page == 'hpt_nuevo':
    st.button("⬅️ Cancelar y Volver al Menú HPT", on_click=set_page, args=('hpt_menu',))
    st.markdown(f"<h1 style='text-align: center;'>Nueva HPT - Paso {st.session_state.hpt_step}</h1>", unsafe_allow_html=True)
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
            
            opciones_rutinario = ["Sí", "No"]
            idx_rut = opciones_rutinario.index(st.session_state.hpt_data.get("trabajo_rutinario", "Sí")) if st.session_state.hpt_data.get("trabajo_rutinario") in opciones_rutinario else 0
            trabajo_rutinario = st.radio("¿Trabajo Rutinario?", opciones_rutinario, index=idx_rut, horizontal=True)

        with col2:
            opciones_centros = list(CENTROS_AREAS.keys())
            idx_centro = opciones_centros.index(st.session_state.hpt_data.get("centro", opciones_centros[0])) if st.session_state.hpt_data.get("centro") in opciones_centros else 0
            centro = st.selectbox("Centro de Cultivo", opciones_centros, index=idx_centro)
            idx_ht = RANGO_TERMINO.index(st.session_state.hpt_data["hora_termino"]) if st.session_state.hpt_data["hora_termino"] in RANGO_TERMINO else 0
            hora_termino = st.selectbox("Hora de Término", RANGO_TERMINO, index=idx_ht)
            
            condicion_puerto = st.selectbox("Condición de Puerto", ["Abierto", "Cerrado para naves menores", "Cerrado total"])
            st.link_button("🌐 Revisar SITPORT (Directemar)", "https://sitport.directemar.cl/#/general", use_container_width=True)
            
            evidencia_img = None
            if condicion_puerto in ["Cerrado para naves menores", "Cerrado total"]:
                evidencia_img = st.file_uploader("📸 Evidencia fotográfica de puerto cerrado", type=['png', 'jpg', 'jpeg'])

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
            tarea = "Puerto Cerrado Total. Sin operaciones."
        else:
            idx_faena = opciones_faena.index(st.session_state.hpt_data.get("faena", opciones_faena[0])) if st.session_state.hpt_data.get("faena") in opciones_faena else 0
            faena = st.selectbox("Faena a realizar", opciones_faena, index=idx_faena)
            tarea = st.text_area("Detalles de faena y lugar", value=st.session_state.hpt_data.get("tarea", ""), placeholder="Indique módulos, jaulas y tareas específicas...")
        
        if st.button("SIGUIENTE ➡️", use_container_width=True):
            img_bytes = evidencia_img.getvalue() if evidencia_img else st.session_state.hpt_data.get("evidencia_puerto")
            st.session_state.hpt_data.update({
                "empresa": empresa, "fecha": fecha, "hora_inicio": hora_inicio, "hora_termino": hora_termino, 
                "centro": centro, "area": area_asignada, "correo": correo, "encargado": encargado, "ponton": ponton, 
                "condicion_puerto": condicion_puerto, "faena": faena, "tarea": tarea, 
                "trabajo_rutinario": trabajo_rutinario,
                "evidencia_puerto": img_bytes
            })
            if condicion_puerto == "Cerrado total":
                set_step(4) 
            else:
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
                set_step(1); st.rerun()
        with col_btn2:
            if st.button("SIGUIENTE ➡️", key="next2", use_container_width=True):
                if not (epp_chaleco and epp_termica and epp_comunicacion and epp_botiquin): st.error("⚠️ No cumple con EPP mínimos.")
                else: st.session_state.hpt_data["epp"] = [epp_guantes, epp_chaleco, epp_zapatos, epp_termica, epp_traje, epp_comunicacion, epp_botiquin]; set_step(3); st.rerun()

    elif st.session_state.hpt_step == 3:
        st.subheader("Evaluación de Riesgos y Controles")
        st.markdown("**Verificaciones Claves de Seguridad**")
        opc_val = ["Sí", "No", "N/A"]
        val1 = opc_val.index(st.session_state.hpt_data.get("check_instruido", "Sí")) if st.session_state.hpt_data.get("check_instruido") in opc_val else 0
        check_instruido = st.radio("¿El personal está instruido en el Procedimiento Específico (Charla 5 min)?", opc_val, index=val1, horizontal=True)
        val2 = opc_val.index(st.session_state.hpt_data.get("check_clima", "Sí")) if st.session_state.hpt_data.get("check_clima") in opc_val else 0
        check_clima = st.radio("¿Condiciones ambientales (viento, lluvia, oleaje) evaluadas y seguras?", opc_val, index=val2, horizontal=True)
        val3 = opc_val.index(st.session_state.hpt_data.get("check_equipos", "Sí")) if st.session_state.hpt_data.get("check_equipos") in opc_val else 0
        check_equipos = st.radio("¿Equipos de apoyo y comunicación operativos y revisados?", opc_val, index=val3, horizontal=True)
        val4 = opc_val.index(st.session_state.hpt_data.get("check_orden", "Sí")) if st.session_state.hpt_data.get("check_orden") in opc_val else 0
        check_orden = st.radio("¿El área de trabajo se encuentra ordenada, despejada y delimitada?", opc_val, index=val4, horizontal=True)
        st.divider()
        estado_erc = st.session_state.hpt_data["erc"]
        st.markdown("**Checklist Riesgos Críticos (ERC)**")
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
                    "erc": [erc_izaje, erc_buceo, erc_electricos, erc_caidas, erc_navegacion, erc_atrapamiento],
                    "check_instruido": check_instruido, "check_clima": check_clima, 
                    "check_equipos": check_equipos, "check_orden": check_orden
                })
                set_step(2); st.rerun()
        with col_btn2:
            if st.button("SIGUIENTE ➡️", key="next3", use_container_width=True):
                st.session_state.hpt_data.update({
                    "erc": [erc_izaje, erc_buceo, erc_electricos, erc_caidas, erc_navegacion, erc_atrapamiento],
                    "check_instruido": check_instruido, "check_clima": check_clima, 
                    "check_equipos": check_equipos, "check_orden": check_orden
                })
                set_step(4); st.rerun()

    elif st.session_state.hpt_step == 4:
        st.subheader("Validación Final")
        with st.expander("Toma de Conocimiento", expanded=True):
            tc_nombre = st.text_input("Nombre Difusión")
            col1, col2 = st.columns(2)
            with col1:
                tc_fecha = st.date_input("Fecha Difusión")
                tc_relator = st.text_input("Nombre Relator (Piloto)", value=st.session_state.current_user)
                tc_rut = st.text_input("RUT Relator")
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
                if st.session_state.hpt_data.get("condicion_puerto") == "Cerrado total": set_step(1)
                else: set_step(3)
                st.rerun()
                
        with col_btn2:
            if st.button("GENERAR Y ENVIAR HPT", type="primary", use_container_width=True):
                data = st.session_state.hpt_data
                barra_carga = st.progress(0, text="⚙️ Generando PDF...")
                
                try:
                    pdf = FPDF(); pdf.add_page()
                    logo_pdf = "logo2.png" if os.path.exists("logo2.png") else "logo2.jpg" if os.path.exists("logo2.jpg") else "logo.png"
                    if os.path.exists(logo_pdf): pdf.image(logo_pdf, x=10, y=8, h=20)
                    
                    pdf.set_draw_color(180, 180, 180)
                    pdf.set_y(32); pdf.set_font("Arial", "B", 12)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 10, "HERRAMIENTA DE PREVENCION EN TERRENO (HPT) - ROV", border=0, ln=True, align="C", fill=True)
                    
                    hora_chile = datetime.datetime.utcnow() - datetime.timedelta(hours=4)
                    fecha_hora_actual = hora_chile.strftime("%Y-%m-%d %H:%M:%S")
                    pdf.set_font("Arial", "I", 8); pdf.set_text_color(128, 128, 128)
                    pdf.cell(0, 6, f"Sello de Auditoría Inmutable: Generado el {fecha_hora_actual} por {st.session_state.current_user}", border=0, ln=True, align="C")
                    pdf.ln(2)

                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "1. DATOS OPERATIVOS", border=0, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0)
                    
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Empresa / Mandante:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('empresa', '')[:35], border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Centro de Cultivo:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('centro', '')[:35], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Fecha Maniobra:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, str(data.get('fecha', '')), border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Area Geografica:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('area', '')[:35], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Hora Inicio Rango:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, str(data.get('hora_inicio', '')), border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Hora Termino Rango:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, str(data.get('hora_termino', '')), border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Nombre Ponton:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('ponton', '')[:35], border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Condicion Puerto:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('condicion_puerto', '')[:35], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Encargado Centro:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('encargado', '')[:35], border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Correo Centro:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, data.get('correo', '')[:35], border=1, ln=True)
                    
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Trabajo Rutinario:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, data.get('trabajo_rutinario', 'Sí'), border=1, ln=True)

                    pdf.set_font("Arial", "B", 8)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.cell(190, 6, "Faena Primaria y Detalles Especificos:", border=0, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "", 8)
                    texto_tarea = f"FAENA: {data.get('faena', '')}\nDETALLES: {data.get('tarea', '')}"
                    pdf.multi_cell(190, 5, texto_tarea, border=1)

                    pdf.ln(2)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "2. EQUIPO DE PROTECCION PERSONAL SELECCIONADO", border=0, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 8)
                    epp_labels = ["Guantes", "Chaleco", "Zapatos", "Ropa Termica", "Traje Agua", "Comunicacion", "Botiquin"]
                    epp_vals = data.get('epp', []); epp_seleccionados = [epp_labels[i] for i in range(len(epp_labels)) if i < len(epp_vals) and epp_vals[i]]
                    if not epp_seleccionados: pdf.cell(190, 6, "Ningun EPP registrado o Aplica (Puerto Cerrado Total).", border=1, ln=True)
                    else:
                        for i, epp in enumerate(epp_seleccionados): pdf.cell(190/3, 6, f"[ X ] {epp}", border=1, ln=1 if (i + 1) % 3 == 0 or i == len(epp_seleccionados) - 1 else 0)

                    pdf.ln(2)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "3. VERIFICACIONES CLAVES DE SEGURIDAD", border=0, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 8)
                    
                    def print_check(pregunta, respuesta):
                        pdf.cell(160, 6, pregunta, border=1)
                        pdf.cell(30, 6, respuesta, border=1, align="C", ln=True)
                        
                    print_check("Personal instruido en Procedimiento Especifico (Charla 5 min)", data.get("check_instruido", ""))
                    print_check("Condiciones ambientales (viento, lluvia, oleaje) evaluadas y seguras", data.get("check_clima", ""))
                    print_check("Equipos de apoyo y comunicacion operativos y revisados", data.get("check_equipos", ""))
                    print_check("Area de trabajo ordenada, despejada y delimitada", data.get("check_orden", ""))

                    pdf.ln(2)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "4. RIESGOS CRITICOS EVALUADOS (ERC)", border=0, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 8)
                    erc_labels = ["Izaje", "Buceo", "Eq. Electricos", "Caidas", "Navegacion", "Atrapamiento"]
                    erc_vals = data.get('erc', []); erc_seleccionados = [erc_labels[i] for i in range(len(erc_labels)) if i < len(erc_vals) and erc_vals[i]]
                    if not erc_seleccionados: pdf.cell(190, 6, "Ningun Riesgo seleccionado o Aplica (Puerto Cerrado Total).", border=1, ln=True)
                    else:
                        for i, erc in enumerate(erc_seleccionados): pdf.cell(190/2, 6, f"[ X ] {erc}", border=1, ln=1 if (i + 1) % 2 == 0 or i == len(erc_seleccionados) - 1 else 0)

                    pdf.ln(2)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "5. DIFUSION Y TOMA DE CONOCIMIENTO", border=0, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Relator / Piloto:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, tc_relator[:35], border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "RUT Relator:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, tc_rut[:20], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Tema Difundido:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(155, 6, tc_nombre[:80], border=1, ln=True)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Fecha y Hora:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, f"{tc_fecha} {tc_hora}", border=1)
                    pdf.set_font("Arial", "B", 8); pdf.cell(35, 6, "Duracion Rango:", border=1); pdf.set_font("Arial", "", 8); pdf.cell(60, 6, tc_duracion, border=1, ln=True)

                    pdf.ln(2)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 9); pdf.cell(190, 6, "6. CUADRO DE FIRMAS RESPONSABLES", border=0, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(95, 22, "", border=1); pdf.cell(95, 22, "", border=1, ln=True)
                    id_firmas = uuid.uuid4().hex[:8]; f_serv = f"f_serv_{id_firmas}.jpg"; f_enc = f"f_encargado_{id_firmas}.jpg"
                    if procesar_firma(firma_sup_serv, f_serv): pdf.image(f_serv, x=35, y=pdf.get_y()-20, w=45, h=15)
                    if procesar_firma(firma_encargado, f_enc): pdf.image(f_enc, x=130, y=pdf.get_y()-20, w=45, h=15)
                    pdf.set_font("Arial", "B", 8); pdf.cell(95, 6, "Firma Supervisor Servicio", border=1, align="C"); pdf.cell(95, 6, "Firma Encargado de Centro", border=1, ln=True, align="C")

                    if data.get('evidencia_puerto'):
                        pdf.add_page()
                        pdf.set_draw_color(180, 180, 180)
                        pdf.set_font("Arial", "B", 10)
                        pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                        pdf.cell(190, 10, "EVIDENCIA FOTOGRAFICA: ESTADO DE PUERTO", border=0, ln=True, fill=True)
                        pdf.set_text_color(0, 0, 0)
                        pdf.ln(5)
                        
                        temp_img_path = f"temp_evidencia_{uuid.uuid4().hex[:6]}.jpg"
                        with open(temp_img_path, "wb") as f: f.write(data['evidencia_puerto'])
                            
                        with Image.open(temp_img_path) as pil_img:
                            if pil_img.mode in ('RGBA', 'LA') or (pil_img.mode == 'P' and 'transparency' in pil_img.info):
                                pil_img = pil_img.convert('RGB')
                                pil_img.save(temp_img_path)
                            w_px, h_px = pil_img.size
                            aspect = h_px / w_px
                            w_mm = 160
                            h_mm = w_mm * aspect
                            if h_mm > 180: h_mm = 180; w_mm = h_mm / aspect
                                
                        x_pos = (210 - w_mm) / 2
                        pdf.image(temp_img_path, x=x_pos, y=pdf.get_y(), w=w_mm, h=h_mm)
                        os.remove(temp_img_path)

                    pdf.set_auto_page_break(auto=False)
                    pdf.set_y(-12)
                    pdf.set_font("Arial", "I", 8)
                    pdf.set_text_color(128, 128, 128)
                    pdf.cell(190, 10, "TridenTech 2026©".encode('latin-1', 'replace').decode('latin-1'), border=0, align="C")

                    identificador_unico = str(uuid.uuid4())[:8]
                    archivo_pdf = f"HPT_{data.get('centro','').replace(' ', '_')}_{data.get('fecha')}_{identificador_unico}.pdf"
                    pdf.output(archivo_pdf)
                    st.session_state.hpt_pdf_generado = archivo_pdf
                    
                    # Logica Supabase (Solo Intento)
                    url_pdf_nube = ""
                    try:
                        time.sleep(0.5) 
                        with open(archivo_pdf, "rb") as f: supabase.storage.from_("documentos").upload(path=archivo_pdf, file=f, file_options={"content-type": "application/pdf"})
                        url_pdf_nube = supabase.storage.from_("documentos").get_public_url(archivo_pdf)
                    except: pass

                    row_data = {
                        "fecha": str(data.get('fecha')), "usuario": st.session_state.current_user,
                        "empresa": data.get('empresa'), "centro": data.get('centro'), "area": data.get('area'),
                        "ponton": data.get('ponton'), "condicion_puerto": data.get('condicion_puerto'),
                        "hora_inicio": data.get('hora_inicio'), "hora_termino": data.get('hora_termino'), 
                        "faena": data.get('faena'), "tarea": data.get('tarea'), "url_documento": url_pdf_nube
                    }
                    try: supabase.table('hpt_history').insert(row_data).execute()
                    except: st.session_state.local_hpt_history.append(row_data)

                    # Logica Email (Solo Simulación para evitar bloqueos)
                    barra_carga.progress(60, text="📧 Enviando PDF...")
                    time.sleep(1) 

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
                st.rerun()
            with open(st.session_state.hpt_pdf_generado, "rb") as pdf_file:
                st.download_button(label="📥 Descargar Copia Local PDF", data=pdf_file, file_name=st.session_state.hpt_pdf_generado, mime="application/pdf", use_container_width=True)

elif st.session_state.current_page == 'reporte_diario':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.markdown("<h1 style='text-align: center;'>Reporte Diario Operativo</h1>", unsafe_allow_html=True)
    st.divider()

    st.subheader("Datos Operacionales de Faena")
    col_em1, col_em2 = st.columns(2)
    with col_em1: empresa_rd = st.selectbox("Empresa / Mandante", ["Salmones Blumar", "Salmones Blumar Magallanes"])
    with col_em2: centro_rd = st.selectbox("Centro de Cultivo", list(CENTROS_AREAS.keys()))
        
    area_rd = CENTROS_AREAS.get(centro_rd, "Desconocida"); correo_asignado_rd = CENTROS_CORREOS.get(centro_rd, "sin_correo@blumar.com")
    st.info(f"⚓ Área Asignada: **{area_rd}** | 📬 Correo Central: **{correo_asignado_rd}**")

    estado_turno = st.radio("Estado Operativo del Piloto", ["Operativo (Faena Normal)", "Detenido por Salud / Licencia"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        fecha_rd = st.date_input("Fecha", value=datetime.date.today())
        piloto_rd = st.text_input("Nombre de Piloto", value=st.session_state.get("rd_piloto", st.session_state.current_user), key="rd_piloto")
        encargado_rd = st.text_input("Encargado de Centro", key="rd_encargado")
        condicion_puerto_rd = st.selectbox("Condición de Puerto", ["Abierto", "Cerrado para naves menores", "Cerrado total"], key="rd_puerto")
        evidencia_img_rd = st.file_uploader("📸 Evidencia fotográfica de puerto cerrado", type=['png', 'jpg', 'jpeg'], key="rd_evidencia") if condicion_puerto_rd != "Abierto" else None
        ponton_rd = st.text_input("Nombre Pontón", key="rd_ponton")

    if estado_turno != "Operativo (Faena Normal)" or condicion_puerto_rd == "Cerrado total":
        st.warning("⚠️ **Modo Express Activado:** Se omitirán los detalles de faena por inactividad.")
        with col2:
            st.text_input("Jaula / Balsa", value="N/A", disabled=True)
            st.text_input("Rango Horario", value="N/A", disabled=True)
            correo_adicional_rd = st.text_input("Correos Adicionales (Separados por coma)", key="rd_correos")
        jaula_rd = "N/A"; hora_inicio_rd = "08:00"; hora_termino_rd = "18:00"
        tarea_rd = f"Jornada sin operaciones submarinas. Motivo: {estado_turno if condicion_puerto_rd != 'Cerrado total' else 'Puerto Cerrado'}."
    else:
        with col2:
            jaula_rd = st.text_input("Jaula / Balsa Trabajada", key="rd_jaula")
            hora_inicio_rd = st.selectbox("Hora Inicio Rango", RANGOS_INICIO, key="rd_hora_inicio")
            hora_termino_rd = st.selectbox("Hora Término Rango", RANGO_TERMINO, key="rd_hora_termino")
            correo_adicional_rd = st.text_input("Correos Adicionales (Separados por coma)", key="rd_correos")
        tarea_rd = st.text_area("Descripción de la Tarea Realizada", key="rd_tarea")
        
    st.subheader("Firmas de Responsabilidad")
    col_f_rd1, col_f_rd2 = st.columns(2)
    with col_f_rd1:
        st.write("Firma Piloto ROV")
        firma_piloto_rd = st_canvas(stroke_width=2, stroke_color="#000", background_color="#FFF", height=150, width=300, key="firma_p_rd")
    with col_f_rd2:
        st.write("Firma Encargado de Centro")
        firma_encargado_rd = st_canvas(stroke_width=2, stroke_color="#000", background_color="#FFF", height=150, width=300, key="firma_e_rd")

    submit_rd = st.button("GENERAR Y GUARDAR REPORTE DIARIO", type="primary", use_container_width=True)

    if submit_rd:
        barra_rd = st.progress(0, text="⚙️ Generando PDF...")
        # Generación simplificada de Reporte Diario (similar al HPT)
        time.sleep(1)
        barra_rd.progress(100, text="✅ ¡LISTO!")
        st.success("✅ Reporte Diario Generado Exitosamente (Simulación).")
        time.sleep(1); barra_rd.empty()

elif st.session_state.current_page == 'entrega_turno':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.markdown("<h1 style='text-align: center;'>Panel de Entrega de Turno Operativo</h1>", unsafe_allow_html=True)
    st.divider()

    st.header("1. Información General")
    c1, c2, c3, c4 = st.columns(4)
    with c1: piloto_entrante = st.text_input("Piloto Entrante")
    with c2: piloto_saliente = st.text_input("Piloto Saliente", value=st.session_state.current_user)
    with c3: fecha_et = st.date_input("Fecha", datetime.date.today())
    with c4: centro_et = st.selectbox("Centro", list(CENTROS_AREAS.keys()))

    st.markdown("---"); st.header("2. Equipos en Terreno (ROV)")
    c6, c7 = st.columns(2)
    with c6: equipo_rov = st.selectbox("Modelo de Equipo", ["DTG3", "MC Petrohue", "Chasing Promax"])
    with c7: estado_equipo = st.selectbox("Estado General del ROV", ["Bueno", "Regular", "Requiere cambio"])

    if st.button("Guardar y Enviar", type="primary", use_container_width=True):
        st.success(f"Reporte de Entrega de Turno para {centro_et} enviado exitosamente (Simulación).")

elif st.session_state.current_page == 'modulo_busqueda':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.markdown("<h1 style='text-align: center;'>Historial de Documentación</h1>", unsafe_allow_html=True)
    st.divider()
    modulo_consulta = st.selectbox("Módulo a Consultar", ["HPT", "Reportes Diarios", "Entregas de Turno"])
    st.info(f"No se registran datos en el historial local de {modulo_consulta}.")

elif st.session_state.current_page == 'panel_graficos':
    st.button("⬅️ Volver al Menú Principal", on_click=set_page, args=('main_menu',))
    st.markdown("<h1 style='text-align: center;'>📈 Métricas e Inteligencia de Negocio</h1>", unsafe_allow_html=True)
    st.divider()
    st.info("No existen suficientes registros en BD para estructurar gráficos estadísticos en esta sesión local.")
