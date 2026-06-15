import streamlit as st
import pandas as pd
import datetime

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

# 7. Lógica de Validación y Envío
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
    else:
        # Aquí se insertará el motor de PDF (FPDF) y envío de correo (SMTP)
        st.success(f"HPT generada exitosamente. Documento PDF enviado a Jefatura del centro {centro_sel}.")
        st.balloons()