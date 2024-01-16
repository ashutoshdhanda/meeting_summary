import os
import streamlit as st
import requests
import tempfile
import base64
import json
from dotenv import load_dotenv
from htmlTemplates import css, bot_template, user_template, scrollable_box_css, response_css

def show_eula():
    style = """
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .scrollable-box {
                height: 400px;
                overflow-y: scroll;
                background-color: rgba(255, 255, 255, 0.5);
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 20px;
                white-space: pre-wrap;
            }
        </style>
    """
    st.markdown(style, unsafe_allow_html=True)

    st.title("End User License Agreement")

    eula_text = """Al utilizar nuestra Aplicación Web basada en Inteligencia Artificial Generativa, usted acepta los siguientes términos y condiciones. Esta aplicación utiliza tecnología de IA generativa avanzada y, como usuario, debe entender que las interacciones con dicha tecnología pueden producir resultados impredecibles, y que el contenido generado debe usarse con discreción. Usted es responsable de garantizar que los datos proporcionados no infrinjan los derechos de privacidad o propiedad intelectual de terceros, y debe estar consciente de que, a pesar de nuestros esfuerzos por asegurar la aplicación y los datos de los usuarios, no se puede garantizar una seguridad completa contra amenazas cibernéticas y accesos no autorizados. Los derechos de propiedad intelectual de la aplicación y el contenido generado pertenecen a nuestra empresa, y su uso no le otorga la propiedad de ningún derecho intelectual relacionado con la aplicación o su contenido. No nos hacemos responsables de daños directos, indirectos, incidentales o consecuentes derivados de su uso de la aplicación, incluyendo aquellos relacionados con inexactitudes, contenido ofensivo o violaciones de seguridad. El uso indebido de la aplicación o su contenido generado puede resultar en la terminación de su acceso. Nos reservamos el derecho de modificar estos términos y condiciones en cualquier momento, y su uso continuado de la aplicación constituye su consentimiento a dichos cambios."""  # Add your EULA text here

    st.markdown(
        f'<div class="scrollable-box">{eula_text}</div>', unsafe_allow_html=True
    )

    if st.button("De acuerdo"):
        st.session_state["eula_accepted"] = True
        st.rerun()


def init():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "run" not in st.session_state:
        st.session_state.run = None

    if "file_ids" not in st.session_state:
        st.session_state.file_ids = []
    
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')


def get_image_summary(encoded_images, endpoint, headers):
    image_content = [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image}"
            }
        }
        for image in encoded_images
    ]

    data = { 
        "messages": [ 
            { 
                "role": "system", 
                "content": "I have attached an image of a Business Process Model. Please analyze it in detail and provide a comprehensive description of each element and phase. This should include identifying the workflows, decision points, roles of executors, and the inputs and outputs of each activity. Also, create a table with columns for ID, Name Activity, Executor, Type of Activity, Short Description, Input, and Output, populated with data from the diagram. After that, offer recommendations for optimizing this process, focusing on aspects like redundant steps, potential bottlenecks, and opportunities for implementing automation technologies or management software to enhance process efficiency and effectiveness. Please respond in Spanish." 
            }, 
            { 
                "role": "user", 
                "content": [  
                    { 
                        "type": "text", 
                        "text": "Perform a detailed analysis of the attached Business Process Model image. Describe each element and phase, noting the workflows, decision points, executor roles, and the inputs and outputs of each activity. Then, prepare a table with the following columns: ID, Name Activity, Executor, Type of Activity, Short Description, Input, Output, using information from the diagram. Provide recommendations for process optimization, highlighting redundant steps, bottlenecks, and opportunities for automation technologies or management software improvements." 
                    },
                    *image_content
                ] 
            } 
        ], 
        "max_tokens": 4096 
    }
    response = requests.post(endpoint, headers=headers, data=json.dumps(data))
    return response

def main():

    load_dotenv()

    api_base = os.getenv("API_BASE") 
    deployment_name = os.getenv("DEPLOYMENT_NAME")
    API_KEY = os.getenv("AZURE_OPENAI_KEY_VISION")
    base_url = f"{api_base}openai/deployments/{deployment_name}" 
    headers = {   
        "Content-Type": "application/json",   
        "api-key": API_KEY
    }

    endpoint = f"{base_url}/chat/completions?api-version=2023-12-01-preview"
    st.set_page_config(page_title="Generar resumen del imagen", page_icon=":eye:", layout="wide")
        # Define CSS to increase text size and adjust container width
    custom_css = """
        <style>
            .big-text {
                font-size: 20px; /* Adjust text size as needed */
            }
            .wide-container {
                max-width: 95%; /* You can adjust this as needed */
            }
        </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
    # Hide the Streamlit footer
    hide_streamlit_style = """
                <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    st.write(css, unsafe_allow_html=True)

    # Initialize conversation and chat history if not present
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    # Initialize a session state variable
    #if 'upload_size_limit' not in st.session_state:
        #st.session_state.upload_size_limit = 20

    # Initialize a variable to hold the formatted message
    formatted_message = None

    st.header("Analizar imágenes con GPT4v :eye:")

    st.markdown(
        """
Paso 1: Cargue imágenes de BPM. Es recomendable subir imagen de leyenda del proceso para que el modelo entienda mejor su diagrama. \n
Paso 2: Si carga una imagen de la leyenda, manténgala después de la imagen principal del diagrama. \n 
Paso 3: Una vez seleccionado, haga clic en el botón de proceso y los resultados aparecerán a continuación.""")
    with st.sidebar:

        uploaded_image = st.file_uploader("Subir imagen: (20 MB Max)", type=['jpeg', 'gif', 'png', 'webp'], accept_multiple_files=True)
        if st.button("Procesar"):
                with st.spinner("Procesando..."):
                    if uploaded_image:
                        temp_dir = tempfile.mkdtemp()
                        encoded_images = []  # List to store encoded images
                        for image in uploaded_image:
                            image_path = os.path.join(temp_dir, image.name)
                            with open(image_path, "wb") as f:
                                f.write(image.getvalue())
                            base64_image = encode_image(image_path)
                            encoded_images.append(base64_image)
                        try:
                            response = get_image_summary(encoded_images, endpoint, headers)
                            if response.ok:
                                response_json = response.json()
                                messages = response_json['choices'][0]['message']['content']
                                formatted_message = bot_template.replace("{{MSG}}", messages)
                                #filename = "saved_string.txt"
                                #with open(filename, 'w') as file:
                                    #file.write(formatted_message)
                            else:
                                st.error(f"Error: {response.status_code} - {response.text}")
                        except Exception as e:
                            #e = RuntimeError('Error!')
                            st.exception(e)
                    else:
                        st.error("No subiste imagen!", icon="🚨")

    if formatted_message:
        st.markdown(response_css, unsafe_allow_html=True)
        # Use a container or just st.markdown directly to display the message on the main page
        #st.markdown('<div class="chat-container wide-container">', unsafe_allow_html=True)
        st.markdown('<div class="response-container"><table class="response-table">', unsafe_allow_html=True)
        #st.markdown(api_response_content)  # where `api_response_content` is the HTML content from the API response
        st.markdown(f'<div class="big-text">{formatted_message}</div>', unsafe_allow_html=True)
        st.markdown('</table></div>', unsafe_allow_html=True)
    else:
        pass

if __name__ == '__main__':
    if "eula_accepted" not in st.session_state:
        st.session_state["eula_accepted"] = False

    if st.session_state["eula_accepted"]:
        main()
    else:
        show_eula()