import os
from dotenv import load_dotenv
from htmlTemplates import css, bot_template, user_template
import streamlit as st
import docx
from streamlit import components
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import whisper
import base64
from openai import AzureOpenAI


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

    if st.button("I Agree"):
        st.session_state["eula_accepted"] = True
        st.experimental_rerun()

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


def extract_audio(video_file, audio_path):
    with open("temp_video", "wb") as f:
        f.write(video_file.getbuffer())

    with st.spinner("Extracting audio..."):
        progress_bar = st.progress(0)
        video = VideoFileClip("temp_video")
        video.audio.write_audiofile(
            "temp_audio.wav", codec="pcm_s16le", ffmpeg_params=["-ar", "16000"]
        )
        progress_bar.progress(100)

    audio = AudioSegment.from_wav("temp_audio.wav")
    if audio.channels > 2:
        audio = audio.set_channels(2)

    audio.export(
        audio_path,
        format="wav",
        parameters=["-ar", "16000", "-ac", "2", "-acodec", "pcm_s16le"],
    )

    os.remove("temp_audio.wav")
    os.remove("temp_video")


def transcribe_audio(audio_path):
    with st.spinner("Transcribing audio..."):
        progress_bar = st.progress(0)
        model = whisper.load_model("medium")
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
        )
        summary = response.choices[0].message.content
        st.session_state.conversation_history.append({"role": "assistant", "content": summary})
        return summary
    except Exception as e:
        st.write(e)
        return str(e)
    
def handle_user_query(user_query, client):
    st.session_state.conversation_history.append({"role": "user", "content": user_query})

    response = client.chat.completions.create(
        model="sopa",
        messages=st.session_state.conversation_history[-5:]  # Adjust as needed
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
    transcription = ""
    default_value = "A continuación se muestra la transcripción de un archivo de audio de una reunión reciente. La reunión cubrió varios temas, incluidas actualizaciones de proyectos, discusiones presupuestarias y planificación futura. Su tarea es analizar el texto y generar notas concisas de la reunión que resuma los puntos clave discutidos. Además, cree una lista de participantes basada en los nombres y títulos mencionados durante la reunión.\nTranscripción del archivo de audio:\n{transcription}\nBasado en la transcripción anterior, genere lo siguiente:\n1. Un resumen de la reunión, destacando los principales temas discutidos, las decisiones tomadas y las acciones a tomar.\n2. Una lista de participantes, incluidos sus nombres y funciones o títulos mencionados en la reunión."
    prompt = st.text_area("Default Prompt", value=default_value, height=400)
    #prompt = str.format(prompt_text)
    if st.button('Change Prompt'):
        try:
            if transcription != "":
                prompt = prompt.replace("{transcription}", transcription)
                st.write("Prompt changed")
                st.write(prompt)  # Display the formatted prompt
            else:
                prompt = prompt.replace("{transcription}", transcription)
                st.write(prompt)
        except KeyboardInterrupt as e:
            st.error(f"Missing a value for the placeholder: {e}")
            #print(default_value)    

    if "meeting_info" not in st.session_state:
        st.session_state.meeting_info = None

    with st.sidebar:
        # Sidebar code for file upload and other inputs

        uploaded_file = st.file_uploader(
            "Upload a video / transcription file", type=["mp4", "avi", "mov", "mkv", "vtt", "txt", "docx"]
        )

        if uploaded_file is not None:
            if uploaded_file.type.startswith("video/"):
                audio_path = "extracted_audio.wav"
                if st.session_state.meeting_info is None:
                    extract_audio(uploaded_file, audio_path)
                    transcription = transcribe_audio(audio_path)
                    prompt = prompt.replace("{transcription}", transcription)
                    st.session_state.meeting_info = generate_meeting_summary(transcription, client, prompt)
            elif uploaded_file.type.startswith("text/"):
                if st.session_state.meeting_info is None:
                    transcription = uploaded_file.getvalue().decode('utf-8')
                    prompt = prompt.replace("{transcription}", transcription)
                    st.session_state.meeting_info = generate_meeting_summary(transcription, client, prompt)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                if st.session_state.meeting_info is None:
                    doc = docx.Document(uploaded_file)
                    full_text = [paragraph.text for paragraph in doc.paragraphs]
                    transcription = "\n".join(full_text)
                    prompt = prompt.replace("{transcription}", transcription)
                    st.session_state.meeting_info = generate_meeting_summary(transcription, client, prompt)
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
                        prompt = prompt.replace("{transcription}", transcription)
                        st.session_state.meeting_info = generate_meeting_summary(transcription, client, prompt)
            else:
                st.error("Please upload a valid file.")

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
        load_dotenv()
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2023-05-15",
        )
        main()
    else:
        show_eula()