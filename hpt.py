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

# Configuración inicial
st.set_page_config(page_title="HPT Operaciones ROV", layout="centered", initial_sidebar_state="collapsed")

datos_empresa = {
    "areas": ["Área Norte", "Área Centro", "Área Sur"],
    "centros": ["Centro Puelche", "Centro Chivato 1", "Centro Elena Norte", "Centro Dring"],
    "pilotos": ["Piloto 1", "Piloto 2", "Piloto 3", "Piloto 4"],
    "tareas": ["Inspección de redes peceras", "Extracción de mortalidad", "Revisión de fondeos"]
}

st.title("Registro HPT - Operaciones ROV")
st.divider()

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

with st.expander("2. MATRIZ RÁPIDA DE RIESGOS"):
    clima_ok = st.radio("¿Condición climática permite la operación?", ("Sí", "No", "N/A"), horizontal=True)
    electrico_ok = st.radio("¿Equipos sin daños eléctricos visibles?", ("Sí", "No", "N/A"), horizontal=True)

st.markdown("### 3. Evidencia y Validación")
foto_entorno = st.file_uploader("Adjuntar foto del entorno/clima", type=['jpg', 'png', 'jpeg'])

st.markdown("**Firma del Piloto**")
firma_canvas = st_canvas(
    stroke_width=2,
    stroke_color="#000000",
    background_color="#EEEEEE",
    height=150,
    width=400,
    drawing_mode="freedraw",
    key="canvas_firma"
)

correo_destino = st.text_input("Correos de destino (Si son varios, separe por coma)")

# Lógica de Generación y Envío
if st.button("GENERAR PDF Y ENVIAR HPT", type="primary", use_container_width=True):
    if area_sel == "Seleccione..." or centro_sel == "Seleccione..." or piloto_sel == "Seleccione...":
        st.error("Faltan datos generales por completar.")
    elif not correo_destino:
        st.error("Debe ingresar al menos un correo de destino.")
    else:
        with st.spinner("Compilando reporte y enviando..."):
            try:
                # 1. Crear el PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, "HERRAMIENTA DE PREVENCION EN TERRENO (HPT) - ROV", ln=True, align="C")
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 10, f"Fecha: {fecha_hpt} | Hora: {hora_hpt}", ln=True)
                pdf.cell(0, 10, f"Area: {area_sel} | Centro: {centro_sel}", ln=True)
                pdf.cell(0, 10, f"Piloto: {piloto_sel} | Tarea: {tarea_sel}", ln=True)
                pdf.line(10, 45, 200, 45)
                
                pdf.cell(0, 10, f"Clima operativo: {clima_ok} | Estado equipos: {electrico_ok}", ln=True)
                
                # Insertar Foto del entorno si existe
                if foto_entorno is not None:
                    foto_img = Image.open(foto_entorno)
                    foto_img.save("foto_temp.jpg")
                    pdf.cell(0, 10, "Evidencia del Entorno:", ln=True)
                    pdf.image("foto_temp.jpg", x=10, w=80)
                    pdf.ln(5) # Espaciado

                # Procesar e insertar la firma
                if firma_canvas.image_data is not None:
                    img_data = firma_canvas.image_data
                    firma_img = Image.fromarray((img_data).astype('uint8'), mode='RGBA')
                    # Convertir fondo transparente a blanco para FPDF
                    fondo_blanco = Image.new("RGB", firma_img.size, (255, 255, 255))
                    fondo_blanco.paste(firma_img, mask=firma_img.split()[3])
                    fondo_blanco.save("firma_temp.jpg")
                    
                    pdf.set_y(-60) # Posicionar en la parte inferior de la hoja
                    pdf.cell(0, 10, "Firma de Responsabilidad:", ln=True)
                    pdf.image("firma_temp.jpg", x=10, w=60)

                # Guardar el PDF generado
                archivo_pdf = f"HPT_{centro_sel}_{fecha_hpt}.pdf"
                pdf.output(archivo_pdf)

                # 2. Enviar el Correo Electrónico
                remitente = st.secrets["EMAIL_USER"]
                password = st.secrets["EMAIL_PASS"]
                
                msg = MIMEMultipart()
                msg['From'] = remitente
                msg['To'] = correo_destino
                msg['Subject'] = f"HPT ROV - {centro_sel} - {piloto_sel}"
                msg.attach(MIMEText("Se adjunta el reporte de prevención de riesgos (HPT) previo a inmersión.", 'plain'))

                with open(archivo_pdf, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {archivo_pdf}")
                msg.attach(part)

                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(remitente, password)
                server.send_message(msg)
                server.quit()

                st.success("Reporte generado y enviado correctamente a las jefaturas.")
                
            except Exception as e:
                st.error(f"Error al procesar: {e}")
                st.info("Recuerde configurar los 'Secrets' de Streamlit con sus credenciales de correo.")
