import streamlit as st
import pandas as pd
import datetime
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# 1. Configuración inicial de la página
st.set_page_config(
    page_title="HPT Operaciones ROV - TechTrident",
    page_icon="🔱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Simulación de Base de Datos (Posteriormente se reemplazará por pd.read_excel('base_datos.xlsx'))
datos_empresa = {
    "areas": ["Área Norte", "Área Centro", "Área Sur"],
    "centros": ["Centro Puelche", "Centro Chivato 1", "Centro Elena Norte", "Centro Dring"],
    "pilotos": ["Piloto 1", "Piloto 2", "Piloto 3", "Piloto 4"],
    "tareas": [
        "Inspección de redes peceras",
        "Inspección de redes loberas",
        "Extracción de mortalidad",
        "Revisión de fondeos",
        "Recuperación de objetos"
    ]
}

# 3. Encabezado de la Aplicación
st.title("Registro HPT - Operaciones ROV")
st.markdown("### TechTrident Soluciones Digitales")
st.divider()

# 4. Sección: Datos Generales (Uso de st.expander para comprimir la interfaz)
with st.expander("1. DATOS GENERALES", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        fecha_hpt = st.date_input("Fecha de Ejecución", datetime.date.today())
        area_sel = st.selectbox("Área Operativa", ["Seleccione..."] + datos_empresa["areas"])
        piloto_sel = st.selectbox("Piloto a Cargo", ["Seleccione..."] + datos_empresa["pilotos"])
        
    with col2:
        hora_hpt = st.time_input("Hora de Inicio", datetime.datetime.now().time())
        centro_sel = st.selectbox("Centro de Cultivo", ["Seleccione..."] + datos_empresa["centros"])
        tarea_sel = st.selectbox("Tarea a Realizar", ["Seleccione..."] + datos_empresa["tareas"])

# 5. Sección: CheckList EPP Obligatorio
with st.expander("2. ELEMENTOS DE PROTECCIÓN PERSONAL (EPP)"):
    st.write("Verificación de elementos obligatorios para tránsito en pontón:")
    epp_col1, epp_col2 = st.columns(2)
    
    with epp_col1:
        epp_casco = st.checkbox("Casco de seguridad")
        epp_chaleco = st.checkbox("Chaleco salvavidas")
        epp_calzado = st.checkbox("Calzado de seguridad")
        
    with epp_col2:
        epp_guantes = st.checkbox("Guantes anticorte/cabritilla")
        epp_lentes = st.checkbox("Lentes de seguridad (UV)")
        epp_traje = st.checkbox("Traje de agua / Ropa térmica")

# 6. Sección: Matriz de Riesgos y Entorno
with st.expander("3. MATRIZ DE RIESGOS PREVIO A INMERSIÓN"):
    st.markdown("**Evaluación del Entorno**")
    clima_ok = st.radio("¿Condiciones climáticas y de corriente permiten la operación segura del ROV?", ("Sí", "No", "N/A"), horizontal=True)
    barandas_ok = st.radio("¿Pasarelas y barandas libres de obstáculos y en buen estado?", ("Sí", "No", "N/A"), horizontal=True)
    
    st.markdown("**Evaluación de Equipos**")
    electrico_ok = st.radio("¿Generador, controlador y umbilical sin daños visibles y aislados de humedad?", ("Sí", "No", "N/A"), horizontal=True)
    winche_ok = st.radio("¿Winche asegurado y libre de riesgo de atrapamiento?", ("Sí", "No", "N/A"), horizontal=True)
    
    st.markdown("**Coordinación**")
    coordinacion_ok = st.radio("¿Maniobra coordinada con alimentadores/embarcaciones para evitar enredos?", ("Sí", "No", "N/A"), horizontal=True)

# 7. NUEVA SECCIÓN: Evidencia y Firmas
with st.expander("4. EVIDENCIA Y FIRMAS", expanded=True):
    st.markdown("**Evidencia Fotográfica**")
    foto_entorno = st.file_uploader("Adjuntar foto del entorno/clima", type=['jpg', 'png', 'jpeg'])

    st.markdown("**Firmas de Responsabilidad**")
    col_firma1, col_firma2 = st.columns(2)
    
    with col_firma1:
        st.write("Firma Piloto a Cargo")
        firma_piloto = st_canvas(
            stroke_width=2,
            stroke_color="#000000",
            background_color="#EEEEEE",
            height=150,
            width=300,
            drawing_mode="freedraw",
            key="canvas_piloto"
        )
        
    with col_firma2:
        st.write("Firma Encargado de Centro")
        firma_encargado = st_canvas(
            stroke_width=2,
            stroke_color="#000000",
            background_color="#EEEEEE",
            height=150,
            width=300,
            drawing_mode="freedraw",
            key="canvas_encargado"
        )
        
    correo_destino = st.text_input("Correos de destino (Si son varios, separe por coma)")

# 8. Lógica de Validación y Envío
st.divider()

# Botón principal de ejecución
if st.button("GENERAR Y ENVIAR HPT", type="primary", use_container_width=True):
    # Validación estricta de campos críticos
    campos_vacios = []
    if area_sel == "Seleccione...": campos_vacios.append("Área Operativa")
    if centro_sel == "Seleccione...": campos_vacios.append("Centro de Cultivo")
    if piloto_sel == "Seleccione...": campos_vacios.append("Piloto a Cargo")
    if tarea_sel == "Seleccione...": campos_vacios.append("Tarea a Realizar")
    
    # Validación de EPP mínimo
    epp_completos = all([epp_casco, epp_chaleco, epp_calzado, epp_guantes, epp_lentes])
    
    if campos_vacios:
        st.error(f"Falta completar los siguientes datos generales: {', '.join(campos_vacios)}")
    elif not epp_completos:
        st.error("Debe confirmar el uso de todos los EPP obligatorios (Casco, Chaleco, Calzado, Guantes, Lentes).")
    elif clima_ok == "No" or electrico_ok == "No":
        st.error("No se puede iniciar la maniobra: Condiciones climáticas adversas o riesgo eléctrico detectado.")
    elif not correo_destino:
        st.error("Debe ingresar al menos un correo electrónico de destino.")
    else:
        with st.spinner("Compilando documento y enviando al servidor de correo..."):
            try:
                # 1. Crear el PDF
                pdf = FPDF()
                pdf.add_page()
                
                # Encabezado
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, "HERRAMIENTA DE PREVENCION EN TERRENO (HPT) - ROV", ln=True, align="C")
                pdf.ln(5)
                
                # Datos Generales
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 8, f"Fecha: {fecha_hpt} | Hora: {hora_hpt}", ln=True)
                pdf.cell(0, 8, f"Area: {area_sel} | Centro: {centro_sel}", ln=True)
                pdf.cell(0, 8, f"Piloto: {piloto_sel} | Tarea: {tarea_sel}", ln=True)
                pdf.line(10, 45, 200, 45)
                pdf.ln(5)
                
                # Matriz
                pdf.cell(0, 8, f"Condiciones climaticas seguras: {clima_ok}", ln=True)
                pdf.cell(0, 8, f"Equipos sin daños electricos: {electrico_ok}", ln=True)
                pdf.cell(0, 8, f"Pasarelas en buen estado: {barandas_ok}", ln=True)
                pdf.cell(0, 8, f"Coordinacion con embarcaciones: {coordinacion_ok}", ln=True)
                pdf.ln(5)
                
                # Procesar Foto
                if foto_entorno is not None:
                    foto_img = Image.open(foto_entorno)
                    # Convertir a RGB por si la imagen tiene canal Alfa (transparencia) o distinto formato
                    foto_img = foto_img.convert("RGB")
                    foto_img.save("foto_temp.jpg")
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 10, "Evidencia del Entorno:", ln=True)
                    pdf.image("foto_temp.jpg", x=10, w=80)
                    pdf.ln(5)
                    
                # Procesar Firmas
                def procesar_firma(canvas_obj, filename):
                    if canvas_obj.image_data is not None:
                        img_data = canvas_obj.image_data
                        firma_img = Image.fromarray((img_data).astype('uint8'), mode='RGBA')
                        # Generar fondo blanco para FPDF
                        fondo_blanco = Image.new("RGB", firma_img.size, (255, 255, 255))
                        fondo_blanco.paste(firma_img, mask=firma_img.split()[3])
                        fondo_blanco.save(filename)
                        return True
                    return False

                # Posicionar firmas en la parte baja de la hoja
                pdf.set_y(-60) 
                
                if procesar_firma(firma_piloto, "firma_piloto.jpg"):
                    pdf.image("firma_piloto.jpg", x=20, w=50)
                if procesar_firma(firma_encargado, "firma_encargado.jpg"):
                    pdf.image("firma_encargado.jpg", x=120, w=50)
                    
                pdf.set_y(-25)
                pdf.set_font("Arial", "B", 10)
                pdf.cell(80, 10, "Firma Piloto", align="C")
                pdf.cell(100, 10, "Firma Encargado", align="C")

                # Guardar PDF temporalmente
                archivo_pdf = f"HPT_{centro_sel.replace(' ', '_')}_{fecha_hpt}.pdf"
                pdf.output(archivo_pdf)

                # 2. Enviar el Correo Electrónico
                remitente = st.secrets["EMAIL_USER"]
                password = st.secrets["EMAIL_PASS"]
                
                msg = MIMEMultipart()
                msg['From'] = remitente
                msg['To'] = correo_destino
                msg['Subject'] = f"Reporte HPT ROV - {centro_sel} - {fecha_hpt}"
                msg.attach(MIMEText("Se adjunta el reporte de Prevención de Riesgos (HPT) previo a inmersión ROV generado desde la plataforma TechTrident.", 'plain'))

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

                st.success(f"HPT generada exitosamente. Documento PDF enviado a {correo_destino}.")
                st.balloons()
                
            except Exception as e:
                st.error(f"Error técnico durante el envío: {e}")
                st.info("Recuerde configurar los 'Secrets' en Streamlit con su EMAIL_USER y EMAIL_PASS.")
