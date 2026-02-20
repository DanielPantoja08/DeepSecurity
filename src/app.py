import streamlit as st
import cv2
import numpy as np
from core.detector import FaceDetector
from core.recognizer import FaceRecognizer
from PIL import Image
import os

st.set_page_config(page_title="DeepSecurity AI", layout="wide")

st.title("🛡️ DeepSecurity - Sistema de Identificación")

# Initialization
@st.cache_resource
def load_models():
    return FaceDetector(), FaceRecognizer()

detector, recognizer = load_models()

# Sidebar for Navigation
menu = ["Reconocimiento en tiempor real.", "Administrar Identidades", "Informacion del Sistema"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Reconocimiento en tiempor real.":
    st.header("📹 Identificación en Tiempo Real")
    
    run = st.checkbox('Iniciar Cámara', value=False)
    FRAME_WINDOW = st.image([])
    camera = cv2.VideoCapture(0)

    while run:
        ret, frame = camera.read()
        if not ret:
            st.error("No se pudo acceder a la cámara.")
            break
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        faces = detector.detect_faces(frame)

        for face_obj in faces:

            x, y, w, h = face_obj['box']
            #x, y, w, h = face_obj["box"]["x"], face_obj["box"]["y"], face_obj["box"]["w"], face_obj["box"]["h"]
            
            # Extract and recognize
            face_img = frame[y:y+h, x:x+w]
            if face_img.size > 0:
                # Use the new find_identity method
                name, distance = recognizer.find_identity(face_img)
                label = f"{name} ({1-distance:.2f})"
                color = (0, 255, 0) if name != "Unknown" else (255, 0, 0)
            else:
                label = "Unknown"
                color = (255, 0, 0)

            # Draw (Using PIL because streamlit handles RGB better)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 4)
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        FRAME_WINDOW.image(frame)
    else:
        st.write("Cámara detenida.")
        camera.release()

elif choice == "Administrar Identidades":
    st.header("👥 Gestión de Identidades")
    
    tab1, tab2 = st.tabs(["Listar Identidades", "Registrar Nueva"])
    
    with tab1:
        st.subheader("Registros en Base de Datos")
        if not os.path.exists("db/faces"):
            st.info("No hay identidades registradas.")
        else:
            names = [d for d in os.listdir("db/faces") if os.path.isdir(os.path.join("db/faces", d))]
            if not names:
                st.info("No hay identidades registradas.")
            else:
                for name in sorted(names):
                    st.write(f"- {name}")
    
    with tab2:
        st.subheader("Registrar Persona")
        new_name = st.text_input("Nombre de la Persona").strip()
        uploaded_files = st.file_uploader("Subir foto(s) del rostro", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
        
        if st.button("Registrar") and new_name and uploaded_files:
            # Create a dedicated folder for the person
            person_dir = os.path.join("db/faces", new_name)
            is_new = not os.path.exists(person_dir)
            
            if is_new:
                os.makedirs(person_dir)
                st.info(f"Creando nuevo perfil para: {new_name}")
            else:
                st.warning(f"La identidad '{new_name}' ya existe. Agregando imágenes al perfil existente.")
            
            saved_count = 0
            for uploaded_file in uploaded_files:
                # Use a timestamp or count to ensure unique filenames
                import time
                timestamp = int(time.time() * 1000)
                ext = os.path.splitext(uploaded_file.name)[1]
                if not ext: ext = ".jpg"
                
                img_path = os.path.join(person_dir, f"face_{timestamp}_{saved_count}{ext}")
                
                # Save the file
                with open(img_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                saved_count += 1
                
            if saved_count > 0:
                st.success(f"¡Se han guardado {saved_count} imágenes para '{new_name}'!")
                
                # Note: DeepFace will rebuild the representation on the next search
                # We need to clear the specific pkl file for VGG-Face
                if os.path.exists("db/faces/representations_vgg_face.pkl"):
                    os.remove("db/faces/representations_vgg_face.pkl")
                    st.info("Caché de modelos actualizado.")
            else:
                st.error("No se pudieron guardar las imágenes.")

elif choice == "Informacion del Sistema":
    st.header("⚙️ Información del Sistema")
    st.write("**Modelos en uso:**")
    st.write("- Detector: MTCNN (DeepFace backend)")
    st.write("- Reconocimiento: VGG-Face")
    st.write("- Base de Datos: Directorio de imágenes (db/faces/)")
    st.write("- Framework UI: Streamlit")
    
    st.markdown("""
    > [!NOTA]
    > Este sistema utiliza una arquitectura modular. Si deseas cambiar el modelo (por ejemplo, a FaceNet o ArcFace), 
    > solo necesitas modificar el archivo `recognizer.py`.
    """)
