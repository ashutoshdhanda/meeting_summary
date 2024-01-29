import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
from htmlTemplates import css
from openai import AzureOpenAI
import os
import re

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

bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="https://i.ibb.co/zX6NHC8/raw.png" style="max-height: 78px; max-width: 78px; border-radius: 50%; object-fit: cover;">
    </div>
    <div class="message">{}</div>
</div>
'''

st.write(css, unsafe_allow_html=True)

# Load environment variables and initialize AzureOpenAI client
load_dotenv()
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2023-05-15",
)

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

st.title("YOUTUBE VIDEO RESUMEN")

# Function to extract video ID from URL
def extract_video_id(url):
    regex = r"(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|(embed|v)\/))([^\?&\"'>]+)"
    match = re.search(regex, url)
    if match:
        return match.group(5)  # The video ID is in the fifth group of the match
    else:
        return None

# Function to get transcript
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        return str(e)

def generate_meeting_summary(transcription, client):
    try:
        # Initialize conversation with system message
        conversation = [
            {"role": "system", "content": "You are a helpful assistant. Your task is to summarize the main points of a YouTube video transcript."},
            {"role": "user", "content": transcription}
        ]

        # Call to Azure OpenAI for a chat completion
        response = client.chat.completions.create(
            model="sopa", # Replace with your actual model name
            messages=conversation
        )

        # Extracting the summary from the response
        summary = response.choices[0].message.content

        # Extend the conversation history with the generated summary
        st.session_state.conversation_history.extend([
            {"role": "user", "content": transcription},
            {"role": "assistant", "content": summary}
        ])

        #st.write(summary)

        return summary

    except Exception as e:
        st.write(e)
        return str(e)


def main():
    # User input for the YouTube URL (with a unique key)
    youtube_url = st.text_input("Enter YouTube Video URL:", key="url_input")
    if youtube_url:
        video_id = extract_video_id(youtube_url)
        transcript = get_transcript(video_id)
        if transcript:
            st.text_area("Transcript:", value=transcript, height=200, key="transcript_area")
        summary = generate_meeting_summary(transcript, client)
        if summary:
            summary_html = bot_template.format(summary)
            st.markdown(summary_html, unsafe_allow_html=True)

# Main app
if __name__ == "__main__":
    if "eula_accepted" not in st.session_state:
        st.session_state["eula_accepted"] = False

    if st.session_state["eula_accepted"]:
        main()
    else:
        show_eula()