import streamlit as st
import datetime
import os
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from fpdf import FPDF
from PIL import Image
try:
    from supabase import create_client, Client
except ImportError:
    pass # Asumimos que está instalado en la nube

# ==========================================
# CONFIGURACIÓN REAL (PRODUCCIÓN)
# ==========================================
USUARIOS = {
    "Ntorres": "17909926", 
    "admin": "admin"
}

CENTROS_AREAS = {
    "Centro Punta Vergara": "Area Austral"
}

# CORREOS REALES DEL CENTRO
CENTROS_CORREOS = {
    "Centro Punta Vergara": "centro.puntavergara@blumar.com"
}

# CORREOS REALES DE PREVENCIÓN BLUMAR
CORREOS_PREVENCION = [
    "franco.vidal@blumar.com", 
    "jonathan.romero@blumar.com"
]

# CORREOS OCULTOS DE JEFATURA INCINEL (BCC)
CORREOS_OCULTOS = [
    "calarcon@incinel.cl", 
    "ealvarez@incinel.cl"
]

# Conexión Supabase (Manejo seguro)
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None
    
# Credenciales Correo
try:
    SMTP_SERVER = st.secrets["SMTP_SERVER"]
    SMTP_PORT = st.secrets["SMTP_PORT"]
    SMTP_USER = st.secrets["SMTP_USER"]
    SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
except:
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = ""
    SMTP_PASSWORD = ""

# ==========================================
# CLASE PDF PERSONALIZADA (FOOTER TRIDENTECH)
# ==========================================
class PDF_Trident(FPDF):
    def footer(self):
        # Posición a 1.5 cm desde abajo
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Color de texto gris claro para la marca de agua
        self.set_text_color(150, 150, 150)
        # Sello de propiedad intelectual
        self.cell(0, 10, 'TridenTech 2026© - Plataforma de Gestión Operativa ROV', 0, 0, 'C')

# ==========================================
# FUNCIONES DE AYUDA
# ==========================================
def enviar_correo_con_adjunto(destinatarios, ocultos, asunto, cuerpo, filepath, filename):
    if not SMTP_USER or not SMTP_PASSWORD:
        return False, "Credenciales SMTP no configuradas."
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(destinatarios)
    msg['Subject'] = asunto

    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        with open(filepath, "rb") as f:
            adjunto = MIMEApplication(f.read(), _subtype="pdf")
            adjunto.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(adjunto)
            
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        todos_destinatarios = destinatarios + ocultos
        server.sendmail(SMTP_USER, todos_destinatarios, msg.as_string())
        server.quit()
        return True, "Enviado con éxito"
    except Exception as e:
        return False, str(e)

def procesar_firma(canvas_result, filename):
    if canvas_result is not None and canvas_result.image_data is not None:
        try:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            img = img.convert('RGB') # Evitar problemas con transparencia en FPDF
            img.save(filename, format="JPEG")
            return True
        except Exception:
            return False
    return False

def generar_pdf_entrega(datos, logo_filename, nombre_archivo, firma_path=None, imagenes_subidas=None):
    pdf = PDF_Trident()
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=15) 
    pdf.add_page()
    
    # Configurar color de borde global a gris suave para un diseño limpio
    pdf.set_draw_color(180, 180, 180)

    # Buscamos logo corporativo de Incinel
    logo_pdf = "logo2.png" if os.path.exists("logo2.png") else "logo2.jpg" if os.path.exists("logo2.jpg") else "logo.png"
    if os.path.exists(logo_pdf):
        pdf.image(logo_pdf, x=10, y=10, h=20)
        
    pdf.set_y(35) 
    pdf.set_font("Arial", 'B', 15)
    pdf.set_fill_color(15, 55, 105) # Azul Marino Corporativo
    pdf.set_text_color(255, 255, 255) 
    pdf.cell(190, 10, "REPORTE FORMAL DE ENTREGA DE TURNO - ROV", border=1, ln=True, align='C', fill=True)
    
    # Sello de Auditoría Inmutable
    fecha_hora_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    piloto_saliente = datos.get('1. Información General', {}).get('Piloto_Saliente', 'Desconocido')
    pdf.set_font("Arial", 'I', 8); pdf.set_text_color(128, 128, 128)
    pdf.cell(190, 6, f"Sello de Auditoría Inmutable: Generado el {fecha_hora_actual} por {piloto_saliente}", border=0, ln=True, align='C')
    pdf.ln(2)
    
    for seccion, campos in datos.items():
        if pdf.get_y() > 250: pdf.add_page()
        pdf.ln(3); pdf.set_font("Arial", 'B', 11)
        pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255) 
        pdf.cell(190, 8, f"  {seccion.upper()}", border=1, ln=True, fill=True)
        for clave, valor in campos.items():
            nombre_campo = clave.replace('_', ' ')
            if pdf.get_y() > 265: pdf.add_page()
            pdf.set_font("Arial", 'B', 9); pdf.set_fill_color(245, 245, 245); pdf.set_text_color(0, 0, 0)
            pdf.cell(190, 8, f" {nombre_campo}:", border=1, ln=True, fill=True)
            pdf.set_font("Arial", '', 9)
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
        pdf.set_font("Arial", 'B', 11)
        pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 8, "  EVIDENCIA FOTOGRAFICA", border=1, ln=True, fill=True); pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        
        y_pos = pdf.get_y()
        for idx, img_file in enumerate(imagenes_subidas):
            if idx > 0 and idx % 2 == 0:
                y_pos += 85
                if y_pos > 200:
                    pdf.add_page()
                    y_pos = pdf.get_y()
            
            x_pos = 10 if idx % 2 == 0 else 105
            
            try:
                temp_img_path = f"temp_img_{idx}.jpg"
                with open(temp_img_path, "wb") as f:
                    f.write(img_file.getbuffer())
                pdf.image(temp_img_path, x=x_pos, y=y_pos, w=90, h=80)
                os.remove(temp_img_path)
            except Exception:
                pdf.set_xy(x_pos, y_pos)
                pdf.cell(90, 80, "Error al procesar imagen", border=1, align='C')

    if firma_path and os.path.exists(firma_path):
        if pdf.get_y() > 220: pdf.add_page()
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(190, 10, "FIRMA DE RESPONSABILIDAD", border=0, ln=True, align='C')
        pdf.image(firma_path, x=75, y=pdf.get_y(), w=60, h=30)
        pdf.ln(35)
        pdf.cell(190, 10, piloto_saliente, border=0, ln=True, align='C')
        
    pdf.output(nombre_archivo, 'F')

# ==========================================
# INICIALIZACIÓN DE LA APP STREAMLIT
# ==========================================
st.set_page_config(page_title="TechTrident ROV", page_icon="⚓", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "local_reportes_history" not in st.session_state:
    st.session_state.local_reportes_history = []

def login():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>⚓ TechTrident Platform</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Gestión Operativa de Flotas ROV</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        st.write("---")
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            if username in USUARIOS and USUARIOS[username] == password:
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

if not st.session_state.logged_in:
    login()
    st.stop()

st.sidebar.image("logo.png" if os.path.exists("logo.png") else "https://via.placeholder.com/150", width=150)
st.sidebar.title(f"Hola, {st.session_state.current_user}")
menu = st.sidebar.radio("Navegación", ["Inicio", "Entrega de Turno", "HPT Submarina", "Reporte Diario"])

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()

if menu == "Inicio":
    st.title("⚓ Panel de Control - TechTrident")
    st.info("Selecciona una opción en el menú lateral para comenzar a operar.")
    st.markdown("### 📊 Estado de la Flota")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Reportes Hoy", "0", "Operativo")
    with c2: st.metric("HPT Activas", "0", "Seguro")
    with c3: st.metric("Alertas Mantención", "0", "Normal")

elif menu == "Entrega de Turno":
    st.title("🔄 Entrega de Turno Formal")
    
    with st.form("entrega_turno_form"):
        st.subheader("1. Información General")
        c1, c2 = st.columns(2)
        piloto_saliente = c1.text_input("Piloto Saliente", value=st.session_state.current_user)
        piloto_entrante = c2.text_input("Piloto Entrante")
        centro = c1.selectbox("Centro de Cultivo", list(CENTROS_AREAS.keys()))
        fecha = c2.date_input("Fecha de Entrega")
        
        st.subheader("2. Estado del Equipo ROV")
        estado_rov = st.selectbox("Condición General del Equipo", ["Operativo", "Operativo con Observaciones", "Inoperativo"])
        obs_rov = st.text_area("Observaciones del ROV (Fallas, mantenciones pendientes)")
        
        st.subheader("3. Herramientas y Accesorios")
        inventario = st.multiselect("Checklist de Herramientas Entregadas", 
                                    ["Control Mando", "Cable Umbilical (Completo)", "Caja Herramientas Básica", 
                                     "Repuestos (Orings, Hélices)", "Notebook Operativo", "Monitor Externo"])
        
        st.subheader("4. Tareas Pendientes")
        pendientes = st.text_area("Describa tareas no concluidas o requerimientos para el próximo turno")
        
        evidencia_fotos = st.file_uploader("Subir Fotografías del Estado del Equipo", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        st.write("---")
        st.subheader("Firma del Piloto Saliente")
        from streamlit_drawable_canvas import st_canvas
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  
            stroke_width=2,
            stroke_color="#000000",
            background_color="#EEEEEE",
            height=150,
            drawing_mode="freedraw",
            key="canvas_entrega"
        )
        
        submit_btn = st.form_submit_button("Generar y Enviar Entrega", type="primary")

    if submit_btn:
        if not piloto_entrante:
            st.error("Debe indicar el Piloto Entrante.")
        else:
            datos_entrega = {
                "1. Información General": {
                    "Piloto_Saliente": piloto_saliente,
                    "Piloto_Entrante": piloto_entrante,
                    "Centro_Cultivo": centro,
                    "Fecha": str(fecha)
                },
                "2. Estado Técnico": {
                    "Estado_General": estado_rov,
                    "Observaciones": obs_rov
                },
                "3. Inventario": {
                    "Elementos_Entregados": inventario
                },
                "4. Gestión Operativa": {
                    "Tareas_Pendientes": pendientes
                }
            }
            
            firma_path = "firma_temp.jpg"
            has_firma = procesar_firma(canvas_result, firma_path)
            
            pdf_filename = f"Entrega_Turno_{centro.replace(' ', '_')}_{fecha}.pdf"
            
            with st.spinner("Generando documento inmutable..."):
                generar_pdf_entrega(datos_entrega, "logo.png", pdf_filename, firma_path if has_firma else None, evidencia_fotos)
            
            destinatarios = CORREOS_PREVENCION + [CENTROS_CORREOS.get(centro, "")]
            ocultos = CORREOS_OCULTOS
            
            with st.spinner("Enviando reportes..."):
                exito, msg = enviar_correo_con_adjunto(
                    destinatarios, ocultos,
                    f"Entrega de Turno ROV - {centro} - {fecha}",
                    f"Se adjunta reporte formal de entrega de turno.\nPiloto Saliente: {piloto_saliente}\nPiloto Entrante: {piloto_entrante}",
                    pdf_filename, pdf_filename
                )
                
            if exito:
                st.success(f"Reporte enviado con éxito a Prevención, Centro y Jefatura.")
            else:
                st.error(f"Error al enviar correo: {msg}")
                
            with open(pdf_filename, "rb") as f:
                st.download_button("📥 Descargar Copia Local PDF", f, file_name=pdf_filename, mime="application/pdf")
                
            if os.path.exists(firma_path): os.remove(firma_path)

elif menu == "HPT Submarina":
    st.title("🛡️ Herramienta de Prevención en Terreno (HPT)")
    
    if "hpt_step" not in st.session_state:
        st.session_state.hpt_step = 1
    if "hpt_data" not in st.session_state:
        st.session_state.hpt_data = {}

    def next_step(): st.session_state.hpt_step += 1
    def prev_step(): st.session_state.hpt_step -= 1
    def reset_hpt(): 
        st.session_state.hpt_step = 1
        st.session_state.hpt_data = {}

    # PASO 1
    if st.session_state.hpt_step == 1:
        st.subheader("Paso 1: Datos Operativos")
        
        st.session_state.hpt_data['empresa'] = st.selectbox("Empresa / Mandante", ["Salmones Blumar", "Salmones Blumar Magallanes"], 
                                                          index=0 if st.session_state.hpt_data.get('empresa') == "Salmones Blumar" else 1)
        st.session_state.hpt_data['centro'] = st.selectbox("Centro de Cultivo", list(CENTROS_AREAS.keys()),
                                                         index=list(CENTROS_AREAS.keys()).index(st.session_state.hpt_data.get('centro', list(CENTROS_AREAS.keys())[0])))
        
        c1, c2 = st.columns(2)
        st.session_state.hpt_data['fecha'] = c1.date_input("Fecha", value=st.session_state.hpt_data.get('fecha', datetime.date.today()))
        st.session_state.hpt_data['area'] = c2.text_input("Área Geográfica", value=st.session_state.hpt_data.get('area', CENTROS_AREAS[st.session_state.hpt_data['centro']]))
        
        c3, c4 = st.columns(2)
        st.session_state.hpt_data['hora_inicio'] = c3.time_input("Hora Inicio", value=st.session_state.hpt_data.get('hora_inicio', datetime.time(8, 0)))
        st.session_state.hpt_data['hora_termino'] = c4.time_input("Hora Término Estimada", value=st.session_state.hpt_data.get('hora_termino', datetime.time(18, 0)))
        
        c5, c6 = st.columns(2)
        st.session_state.hpt_data['ponton'] = c5.text_input("Nombre Pontón", value=st.session_state.hpt_data.get('ponton', ''))
        st.session_state.hpt_data['condicion_puerto'] = c6.selectbox("Condición de Puerto", ["Abierto", "Cerrado para Embarcaciones Menores", "Cerrado Total"],
                                                                   index=["Abierto", "Cerrado para Embarcaciones Menores", "Cerrado Total"].index(st.session_state.hpt_data.get('condicion_puerto', "Abierto")))
        
        if st.session_state.hpt_data['condicion_puerto'] != "Abierto":
            st.session_state.hpt_data['evidencia_puerto'] = st.file_uploader("Evidencia Estado de Puerto (Obligatorio para puerto cerrado)", type=["jpg", "png", "jpeg"])
        else:
            st.session_state.hpt_data['evidencia_puerto'] = None

        st.session_state.hpt_data['encargado'] = st.text_input("Encargado de Centro", value=st.session_state.hpt_data.get('encargado', ''))
        
        st.session_state.hpt_data['faena'] = st.selectbox("Faena (Actividad Principal)", ["Inspección Peceras", "Extracción Mortalidad", "Revisión Fondeos", "Búsqueda Elementos", "Otro"])
        st.session_state.hpt_data['tarea'] = st.text_area("Detalle Tarea Específica", value=st.session_state.hpt_data.get('tarea', ''))
        
        if st.button("Siguiente ➡️", type="primary"):
            if not st.session_state.hpt_data['ponton'] or not st.session_state.hpt_data['encargado'] or not st.session_state.hpt_data['tarea']:
                st.error("Por favor complete todos los campos de texto.")
            elif st.session_state.hpt_data['condicion_puerto'] != "Abierto" and not st.session_state.hpt_data['evidencia_puerto']:
                st.error("Debe adjuntar evidencia fotográfica del puerto cerrado.")
            else:
                next_step()
                st.rerun()

    # PASO 2
    elif st.session_state.hpt_step == 2:
        st.subheader("Paso 2: EPP Seleccionado")
        st.write("Seleccione los Equipos de Protección Personal utilizados:")
        epp1 = st.checkbox("Guantes", value=True)
        epp2 = st.checkbox("Chaleco Salvavidas", value=True)
        epp3 = st.checkbox("Zapatos Seguridad", value=True)
        epp4 = st.checkbox("Ropa Térmica", value=True)
        epp5 = st.checkbox("Traje de Agua", value=True)
        epp6 = st.checkbox("Radiocomunicación", value=True)
        epp7 = st.checkbox("Botiquín Primeros Auxilios", value=True)
        
        c1, c2 = st.columns(2)
        if c1.button("⬅️ Atrás"): prev_step(); st.rerun()
        if c2.button("Siguiente ➡️", type="primary"):
            st.session_state.hpt_data['epp'] = [epp1, epp2, epp3, epp4, epp5, epp6, epp7]
            if not any(st.session_state.hpt_data['epp']) and st.session_state.hpt_data['condicion_puerto'] == "Abierto":
                st.error("Debe seleccionar al menos un EPP si el puerto está abierto.")
            else:
                next_step(); st.rerun()

    # PASO 3
    elif st.session_state.hpt_step == 3:
        st.subheader("Paso 3: Riesgos Críticos (ERC)")
        st.write("Seleccione los riesgos presentes en la faena:")
        erc1 = st.checkbox("Operación Izaje")
        erc2 = st.checkbox("Interacción Buceo")
        erc3 = st.checkbox("Equipos Energizados")
        erc4 = st.checkbox("Caída al Mar / Distinto Nivel")
        erc5 = st.checkbox("Navegación / Clima")
        erc6 = st.checkbox("Atrapamiento")
        
        c1, c2 = st.columns(2)
        if c1.button("⬅️ Atrás"): prev_step(); st.rerun()
        if c2.button("Siguiente ➡️", type="primary"):
            st.session_state.hpt_data['erc'] = [erc1, erc2, erc3, erc4, erc5, erc6]
            if not any(st.session_state.hpt_data['erc']) and st.session_state.hpt_data['condicion_puerto'] == "Abierto":
                st.error("Debe identificar al menos un Riesgo Crítico si el puerto está abierto.")
            else:
                next_step(); st.rerun()

    # PASO 4 (AÑADIDO RUT RELATOR)
    elif st.session_state.hpt_step == 4:
        st.subheader("Paso 4: Difusión y Toma de Conocimiento")
        tc_relator = st.text_input("Nombre Relator / Piloto", value=st.session_state.current_user)
        tc_rut = st.text_input("RUT Relator", placeholder="12.345.678-9")
        tc_nombre = st.text_input("Nombre del Tema Difundido (Procedimiento)")
        tc_fecha = st.date_input("Fecha Difusión", value=st.session_state.hpt_data.get('fecha', datetime.date.today()))
        tc_hora = st.time_input("Hora Inicio Difusión")
        tc_duracion = st.selectbox("Duración", ["10 min", "15 min", "30 min", "45 min", "60 min"])
        
        c1, c2 = st.columns(2)
        if c1.button("⬅️ Atrás"): prev_step(); st.rerun()
        if c2.button("Siguiente ➡️", type="primary"):
            if not tc_nombre or not tc_rut:
                st.error("Debe ingresar el RUT del relator y el Tema Difundido.")
            else:
                st.session_state.hpt_data['tc'] = {
                    'relator': tc_relator, 'rut': tc_rut, 'tema': tc_nombre,
                    'fecha': tc_fecha, 'hora': tc_hora, 'duracion': tc_duracion
                }
                next_step(); st.rerun()

    # PASO 5 (FIRMAS Y GENERACION DE PDF)
    elif st.session_state.hpt_step == 5:
        st.subheader("Paso 5: Firmas y Envío")
        
        from streamlit_drawable_canvas import st_canvas
        st.write("Firma Piloto ROV / Supervisor Servicio")
        firma_sup_serv = st_canvas(fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000000", background_color="#EEEEEE", height=100, drawing_mode="freedraw", key="f1")
        st.write("Firma Encargado de Centro")
        firma_encargado = st_canvas(fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000000", background_color="#EEEEEE", height=100, drawing_mode="freedraw", key="f2")

        c1, c2 = st.columns(2)
        if c1.button("⬅️ Atrás"): prev_step(); st.rerun()
        
        if firma_sup_serv.image_data is not None and firma_encargado.image_data is not None:
            if st.button("GENERAR Y ENVIAR HPT", type="primary", use_container_width=True):
                data = st.session_state.hpt_data
                tc_data = data['tc']
                tc_relator = str(tc_data['relator']); tc_rut = str(tc_data['rut'])
                tc_nombre = str(tc_data['tema']); tc_fecha = str(tc_data['fecha'])
                tc_hora = str(tc_data['hora']); tc_duracion = str(tc_data['duracion'])
                
                barra_carga = st.progress(0, text="⚙️ Generando PDF...")
                
                try:
                    # PDF_Trident para asegurar el sello en el footer
                    pdf = PDF_Trident(); pdf.add_page()
                    
                    # BUSCA Y COLOCA LOGO INCINEL (LOGO2)
                    logo_pdf = "logo2.png" if os.path.exists("logo2.png") else "logo2.jpg" if os.path.exists("logo2.jpg") else "logo.png"
                    if os.path.exists(logo_pdf): pdf.image(logo_pdf, x=10, y=8, h=20)
                    
                    pdf.set_draw_color(180, 180, 180)
                    pdf.set_y(32); pdf.set_font("Arial", "B", 13)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 10, "HERRAMIENTA DE PREVENCION EN TERRENO (HPT) - ROV", border=1, ln=True, align="C", fill=True)
                    
                    # Sello de Auditoría Inmutable
                    fecha_hora_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    pdf.set_font("Arial", "I", 8); pdf.set_text_color(128, 128, 128)
                    pdf.cell(0, 6, f"Sello de Auditoría Inmutable: Generado el {fecha_hora_actual} por {st.session_state.current_user}", border=0, ln=True, align="C")
                    pdf.ln(2)

                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 10); pdf.cell(190, 8, "1. DATOS OPERATIVOS", border=1, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0)
                    
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Empresa / Mandante:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, data.get('empresa', '')[:35], border=1)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Centro de Cultivo:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, data.get('centro', '')[:35], border=1, ln=True)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Fecha Maniobra:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, str(data.get('fecha', '')), border=1)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Area Geografica:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, data.get('area', '')[:35], border=1, ln=True)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Hora Inicio Rango:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, str(data.get('hora_inicio', '')), border=1)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Hora Termino Rango:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, str(data.get('hora_termino', '')), border=1, ln=True)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Nombre Ponton:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, data.get('ponton', '')[:35], border=1)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Condicion Puerto:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, data.get('condicion_puerto', '')[:35], border=1, ln=True)
                    
                    # RESTAURADO: Encargado de Centro y Correo Centro
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Encargado Centro:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(155, 8, data.get('encargado', '')[:80], border=1, ln=True)
                    correo_centro_hpt = CENTROS_CORREOS.get(data.get('centro', ''), 'No registrado')
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Correo Centro:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(155, 8, correo_centro_hpt[:80], border=1, ln=True)
                    
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Prevencionista 1:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(155, 8, CORREOS_PREVENCION[0], border=1, ln=True)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Prevencionista 2:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(155, 8, CORREOS_PREVENCION[1], border=1, ln=True)
                    
                    pdf.set_font("Arial", "B", 9)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.cell(190, 8, "Faena Primaria y Detalles Especificos:", border=1, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "", 9)
                    texto_tarea = f"FAENA: {data.get('faena', '')}\nDETALLES: {data.get('tarea', '')}"
                    pdf.multi_cell(190, 6, texto_tarea, border=1)

                    pdf.ln(2)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 10); pdf.cell(190, 8, "2. EQUIPO DE PROTECCION PERSONAL SELECCIONADO", border=1, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 9)
                    epp_labels = ["Guantes", "Chaleco", "Zapatos", "Ropa Termica", "Traje Agua", "Comunicacion", "Botiquin"]
                    epp_vals = data.get('epp', []); epp_seleccionados = [epp_labels[i] for i in range(len(epp_labels)) if i < len(epp_vals) and epp_vals[i]]
                    if not epp_seleccionados: pdf.cell(190, 8, "Ningun EPP registrado o Aplica (Puerto Cerrado Total).", border=1, ln=True)
                    else:
                        for i, epp in enumerate(epp_seleccionados): pdf.cell(190/3, 8, f"[ X ] {epp}", border=1, ln=1 if (i + 1) % 3 == 0 or i == len(epp_seleccionados) - 1 else 0)

                    pdf.ln(2)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 10); pdf.cell(190, 8, "3. RIESGOS CRITICOS EVALUADOS (ERC)", border=1, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 9)
                    erc_labels = ["Izaje", "Buceo", "Eq. Electricos", "Caidas", "Navegacion", "Atrapamiento"]
                    erc_vals = data.get('erc', []); erc_seleccionados = [erc_labels[i] for i in range(len(erc_labels)) if i < len(erc_vals) and erc_vals[i]]
                    if not erc_seleccionados: pdf.cell(190, 8, "Ningun Riesgo seleccionado o Aplica (Puerto Cerrado Total).", border=1, ln=True)
                    else:
                        for i, erc in enumerate(erc_seleccionados): pdf.cell(190/2, 8, f"[ X ] {erc}", border=1, ln=1 if (i + 1) % 2 == 0 or i == len(erc_seleccionados) - 1 else 0)

                    pdf.ln(2)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 10); pdf.cell(190, 8, "4. DIFUSION Y TOMA DE CONOCIMIENTO", border=1, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Relator / Piloto:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, tc_relator[:35], border=1)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "RUT Relator:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, tc_rut[:20], border=1, ln=True)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Tema Difundido:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(155, 8, tc_nombre[:80], border=1, ln=True)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Fecha y Hora:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, f"{tc_fecha} {tc_hora}", border=1)
                    pdf.set_font("Arial", "B", 9); pdf.cell(35, 8, "Duracion Rango:", border=1); pdf.set_font("Arial", "", 9); pdf.cell(60, 8, tc_duracion, border=1, ln=True)

                    pdf.ln(2)
                    pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 10); pdf.cell(190, 8, "5. CUADRO DE FIRMAS RESPONSABLES", border=1, ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(95, 22, "", border=1); pdf.cell(95, 22, "", border=1, ln=True)
                    id_firmas = uuid.uuid4().hex[:8]; f_serv = f"f_serv_{id_firmas}.jpg"; f_enc = f"f_encargado_{id_firmas}.jpg"
                    if procesar_firma(firma_sup_serv, f_serv): pdf.image(f_serv, x=35, y=pdf.get_y()-20, w=45, h=15)
                    if procesar_firma(firma_encargado, f_enc): pdf.image(f_enc, x=130, y=pdf.get_y()-20, w=45, h=15)
                    pdf.set_font("Arial", "B", 9); pdf.cell(95, 8, "Firma Supervisor Servicio", border=1, align="C"); pdf.cell(95, 8, "Firma Encargado de Centro", border=1, ln=True, align="C")

                    # Agregar foto de evidencia de puerto si existe
                    if data.get('evidencia_puerto'):
                        pdf.add_page()
                        pdf.set_draw_color(180, 180, 180)
                        pdf.set_font("Arial", "B", 11)
                        pdf.set_fill_color(15, 55, 105); pdf.set_text_color(255, 255, 255)
                        pdf.cell(190, 10, "EVIDENCIA FOTOGRAFICA: ESTADO DE PUERTO", border=1, ln=True, fill=True)
                        pdf.set_text_color(0, 0, 0)
                        
                        ev_puerto = data['evidencia_puerto']
                        temp_ev_path = f"temp_ev_{uuid.uuid4().hex[:8]}.jpg"
                        with open(temp_ev_path, "wb") as f:
                            f.write(ev_puerto.getbuffer())
                        pdf.image(temp_ev_path, x=60, y=pdf.get_y()+5, w=90, h=80)
                        os.remove(temp_ev_path)

                    pdf_filename_hpt = f"HPT_{data.get('centro', '').replace(' ', '_')}_{data.get('fecha', '')}.pdf"
                    pdf.output(pdf_filename_hpt, 'F')
                    barra_carga.progress(50, text="PDF Generado. Subiendo a Base de Datos...")

                    if supabase:
                        with open(pdf_filename_hpt, "rb") as f:
                            supabase.storage.from_("pdfs").upload(f"hpt/{pdf_filename_hpt}", f, {"content-type": "application/pdf"})
                        url_pdf_nube = supabase.storage.from_("pdfs").get_public_url(f"hpt/{pdf_filename_hpt}")
                        supabase.table("reportes_history").insert({
                            "tipo": "HPT", "centro": data.get('centro'), "fecha": str(data.get('fecha')), 
                            "piloto": st.session_state.current_user, "pdf_url": url_pdf_nube
                        }).execute()

                    barra_carga.progress(80, text="Enviando correos oficiales...")
                    
                    destinatarios_hpt = CORREOS_PREVENCION + [CENTROS_CORREOS.get(data.get('centro', ''), '')]
                    destinatarios_hpt = [d for d in destinatarios_hpt if d]
                    ocultos_hpt = CORREOS_OCULTOS
                    
                    cuerpo_correo = f"""
Estimados,
Se adjunta la Herramienta de Prevención en Terreno (HPT) generada digitalmente.

Centro: {data.get('centro', '')}
Fecha: {data.get('fecha', '')}
Piloto ROV: {st.session_state.current_user}

Atentamente,
TechTrident Operations - Plataforma Oficial
                    """
                    exito_hpt, msg_hpt = enviar_correo_con_adjunto(
                        destinatarios_hpt, ocultos_hpt,
                        f"HPT Digital ROV - {data.get('centro', '')} - {data.get('fecha', '')}",
                        cuerpo_correo.strip(), pdf_filename_hpt, pdf_filename_hpt
                    )
                    
                    barra_carga.progress(100, text="¡Completado!")
                    if exito_hpt: st.success("HPT Generada y Enviada Correctamente a Prevención y Jefatura.")
                    else: st.warning(f"HPT Generada localmente. Error correo: {msg_hpt}")
                    
                    with open(pdf_filename_hpt, "rb") as f:
                        st.download_button("📥 Descargar Copia Local HPT", f, file_name=pdf_filename_hpt, mime="application/pdf")
                        
                    if st.button("Crear Nueva HPT", type="secondary"):
                        reset_hpt()
                        st.rerun()

                except Exception as e:
                    st.error(f"Error procesando HPT: {e}")
                finally:
                    if os.path.exists(f_serv): os.remove(f_serv)
                    if os.path.exists(f_enc): os.remove(f_enc)

elif menu == "Reporte Diario":
    st.title("📋 Reporte Diario Operativo")
    st.info("Registre las actividades y evidencias del día.")
    
    with st.form("form_reporte_diario"):
        c1, c2 = st.columns(2)
        empresa_rd = c1.selectbox("Empresa / Mandante", ["Salmones Blumar", "Salmones Blumar Magallanes"])
        centro_rd = c2.selectbox("Centro de Cultivo", list(CENTROS_AREAS.keys()))
        fecha_rd = c1.date_input("Fecha")
        piloto_rd = c2.text_input("Piloto ROV", value=st.session_state.current_user)
        
        c3, c4 = st.columns(2)
        hora_inicio_rd = c3.time_input("Hora Inicio Jornada", value=datetime.time(8, 0))
        hora_termino_rd = c4.time_input("Hora Término Jornada", value=datetime.time(18, 0))
        
        ponton_rd = c3.text_input("Nombre Pontón")
        area_rd = c4.text_input("Área Geográfica", value=CENTROS_AREAS[centro_rd])
        condicion_puerto_rd = c3.selectbox("Condición de Puerto", ["Abierto", "Cerrado para Embarcaciones Menores", "Cerrado Total"])
        st.session_state.encargado_rd = c4.text_input("Encargado de Centro")
        
        st.write("---")
        st.subheader("Desarrollo Operativo")
        jaula_rd = st.text_input("Estructura/Jaula Intervenida (Ej. Jaula 104, Línea fondeo Norte)")
        tarea_rd = st.text_area("Descripción de Tareas Realizadas (Detallado)")
        evidencia_img_rd = st.file_uploader("Evidencia Fotográfica del Trabajo o SITPORT", type=["jpg", "png", "jpeg"])
        
        st.write("---")
        st.subheader("Cuadro de Firmas")
        from streamlit_drawable_canvas import st_canvas
        st.write("Firma Piloto ROV")
        firma_piloto_rd = st_canvas(fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000000", background_color="#EEEEEE", height=100, drawing_mode="freedraw", key="f_rd_1")
        st.write("Firma Encargado Centro")
        firma_encargado_rd = st_canvas(fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000000", background_color="#EEEEEE", height=100, drawing_mode="freedraw", key="f_rd_2")
        
        # ESPACIADOR AJUSTADO A 53px 
        st.markdown("<div style='height: 53px;'></div>", unsafe_allow_html=True)
        
        # BOTON MODIFICADO PARA SOLO GUARDAR Y DESCARGAR
        submit_rd = st.form_submit_button("GENERAR Y GUARDAR REPORTE DIARIO", type="primary", use_container_width=True)
        
    if submit_rd:
        barra_rd = st.progress(0, text="⚙️ Generando PDF...")
        
        # Generar Folio Correlativo (Cuenta reportes históricos)
        fecha_str = datetime.date.today().strftime("%Y%m%d")
        try:
            res_count = supabase.table('reportes_history').select('id', count='exact').execute()
            correlativo = res_count.count + 1
        except:
            correlativo = len(st.session_state.local_reportes_history) + 1
        folio_str = f"N° RD-{fecha_str}-{correlativo:04d}"
        
        try:
            # PDF_Trident para asegurar el sello en el footer
            pdf_rd = PDF_Trident(); pdf_rd.add_page()
            pdf_rd.set_draw_color(180, 180, 180)
            
            # BUSCA Y COLOCA LOGO INCINEL (LOGO2)
            logo_pdf_rd = "logo2.png" if os.path.exists("logo2.png") else "logo2.jpg" if os.path.exists("logo2.jpg") else "logo.png"
            if os.path.exists(logo_pdf_rd): pdf_rd.image(logo_pdf_rd, x=10, y=8, h=20)
            
            pdf_rd.set_y(32); pdf_rd.set_font("Arial", "B", 15)
            pdf_rd.set_fill_color(15, 55, 105); pdf_rd.set_text_color(255, 255, 255)
            pdf_rd.cell(0, 10, "REPORTE DIARIO DE OPERACIONES - ROV", border=1, ln=True, align="C", fill=True)
            
            # Sello de Auditoría e Info del Folio
            fecha_hora_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pdf_rd.set_font("Arial", "I", 8); pdf_rd.set_text_color(128, 128, 128)
            pdf_rd.cell(0, 6, f"Folio: {folio_str} | Sello de Auditoría Inmutable: Generado el {fecha_hora_actual} por {piloto_rd}", border=0, ln=True, align="C")
            pdf_rd.ln(3)
            
            pdf_rd.set_fill_color(15, 55, 105); pdf_rd.set_text_color(255, 255, 255)
            pdf_rd.set_font("Arial", "B", 10); pdf_rd.cell(190, 8, "1. DATOS GENERALES", border=1, ln=True, fill=True)
            pdf_rd.set_text_color(0, 0, 0)
            
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Fecha:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(65, 8, str(fecha_rd), border=1)
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Rango Horario:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(65, 8, f"{hora_inicio_rd} - {hora_termino_rd}", border=1, ln=True)
            
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Piloto ROV:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(65, 8, piloto_rd, border=1)
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Nombre Ponton:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(65, 8, ponton_rd, border=1, ln=True)
            
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Empresa:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(65, 8, empresa_rd, border=1)
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Centro Cultivo:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(65, 8, centro_rd, border=1, ln=True)

            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Area Asignada:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(65, 8, area_rd, border=1)
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Condicion Puerto:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(65, 8, condicion_puerto_rd, border=1, ln=True)
            
            # Restauración: Encargado de Centro y Correo Centro
            correo_centro_rd = CENTROS_CORREOS.get(centro_rd, 'No registrado')
            encargado_val_rd = str(st.session_state.get('encargado_rd', 'No registrado'))
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Encargado Centro:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(160, 8, encargado_val_rd[:80], border=1, ln=True)
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(30, 8, "Correo Centro:", border=1); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(160, 8, correo_centro_rd[:80], border=1, ln=True)

            pdf_rd.ln(5)
            pdf_rd.set_fill_color(15, 55, 105); pdf_rd.set_text_color(255, 255, 255)
            pdf_rd.set_font("Arial", "B", 10); pdf_rd.cell(190, 8, "2. DETALLE OPERATIVO", border=1, ln=True, fill=True)
            pdf_rd.cell(190, 8, "Estructura Intervenida:", border=1, ln=True, fill=True)
            pdf_rd.set_text_color(0, 0, 0); pdf_rd.set_font("Arial", "", 9); pdf_rd.cell(190, 8, str(jaula_rd), border=1, ln=True)
            
            pdf_rd.set_fill_color(15, 55, 105); pdf_rd.set_text_color(255, 255, 255)
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(190, 8, "Descripcion de la Tarea Realizada:", border=1, ln=True, fill=True)
            pdf_rd.set_text_color(0, 0, 0); pdf_rd.set_font("Arial", "", 9)
            pdf_rd.multi_cell(190, 6, tarea_rd, border=1)
            
            pdf_rd.ln(4)
            pdf_rd.set_fill_color(15, 55, 105); pdf_rd.set_text_color(255, 255, 255)
            pdf_rd.set_font("Arial", "B", 10); pdf_rd.cell(190, 8, "3. CUADRO DE FIRMAS RESPONSABLES", border=1, ln=True, fill=True)
            pdf_rd.set_text_color(0, 0, 0)
            pdf_rd.cell(95, 22, "", border=1); pdf_rd.cell(95, 22, "", border=1, ln=True)
            id_firmas_rd = uuid.uuid4().hex[:8]; f_pil_rd = f"f_p_rd_{id_firmas_rd}.jpg"; f_enc_rd = f"f_e_rd_{id_firmas_rd}.jpg"
            if procesar_firma(firma_piloto_rd, f_pil_rd): pdf_rd.image(f_pil_rd, x=35, y=pdf_rd.get_y()-20, w=45, h=15)
            if procesar_firma(firma_encargado_rd, f_enc_rd): pdf_rd.image(f_enc_rd, x=130, y=pdf_rd.get_y()-20, w=45, h=15)
            pdf_rd.set_font("Arial", "B", 9); pdf_rd.cell(95, 8, "Firma Piloto ROV", border=1, align="C"); pdf_rd.cell(95, 8, "Firma Encargado de Centro", border=1, ln=True, align="C")
            
            # Agregar foto de evidencia si existe
            if evidencia_img_rd:
                pdf_rd.add_page()
                pdf_rd.set_draw_color(180, 180, 180)
                pdf_rd.set_font("Arial", "B", 11)
                pdf_rd.set_fill_color(15, 55, 105); pdf_rd.set_text_color(255, 255, 255)
                pdf_rd.cell(190, 10, "EVIDENCIA FOTOGRAFICA Y/O ESTADO DE PUERTO", border=1, ln=True, fill=True)
                pdf_rd.set_text_color(0, 0, 0)
                
                temp_img_path = f"temp_rd_{uuid.uuid4().hex[:8]}.jpg"
                with open(temp_img_path, "wb") as f:
                    f.write(evidencia_img_rd.getbuffer())
                
                img_pil = Image.open(temp_img_path)
                w_orig, h_orig = img_pil.size
                ratio = w_orig / h_orig
                w_pdf = 160; h_pdf = w_pdf / ratio
                if h_pdf > 200: h_pdf = 200; w_pdf = h_pdf * ratio
                
                x_pos = (210 - w_pdf) / 2
                pdf_rd.image(temp_img_path, x=x_pos, y=pdf_rd.get_y()+5, w=w_pdf, h=h_pdf)
                os.remove(temp_img_path)

            pdf_filename_rd = f"RD_{centro_rd.replace(' ', '_')}_{fecha_rd}.pdf"
            pdf_rd.output(pdf_filename_rd, 'F')
            barra_rd.progress(50, text="PDF Generado. Guardando en Servidor...")

            # Subir a Supabase
            if supabase:
                try:
                    with open(pdf_filename_rd, "rb") as f:
                        supabase.storage.from_("pdfs").upload(f"rd/{pdf_filename_rd}", f, {"content-type": "application/pdf"})
                    url_pdf_rd_nube = supabase.storage.from_("pdfs").get_public_url(f"rd/{pdf_filename_rd}")
                    supabase.table("reportes_history").insert({
                        "tipo": "RD", "centro": centro_rd, "fecha": str(fecha_rd), 
                        "piloto": piloto_rd, "pdf_url": url_pdf_rd_nube
                    }).execute()
                except Exception as e:
                    st.warning(f"No se pudo guardar en el historial en la nube: {e}")
            
            barra_rd.progress(100, text="¡Completado! Listo para descarga.")
            st.success("Reporte Diario generado correctamente.")
            
            with open(pdf_filename_rd, "rb") as f:
                st.download_button("📥 Descargar Reporte Diario (PDF)", f, file_name=pdf_filename_rd, mime="application/pdf")
            
            if st.button("Crear Nuevo Reporte", type="secondary"):
                st.rerun()

        except Exception as e:
            st.error(f"Error procesando Reporte Diario: {e}")
        finally:
            if os.path.exists(f_pil_rd): os.remove(f_pil_rd)
            if os.path.exists(f_enc_rd): os.remove(f_enc_rd)

st.sidebar.write("---")
st.sidebar.caption("TechTrident © 2026")
