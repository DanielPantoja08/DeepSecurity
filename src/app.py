import streamlit as st
import cv2
import numpy as np
from core.detector import FaceDetector
from core.recognizer import FaceRecognizer
from PIL import Image
import os
import time
from dotenv import load_dotenv
from streamlit_webrtc import webrtc_streamer, RTCConfiguration
import av

load_dotenv()

st.set_page_config(page_title="DeepSecurity AI", layout="wide")

st.title("🛡️ DeepSecurity - Sistema de Identificación")

# Custom CSS to prevent distortion
st.markdown("""
    <style>
    div[data-testid="stVideo"] > video {
        object-fit: contain !important;
    }
    .stImage > img {
        object-fit: contain !important;
    }
    </style>
""", unsafe_allow_html=True)

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
    
    RTC_CONFIGURATION = RTCConfiguration(
        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    def video_frame_callback(frame):
        img = frame.to_ndarray(format="bgr24")
        
        # Convert to RGB for the AI models
        rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        faces = detector.detect_faces(rgb_frame)

        for face_obj in faces:
            x, y, w, h = face_obj['box']
            
            # Extract and recognize (using RGB)
            face_img = rgb_frame[y:y+h, x:x+w]
            if face_img.size > 0:
                name, distance = recognizer.find_identity(face_img)
                label = f"{name} ({1-distance:.2f})"
                # Color in BGR for drawing with OpenCV
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            else:
                label = "Unknown"
                color = (0, 0, 255)

            # Draw on the original BGR frame
            cv2.rectangle(img, (x, y), (x+w, y+h), color, 4)
            cv2.putText(img, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

    webrtc_streamer(
        key="face-recognition",
        video_frame_callback=video_frame_callback,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={
            "video": {
                "width": 1280,
                "height": 720,
                "frameRate": {"ideal": 30, "max": 60},
            },
            "audio": False
        },
        async_processing=True,
        video_html_attrs={
            "style": {"width": "100%", "margin-left": "auto", "margin-right": "auto", "object-fit": "contain"},
            "controls": False,
            "autoPlay": True,
        },
    )

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
        
        st.write("---")
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_files = st.file_uploader("Subir foto(s) del rostro", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
        
        with col2:
            camera_photo = st.camera_input("Tomar foto con la cámara")
        
        # Combine all sources
        all_images = []
        if uploaded_files:
            all_images.extend(uploaded_files)
        if camera_photo:
            all_images.append(camera_photo)
        
        if st.button("Registrar") and new_name and all_images:
            # Create a dedicated folder for the person
            person_dir = os.path.join("db/faces", new_name)
            is_new = not os.path.exists(person_dir)
            
            if is_new:
                os.makedirs(person_dir, exist_ok=True)
                st.info(f"Creando nuevo perfil para: {new_name}")
            else:
                st.warning(f"La identidad '{new_name}' ya existe. Agregando imágenes al perfil existente.")
            
            saved_count = 0
            for img_file in all_images:
                # Use a timestamp or count to ensure unique filenames
                timestamp = int(time.time() * 1000)
                
                # Handle file extension
                ext = ".jpg" # Default
                if hasattr(img_file, 'name') and img_file.name:
                    file_ext = os.path.splitext(img_file.name)[1]
                    if file_ext:
                        ext = file_ext
                
                img_path = os.path.join(person_dir, f"face_{timestamp}_{saved_count}{ext}")
                
                # Save the file
                with open(img_path, "wb") as f:
                    f.write(img_file.getbuffer())
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
