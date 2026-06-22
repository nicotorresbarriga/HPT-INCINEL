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

# 1. Configuración de página
st.set_page_config(
    page_title="Plataforma TechTrident",
    page_icon="🔱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Inyección CSS (Diseño claro y moderno)
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f2 100%);
        color: #1a202c;
    }
    h1, h2, h3 {
        color: #2d3748;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stButton>button {
        background-color: #3182ce;
        color: white;
        border-radius: 8px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2b6cb0;
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        border-radius: 6px;
        border: 1px solid #cbd5e0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Inicialización del Administrador de Estados (Session State)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'
if 'hpt_step' not in st.session_state:
    st.session_state.hpt_step = 1
if 'hpt_data' not in st.session_state:
    st.session_state.hpt_data = {}

# Funciones de Navegación
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
        st.markdown("<h2 style='text-align: center;'>Portal Operativo</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("INGRESAR", use_container_width=True)
            
            if submitted:
                if user != "" and password != "":
                    st.session_state.logged_in = True
                    st.session_state.current_page = 'main_menu'
                    st.rerun()
                else:
                    st.error("Credenciales inválidas. Intente nuevamente.")

# ---------------------------------------------------------
# MÓDULO 2: MENÚ PRINCIPAL
# ---------------------------------------------------------
elif st.session_state.current_page == 'main_menu':
    st.title("Sistema de Gestión Operativa")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 HPT", use_container_width=True):
            set_page('hpt_menu')
            st.rerun()
    with col2:
        if st.button("📊 REPORTE DIARIO", use_container_width=True):
            st.info("Módulo en desarrollo.")
    with col3:
        if st.button("🔒 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
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
        if st.button("➕ NUEVO", use_container_width=True):
            set_step(1)
            set_page('hpt_nuevo')
            st.rerun()
    with col2:
        st.button("🔍 BÚSQUEDA", use_container_width=True)
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
        empresa = st.selectbox("Empresa", ["Salmones Blumar", "Salmones Blumar Magallanes"])
        
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", datetime.date.today())
            hora_inicio = st.time_input("Hora de Inicio")
            encargado = st.text_input("Encargado del Centro")
            apr1 = st.text_input("Asesor Prevención Riesgos 1")
        with col2:
            centros_dict = {
                "dring3": "centro.dring3@blumar.com",
                "Elena Norte": "centro.elenanorte@blumar.com",
                "Ninualac 2": "centro.ninualac2@blumar.com",
                "Otro": ""
            }
            centro = st.selectbox("Centro de Cultivo", list(centros_dict.keys()))
            hora_termino = st.time_input("Hora de Término")
            correo = st.text_input("Correo del Centro", value=centros_dict.get(centro, ""))
            apr2 = st.text_input("Asesor Prevención Riesgos 2")
            
        tarea = st.text_area("Tarea a Realizar")
        
        if st.button("SIGUIENTE ➡️", use_container_width=True):
            st.session_state.hpt_data.update({
                "empresa": empresa, "fecha": str(fecha), "hora_inicio": str(hora_inicio),
                "hora_termino": str(hora_termino), "centro": centro, "correo": correo,
                "encargado": encargado, "apr1": apr1, "apr2": apr2, "tarea": tarea
            })
            set_step(2)
            st.rerun()

    # --- PASO 2: EPP CHECKLIST ---
    elif st.session_state.hpt_step == 2:
        st.subheader("Checklist EPP")
        col1, col2 = st.columns(2)
        with col1:
            epp_guantes = st.checkbox("Guantes")
            epp_chaleco = st.checkbox("Chaleco Salvavidas")
            epp_zapatos = st.checkbox("Zapatos de seguridad / Botas")
            epp_termica = st.checkbox("Ropa Térmica")
        with col2:
            epp_traje = st.checkbox("Traje de Agua")
            epp_comunicacion = st.checkbox("Medios de Comunicación")
            epp_botiquin = st.checkbox("Botiquín")
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⬅️ ATRÁS", key="back2", use_container_width=True):
                set_step(1)
                st.rerun()
        with col_btn2:
            if st.button("SIGUIENTE ➡️", key="next2", use_container_width=True):
                st.session_state.hpt_data.update({
                    "epp": [epp_guantes, epp_chaleco, epp_zapatos, epp_termica, epp_traje, epp_comunicacion, epp_botiquin]
                })
                set_step(3)
                st.rerun()

    # --- PASO 3: ERC CHECKLIST Y FAENA ---
    elif st.session_state.hpt_step == 3:
        st.subheader("Faena a Realizar y Checklist ERC")
        
        opciones_faena = [
            "Inspeccion Red Lobera", 
            "Inspeccion Red pecera", 
            "Inspeccion Tensores", 
            "Recuperacion inorganico", 
            "Apoyo Centro de cultivo", 
            "Extraccion de mortalidad", 
            "Mantencion equipos"
        ]
        faena = st.selectbox("Faena a realizar", opciones_faena)
        
        st.markdown("**Checklist ERC**")
        col1, col2 = st.columns(2)
        with col1:
            erc_izaje = st.checkbox("Izaje")
            erc_buceo = st.checkbox("Buceo")
            erc_electricos = st.checkbox("Intervención Equipos Eléctricos")
        with col2:
            erc_caidas = st.checkbox("Caídas al mismo/distinto nivel")
            erc_navegacion = st.checkbox("Navegación Diurna/Nocturna")
            erc_atrapamiento = st.checkbox("Atrapamiento")
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⬅️ ATRÁS", key="back3", use_container_width=True):
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
                
                with st.spinner("Compilando arquitectura PDF y transmitiendo..."):
                    try:
                        pdf = FPDF()
                        pdf.add_page()
                        
                        if os.path.exists("logo.png"):
                            pdf.image("logo.png", x=10, y=8, w=30)
                        
                        pdf.set_font("Arial", "B", 14)
                        pdf.cell(0, 10, "HERRAMIENTA DE PREVENCION EN TERRENO (HPT) - ROV", ln=True, align="C")
                        pdf.ln(5)
                        
                        pdf.set_font("Arial", "", 9)
                        pdf.cell(0, 6, f"Empresa: {data.get('empresa')} | Centro: {data.get('centro')}", ln=True)
                        pdf.cell(0, 6, f"Fecha: {data.get('fecha')} | Inicio: {data.get('hora_inicio')} | Termino: {data.get('hora_termino')}", ln=True)
                        pdf.cell(0, 6, f"Encargado: {data.get('encargado')} | Correo: {data.get('correo')}", ln=True)
                        pdf.cell(0, 6, f"APR1: {data.get('apr1')} | APR2: {data.get('apr2')}", ln=True)
                        pdf.cell(0, 6, f"Faena: {data.get('faena')}", ln=True)
                        pdf.multi_cell(0, 6, f"Tarea complementaria: {data.get('tarea')}")
                        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                        pdf.ln(3)
                        
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(0, 6, "EPP:", ln=True)
                        pdf.set_font("Arial", "", 8)
                        epp_labels = ["Guantes", "Chaleco", "Zapatos/Botas", "Ropa Termica", "Traje Agua", "Comunicacion", "Botiquin"]
                        epp_vals = [f"[{'X' if v else ' '}] {l}" for v, l in zip(data.get('epp', []), epp_labels)]
                        pdf.multi_cell(0, 5, " | ".join(epp_vals))
                        
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(0, 6, "ERC:", ln=True)
                        pdf.set_font("Arial", "", 8)
                        erc_labels = ["Izaje", "Buceo", "Eq. Electricos", "Caidas", "Nav. Diurna/Nocturna", "Atrapamiento"]
                        erc_vals = [f"[{'X' if v else ' '}] {l}" for v, l in zip(data.get('erc', []), erc_labels)]
                        pdf.multi_cell(0, 5, " | ".join(erc_vals))
                        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                        pdf.ln(3)
                        
                        pdf.set_font("Arial", "B", 9)
                        pdf.cell(0, 6, "Toma de Conocimiento:", ln=True)
                        pdf.set_font("Arial", "", 8)
                        pdf.cell(0, 5, f"Difusion: {tc_nombre} | Fecha: {tc_fecha} | Hora: {tc_hora} | Duracion: {tc_duracion}", ln=True)
                        pdf.cell(0, 5, f"Relator: {tc_relator} | Cargo: {tc_cargo}", ln=True)
                        
                        # Función de procesamiento de lienzo a JPG
                        def procesar_firma(canvas_obj, filename):
                            if canvas_obj.image_data is not None:
                                img_data = canvas_obj.image_data
                                firma_img = Image.fromarray((img_data).astype('uint8'), mode='RGBA')
                                fondo_blanco = Image.new("RGB", firma_img.size, (255, 255, 255))
                                fondo_blanco.paste(firma_img, mask=firma_img.split()[3])
                                fondo_blanco.save(filename)
                                return True
                            return False

                        y_firmas = pdf.get_y() + 5
                        
                        if procesar_firma(firma_relator, "f_relator.jpg"):
                            pdf.image("f_relator.jpg", x=10, y=y_firmas, w=40)
                        if procesar_firma(firma_sup_serv, "f_serv.jpg"):
                            pdf.image("f_serv.jpg", x=70, y=y_firmas, w=40)
                        if procesar_firma(firma_sup_sal, "f_sal.jpg"):
                            pdf.image("f_sal.jpg", x=130, y=y_firmas, w=40)
                            
                        pdf.set_y(y_firmas + 30)
                        pdf.set_font("Arial", "B", 8)
                        pdf.cell(60, 5, "Firma Relator", align="C")
                        pdf.cell(60, 5, "Firma Sup. Servicio", align="C")
                        pdf.cell(60, 5, f"Firma {data.get('empresa')}", align="C")

                        archivo_pdf = f"HPT_{data.get('centro','').replace(' ', '_')}_{data.get('fecha')}.pdf"
                        pdf.output(archivo_pdf)

                        # Rutina SMTP
                        remitente = st.secrets["EMAIL_USER"]
                        password = st.secrets["EMAIL_PASS"]
                        destinatario = data.get('correo', remitente)
                        
                        msg = MIMEMultipart()
                        msg['From'] = remitente
                        msg['To'] = destinatario
                        msg['Subject'] = f"Reporte HPT - {data.get('centro')} - {data.get('fecha')}"
                        msg.attach(MIMEText("Se adjunta el reporte HPT operacional.", 'plain'))

                        with open(archivo_pdf, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename={archivo_pdf}")
                        msg.attach(part)

                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(remitente, password)
                        server.send_message(msg)
                        server.quit()

                        st.success("HPT Compilada y Transmitida con éxito.")
                        
                        with open(archivo_pdf, "rb") as pdf_file:
                            st.download_button(label="📥 Descargar PDF", data=pdf_file, file_name=archivo_pdf, mime="application/pdf")
                            
                    except Exception as e:
                        st.error(f"Falla de ejecución técnica: {e}")
