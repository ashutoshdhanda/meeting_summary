import os
from dotenv import load_dotenv
from htmlTemplates import css, bot_template
import streamlit as st
import docx
from streamlit import components
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import whisper
import base64
from openai import AzureOpenAI
import uuid

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

def get_base64_encoded_data(filename):
    with open(filename, "rb") as file:
        # Read the file content
        data = file.read()
        # Encode the data to Base64
        base64_encoded_data = base64.b64encode(data)
        base64_message = base64_encoded_data.decode('utf-8')
        return base64_message

def create_download_link(filename, download_name):
    base64_data = get_base64_encoded_data(filename)
    href = f'<a href="data:file/txt;base64,{base64_data}" download="{download_name}">Descargar transcripción.</a>'
    st.markdown(href, unsafe_allow_html=True)

def process_file(uploaded_file, unique_id):
    original_name = uploaded_file.name
    extension = os.path.splitext(original_name)[1]
    temp_file_path = f"temp_file_{unique_id}{extension}"

    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return temp_file_path

def extract_audio(video_file_path, unique_id):
    temp_audio_path = f"temp_audio_{unique_id}.wav"

    with st.spinner("Extracting audio..."):
        video = VideoFileClip(video_file_path)
        video.audio.write_audiofile(
            temp_audio_path, codec="pcm_s16le", ffmpeg_params=["-ar", "16000"]
        )

    return temp_audio_path


def transcribe_audio(audio_path):
    with st.spinner("Transcribing audio..."):
        progress_bar = st.progress(0)
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        progress_bar.progress(100)

    # Extract the transcription text from the result
    transcribed_text = result["text"]

    # Specify the path for the text file where you want to save the transcription
    text_file_path = audio_path.replace(".wav", ".txt")

    # Write the transcription to the text file
    with open(text_file_path, "w") as text_file:
        text_file.write(transcribed_text)

    create_download_link(text_file_path, "transcription.txt")

    return transcribed_text


def generate_meeting_summary(transcription, client, prompt):
    try:
        response = client.chat.completions.create(
            model="sopa",
            messages=[
                {
                    "role": "system",
                    "content": "Provide some context and/or instructions to the model",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0
        )
        summary = response.choices[0].message.content
        st.session_state.conversation_history.extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": summary}
        ])
        return summary
    except Exception as e:
        st.write(e)
        return str(e)

def handle_user_query(user_query, client):
    st.session_state.conversation_history.append({"role": "user", "content": user_query})

    response = client.chat.completions.create(
        model="sopa",
        messages=st.session_state.conversation_history[-10:]  # Adjust as needed
    )

    st.session_state.conversation_history.append({"role": "assistant", "content": response.choices[0].message.content})
    return response.choices[0].message.content


def create_chat_message(message, template):
    return template.replace("{{MSG}}", message)

def main():
    load_dotenv()
    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version="2023-05-15",
    )

    st.set_page_config(page_title="Chat with meetings", page_icon="📺")
    st.write(css, unsafe_allow_html=True)

    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "meeting_info" not in st.session_state:
        st.session_state.meeting_info = None

    st.header("Chat with Videos 📺")
    st.markdown(
        """
Paso 1: Subir transcript / video de reunion. \n
Paso 2: Seleccionar el tipo de reunion y modificar las instrucciones, de ser necesario. \n 
Paso 3: Presione el boton de procesar. \n
Paso 4: Espere a que el modelo genere la minuta. Los resultados aparecerán a continuación. \n
""")
    transcription = ""
    default_value = "A continuación se muestra la transcripción de un archivo de audio de una reunión reciente. Su tarea es analizar el texto y generar notas concisas de la reunión que resuma los puntos clave discutidos. Además, cree una lista de participantes basada en los nombres y títulos mencionados durante la reunión.\nTranscripción del archivo de audio:\n{transcription}\nBasado en la transcripción anterior, genere lo siguiente:\n1. Un resumen de la reunión, destacando los principales temas discutidos, las decisiones tomadas y las acciones a tomar.\n2. Una lista de participantes, incluidos sus nombres y funciones o títulos mencionados en la reunión."
    uploaded_file = st.file_uploader(
    "Upload a video / transcription file", type=["mp4", "avi", "mov", "mkv", "vtt", "txt", "docx"]
)
    button = None
    if uploaded_file is not None:
        unique_id = str(uuid.uuid4())
        temp_file_path = process_file(uploaded_file, unique_id)
        if uploaded_file.type.startswith("video/"):
            if st.session_state.meeting_info is None:
                audio_path = extract_audio(temp_file_path, unique_id)
                transcription = transcribe_audio(audio_path)
        elif uploaded_file.type.startswith("text/"):
            if st.session_state.meeting_info is None:
                transcription = uploaded_file.getvalue().decode('utf-8')
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            if st.session_state.meeting_info is None:
                doc = docx.Document(uploaded_file)
                full_text = [paragraph.text for paragraph in doc.paragraphs]
                transcription = "\n".join(full_text)
        elif uploaded_file.type.startswith("application/octet-stream"):
            if st.session_state.meeting_info is None:
                # Check if the file extension is .vtt
                file_name = uploaded_file.name
                file_extension = os.path.splitext(file_name)[1].lower()
                if file_extension == '.vtt':
                    # Extracting dialogues from the VTT file and concatenating them into a continuous text
                    vtt_content = uploaded_file.getvalue().decode("utf-8").splitlines()
                    dialogues = []
                    is_dialogue_line = False  # Flag to track if a line is part of a dialogue
                    for line in vtt_content:
                        # Skip empty lines and lines with metadata (like timestamps and identifiers)
                        if line.strip() and not '-->' in line and not line[0].isalnum():
                            is_dialogue_line = True
                        elif line.strip() == '':
                            is_dialogue_line = False

                        # If it's a dialogue line, add it to the dialogues list
                        if is_dialogue_line:
                            dialogues.append(line.strip())

                    # Joining the dialogues into a continuous text
                    transcription = ' '.join(dialogues)
        else:
            st.error("Please upload a valid file.")
        
        option = st.selectbox(
            "Que tipo de reunion es? 📺",
            ("Session de trabajo", "Estatus", "Capacitacion", "Presentacion", "Otro"),
            index=None,
            placeholder="Seleccionar tipo de reunion...",
        )

        if option is not None:
            if option == "Session de trabajo":
                prompt_session_trabajo = "Dada la transcripción de una reunión reciente, su tarea es analizar el contenido y elaborar un documento que resuma eficientemente los aspectos más importantes discutidos durante la sesión. Utilice la siguiente estructura para su análisis:\n\n- **Sesión de Trabajo:** Incluya una breve descripción de la naturaleza y objetivos de la reunión.\n- **Tema de la reunión:** Especifique el tema principal o los temas cubiertos.\n- **Puntos clave discutidos:** Identifique y resuma los puntos clave discutidos, incluyendo cualquier debate significativo o intercambio de ideas.\n- **Decisiones tomadas:** Liste las decisiones concretas que se tomaron durante la reunión, junto con cualquier contexto relevante.\n- **Tareas asignadas a cada participante:** Enumere las tareas o acciones asignadas, especificando a quién se le asignó cada tarea y cualquier plazo relevante.\n\nBasado en la transcripción proporcionada bajo `{transcription}`, genere lo siguiente:\n1. Un resumen de la reunión, destacando los principales temas discutidos, las decisiones tomadas, y las acciones a tomar.\n2. Una lista de participantes, incluyendo sus nombres y funciones o títulos mencionados en la reunión.\n\nPor favor, asegúrese de que su respuesta sea concisa, clara y organizada, facilitando la comprensión rápida de los resultados de la reunión."
                with st.expander("Instrucciones:"):
                    prompt = st.text_area("Estaré trabajando de acuerdo con las siguientes instrucciones. Puedes cambiarlos, si quieres..", value=prompt_session_trabajo, height=300)
                    #prompt = st.text_area("Default Prompt", value=default_value, height=300)
                    if st.button('Cambiar :test_tube:'):
                        st.success("Prompt cambiado exitosamente!")
                        try:
                            if transcription != "":
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write("Prompt changed")
                                #st.write(prompt)  # Display the formatted prompt
                            else:
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write(prompt)
                        except KeyboardInterrupt as e:
                            st.error(f"Missing a value for the placeholder: {e}")
                button = st.button('Procesar :sparkles:')

            elif option == "Estatus":
                prompt_estatus = "En base a la transcripción de una reciente sesión de capacitación, su misión es sintetizar la información clave y estructurar un documento que refleje de manera precisa y eficiente los aprendizajes y discusiones importantes de la sesión. Por favor, siga el siguiente formato para su análisis:\n\n- **Capacitación:** Ofrezca una introducción general al objetivo y al ámbito de la sesión de capacitación.\n- **Tema de la reunión:** Detalle el tema principal de la capacitación y cualquier subtema relevante abordado.\n- **Conceptos clave enseñados:** Resuma los conceptos fundamentales que se impartieron, incluyendo metodologías, teorías o prácticas específicas.\n- **Preguntas y respuestas destacadas:** Proporcione un resumen de las interacciones más significativas, incluyendo preguntas clave de los participantes y las respuestas proporcionadas.\n- **Material de seguimiento proporcionado:** Liste cualquier recurso o material de seguimiento que se haya distribuido para profundizar en los temas tratados.\n\nCon base en la transcripción facilitada `{transcription}`, por favor, elabore lo siguiente:\n1. Un resumen conciso de la sesión de capacitación, resaltando los temas tratados, los conceptos clave enseñados, y las interacciones relevantes entre los instructores y participantes.\n2. Una compilación de los materiales de seguimiento proporcionados durante la sesión, si los hay.\n\nAsegúrese de que su documento sea claro, bien estructurado, y útil para quienes busquen entender los resultados y el contenido de la capacitación."
                with st.expander("Instrucciones:"):
                    prompt = st.text_area("Estaré trabajando de acuerdo con las siguientes instrucciones. Puedes cambiarlos, si quieres..", value=prompt_estatus, height=300)
                    #prompt = st.text_area("Default Prompt", value=default_value, height=300)
                    if st.button('Cambiar :test_tube:'):
                        st.success("Prompt cambiado exitosamente!")
                        try:
                            if transcription != "":
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write("Prompt changed")
                                #st.write(prompt)  # Display the formatted prompt
                            else:
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write(prompt)
                        except KeyboardInterrupt as e:
                            st.error(f"Missing a value for the placeholder: {e}")
                button = st.button('Procesar :sparkles:')
            
            elif option == "Capacitacion":
                prompt_capacitacion = "En base a la transcripción de una reciente sesión de capacitación, su misión es sintetizar la información clave y estructurar un documento que refleje de manera precisa y eficiente los aprendizajes y discusiones importantes de la sesión. Por favor, siga el siguiente formato para su análisis:\n\n- **Capacitación:** Ofrezca una introducción general al objetivo y al ámbito de la sesión de capacitación.\n- **Tema de la reunión:** Detalle el tema principal de la capacitación y cualquier subtema relevante abordado.\n- **Conceptos clave enseñados:** Resuma los conceptos fundamentales que se impartieron, incluyendo metodologías, teorías o prácticas específicas.\n- **Preguntas y respuestas destacadas:** Proporcione un resumen de las interacciones más significativas, incluyendo preguntas clave de los participantes y las respuestas proporcionadas.\n- **Material de seguimiento proporcionado:** Liste cualquier recurso o material de seguimiento que se haya distribuido para profundizar en los temas tratados.\n\nCon base en `{transcription}`, por favor, elabore lo siguiente:\n1. Un resumen conciso de la sesión de capacitación, resaltando los temas tratados, los conceptos clave enseñados, y las interacciones relevantes entre los instructores y participantes.\n2. Una compilación de los materiales de seguimiento proporcionados durante la sesión, si los hay.\n\nAsegúrese de que su documento sea claro, bien estructurado, y útil para quienes busquen entender los resultados y el contenido de la capacitación."
                with st.expander("Instrucciones:"):
                    prompt = st.text_area("Estaré trabajando de acuerdo con las siguientes instrucciones. Puedes cambiarlos, si quieres..", value=prompt_capacitacion, height=300)
                    #prompt = st.text_area("Default Prompt", value=default_value, height=300)
                    if st.button('Cambiar :test_tube:'):
                        st.success("Prompt cambiado exitosamente!")
                        try:
                            if transcription != "":
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write("Prompt changed")
                                #st.write(prompt)  # Display the formatted prompt
                            else:
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write(prompt)
                        except KeyboardInterrupt as e:
                            st.error(f"Missing a value for the placeholder: {e}")
                button = st.button('Procesar :sparkles:')

            elif option == "Presentacion":
                prompt_presentacion = "Dado el contenido de una reciente presentación, su tarea es analizar y condensar la información en un formato que destaque los aspectos más importantes y las interacciones clave. Siga la estructura propuesta para su reporte:\n\n- **Presentación:** Proporcione un resumen introductorio sobre el propósito y los objetivos generales de la presentación.\n- **Tema de la reunión:** Identifique el tema principal abordado en la presentación.\n- **Puntos principales de la presentación:** Detalle los puntos o argumentos clave presentados, enfocándose en aquellos que representan el núcleo de la discusión.\n- **Preguntas y respuestas importantes:** Resuma las interacciones más significativas que surgieron durante la sesión, destacando las preguntas relevantes y las respuestas dadas.\n- **Acción requerida de los participantes:** Liste cualquier llamado a la acción o pasos siguientes que se hayan solicitado a los participantes al final de la presentación.\n\nCon base en `{transcription}`, genere:\n1. Un resumen detallado de la presentación, enfocado en los puntos principales, las discusiones generadas y las acciones a seguir.\n2. Un listado de las preguntas y respuestas clave que ayuden a entender mejor el tema y las expectativas post-reunión.\n\nAsegúrese de que su respuesta sea precisa, bien organizada y ofrezca una visión clara de los resultados y expectativas de la presentación."
                with st.expander("Instrucciones:"):
                    prompt = st.text_area("Estaré trabajando de acuerdo con las siguientes instrucciones. Puedes cambiarlos, si quieres..", value=prompt_presentacion, height=300)
                    #prompt = st.text_area("Default Prompt", value=default_value, height=300)
                    if st.button('Cambiar :test_tube:'):
                        st.success("Prompt cambiado exitosamente!")
                        try:
                            if transcription != "":
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write("Prompt changed")
                                #st.write(prompt)  # Display the formatted prompt
                            else:
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write(prompt)
                        except KeyboardInterrupt as e:
                            st.error(f"Missing a value for the placeholder: {e}")
                button = st.button('Procesar :sparkles:')

            elif option == "Lluvia de ideas":
                prompt_lluvia_ideas = "Tras revisar la transcripción de una reciente reunión de lluvia de ideas, su objetivo es sintetizar y estructurar un documento que resuma efectivamente las ideas innovadoras y los acuerdos alcanzados. Por favor, siga este esquema para su análisis:\n\n- **Reunión de Lluvia de Ideas:** Breve introducción sobre el propósito y los objetivos de la sesión.\n- **Tema de la reunión:** Especificar el tema central que se exploró durante la sesión.\n- **Ideas generadas:** Resumir las ideas principales que surgieron, destacando aquellas que generaron mayor interés o discusión.\n- **Decisiones tomadas:** Identificar las decisiones concretas que se acordaron, incluyendo cualquier consenso o discrepancia notable.\n- **Próximos pasos acordados:** Enumerar los pasos a seguir que se acordaron, señalando responsables y plazos cuando sea posible.\n\nCon base en `{transcription}`, genere:\n1. Un resumen de las ideas clave y decisiones tomadas durante la reunión.\n2. Un plan de acción detallado que incluya los próximos pasos y responsables asignados.\n\nAsegúrese de que su reporte sea claro, conciso y útil para los participantes y otros interesados, facilitando la comprensión y el seguimiento de los acuerdos alcanzados."
                with st.expander("Instrucciones:"):
                    prompt = st.text_area("Estaré trabajando de acuerdo con las siguientes instrucciones. Puedes cambiarlos, si quieres..", value=prompt_lluvia_ideas, height=300)
                    #prompt = st.text_area("Default Prompt", value=default_value, height=300)
                    if st.button('Cambiar :test_tube:'):
                        st.success("Prompt cambiado exitosamente!")
                        try:
                            if transcription != "":
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write("Prompt changed")
                                #st.write(prompt)  # Display the formatted prompt
                            else:
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write(prompt)
                        except KeyboardInterrupt as e:
                            st.error(f"Missing a value for the placeholder: {e}")
                button = st.button('Procesar :sparkles:')

            elif option == "Otro":
                prompt_5 = "Otro \n{transcription}\n"
                with st.expander("Instrucciones:"):
                    prompt = st.text_area("Estaré trabajando de acuerdo con las siguientes instrucciones. Puedes cambiarlos, si quieres..", value=default_value, height=300)
                    #prompt = st.text_area("Default Prompt", value=default_value, height=300)
                    if st.button('Cambiar :test_tube:'):
                        st.success("Prompt cambiado exitosamente!")
                        try:
                            if transcription != "":
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write("Prompt changed")
                                #st.write(prompt)  # Display the formatted prompt
                            else:
                                prompt = prompt.replace("{transcription}", transcription)
                                #st.write(prompt)
                        except KeyboardInterrupt as e:
                            st.error(f"Missing a value for the placeholder: {e}")
                button = st.button('Procesar :sparkles:')

        if button:
            if uploaded_file.type.startswith("video/"):
                if st.session_state.meeting_info is None:
                    prompt = prompt.replace("{transcription}", transcription)
                    st.session_state.meeting_info = generate_meeting_summary(transcription, client, prompt)
                    os.remove(temp_file_path)
                    os.remove(audio_path)
            else:
                if st.session_state.meeting_info is None:
                    prompt = prompt.replace("{transcription}", transcription)
                    st.session_state.meeting_info = generate_meeting_summary(transcription, client, prompt)
                    os.remove(temp_file_path)



    if "meeting_info" not in st.session_state:
        st.session_state.meeting_info = None

    # Displaying the generated meeting information as a bot message on the right side
    if st.session_state.meeting_info:
        bot_message = create_chat_message(st.session_state.meeting_info, bot_template)
        st.markdown(bot_message, unsafe_allow_html=True)

        st.header("que mas....? 📺")
        # User input text area below the bot message
        user_question = st.text_input("Pregunten aqui:")

        if user_question:
            response = handle_user_query(user_question, client)
            for message in st.session_state.conversation_history:
                if message["role"] == "assistant":
                    chat_message = create_chat_message(message["content"], bot_template)
                    st.markdown(chat_message, unsafe_allow_html=True)


if __name__ == "__main__":
    if "eula_accepted" not in st.session_state:
        st.session_state["eula_accepted"] = False

    if st.session_state["eula_accepted"]:
        main()
    else:
        show_eula()
