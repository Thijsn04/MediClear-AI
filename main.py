import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from gtts import gTTS
import tempfile
from PIL import Image
from translations import TRANSLATIONS

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
st.set_page_config(
    page_title="MediClear AI",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- STATE MANAGEMENT ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "current_text" not in st.session_state:
    st.session_state.current_text = ""
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "selected_lang_code" not in st.session_state:
    st.session_state.selected_lang_code = "Nederlands"
if "audio_file_path" not in st.session_state:
    st.session_state.audio_file_path = None
if "uploaded_gemini_file" not in st.session_state:
    st.session_state.uploaded_gemini_file = None

def cleanup_audio():
    """Removes the old temporary audio file if it exists."""
    if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
        try:
            os.remove(st.session_state.audio_file_path)
            st.session_state.audio_file_path = None
        except OSError:
            pass

def cleanup_gemini_file():
    """No longer used, kept for state reset safety."""
    st.session_state.uploaded_gemini_file = None

def reset_analysis():
    """Resets the state for a new analysis."""
    st.session_state.analysis_done = False
    st.session_state.current_text = ""
    st.session_state.chat_session = None
    cleanup_audio()
    cleanup_gemini_file()

# --- SIDEBAR (Settings & Navigation) ---
with st.sidebar:
    st.title("🩺 MediClear AI")
    st.selectbox(
        "Taal / Language",
        options=list(TRANSLATIONS.keys()),
        key="selected_lang_code"
    )
    
    T = TRANSLATIONS[st.session_state.selected_lang_code]
    
    st.divider()
    if st.button("Herstart / Clear Data", use_container_width=True):
        reset_analysis()
        st.rerun()

# --- PREMIUM STYLING ---
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    /* Global Typography */
    html, body, [class*="css"]  {
        font-family: 'Outfit', sans-serif;
    }

    /* Main Container Padding */
    .element-container, .stMarkdown {
        margin-bottom: 0.5rem;
    }

    /* Primary Headers */
    h1, h2, h3 {
        color: #0f172a;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* Hero Title styling */
    h1 {
        background: linear-gradient(135deg, #005EB8 0%, #0ea5e9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: -10px;
        padding-top: 1rem;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
        padding: 0.75rem 1.5rem;
        border: none;
    }
    
    /* Primary Action Button Hover */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #005EB8 0%, #0284c7 100%);
        box-shadow: 0 4px 14px 0 rgba(0, 94, 184, 0.39);
        color: white;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 94, 184, 0.5);
    }
    
    /* Secondary Buttons */
    .stButton > button[kind="secondary"] {
        background: white;
        color: #005EB8;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #005EB8;
        background: #f8fafc;
        transform: translateY(-1px);
    }

    /* Text Area */
    .stTextArea textarea {
        border-radius: 16px;
        border: 2px solid #e2e8f0;
        padding: 1rem;
        font-size: 1rem;
        transition: border-color 0.2s;
        box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.02);
    }
    .stTextArea textarea:focus {
        border-color: #005EB8;
        box-shadow: 0 0 0 3px rgba(0, 94, 184, 0.2);
    }

    /* Results Container (Glassmorphism card effect) */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        border-radius: 20px !important;
        border: 1px solid #e2e8f0 !important;
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(10px) !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01) !important;
        padding: 1.5rem !important;
        transition: all 0.3s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.06), 0 10px 10px -5px rgba(0, 0, 0, 0.02) !important;
    }

    /* Chat Messages */
    [data-testid="stChatMessage"] {
        padding: 1rem;
        border-radius: 16px;
        margin-bottom: 0.5rem;
    }
    /* User Message */
    [data-testid="stChatMessage"]:nth-child(even) {
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-bottom-right-radius: 4px;
    }
    /* Assistant Message */
    [data-testid="stChatMessage"]:nth-child(odd) {
        background-color: white;
        border: 1px solid #e0f2fe;
        border-bottom-left-radius: 4px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f8fafc;
        border-radius: 12px 12px 0 0;
        padding: 0.5rem 1.5rem;
        border: 1px solid #e2e8f0;
        border-bottom: none;
        color: #64748b;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: white;
        color: #005EB8 !important;
        border-top: 2px solid #005EB8;
    }

    /* Subheaders and text */
    h3 {
        color: #334155;
    }
    
    /* Uploader Area */
    [data-testid="stFileUploadDropzone"] {
        border-radius: 16px;
        border: 2px dashed #cbd5e1;
        background-color: #f8fafc;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #005EB8;
        background-color: #eff6ff;
    }
</style>
""", unsafe_allow_html=True)

# --- MAIN APP LAYOUT ---
# Hero Section
st.title(T['header_title'])
st.markdown(f"**{T['header_subtitle']}**")
st.caption(T['hero_text'])
st.divider()

# Input Area
st.subheader(T['input_label'])
tab1, tab2 = st.tabs([T['tab_text'], T['tab_file']])

extracted_text = ""
uploaded_file = None
file_type = None

with tab1:
    text_val = st.text_area(
        "Input Text",
        height=200,
        placeholder=T['placeholder_text'],
        label_visibility="collapsed"
    )
    if text_val:
        extracted_text = text_val
        file_type = "text"

with tab2:
    uploaded_file = st.file_uploader(
        T['upload_help'],
        type=['pdf', 'jpg', 'jpeg', 'png'],
        label_visibility="collapsed"
    )
    if uploaded_file:
        st.success(T['success_upload'])
        if uploaded_file.type == "application/pdf":
            file_type = "pdf"
            st.info("PDF document gereed voor analyse.")
        elif uploaded_file.type.startswith("image"):
            file_type = "image"
            img = Image.open(uploaded_file)
            st.image(img, caption="Geüploade afbeelding", use_container_width=True)

st.write("") # Spacer

# Analysis Action
if st.button(T['btn_analyze'], type="primary", use_container_width=True):
    # 1. API Key Validation
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error(T['err_no_api'])
        st.stop()

    # 2. Input Validation
    if not extracted_text and not uploaded_file:
        st.warning(T['err_no_input'])
        st.stop()

    # 3. Processing with Gemini
    reset_analysis() # Clean slate before new request
    
    with st.spinner(f"✨ {T['btn_processing']}"):
        try:
            genai.configure(api_key=api_key)
            
            # Verified available model for this API key
            model = genai.GenerativeModel('gemini-2.5-flash')

            sys_prompt = f"""
            Je bent een deskundige medische communicator voor patiënten.
            Taak: Vertaal en leg de medische informatie uit op B1 taalniveau (begrijpelijke taal voor de gemiddelde burger).
            Doeltaal: {st.session_state.selected_lang_code}.
            Stijl: Geruststellend, duidelijk en gestructureerd. Gebruik alinea's en eventueel bulletpoints.
            
            Gebruik de volgende structuur:
            ## Samenvatting
            (Wat is er aan de hand? Wat staat er in het kort in het document?)
            
            ## Uitleg
            (Gedetailleerde, erg simpele uitleg van de inhoud)
            
            ## Belangrijke Begrippen (indien van toepassing)
            * (Opsomming van moeilijke termen met een simpele uitleg erachter)
            """

            # Initialize chat session with the system instructions via an initial user prompt
            # (Streamlit caching or basic model init makes it easier to just pass the "role/persona" in the first message)
            
            initial_prompt_parts = [sys_prompt]

            if file_type == "text":
                 initial_prompt_parts.append(f"INVOER TEKST:\n{extracted_text}")
            elif file_type == "image":
                 img = Image.open(uploaded_file)
                 initial_prompt_parts.append("ANALYSEER DEZE AFBEELDING:")
                 initial_prompt_parts.append(img)
            elif file_type == "pdf":
                 # Fallback to PyPDF2 for text extraction as `gemini-pro` v1 
                 # does not reliably support direct file uploads on all keys.
                 try:
                     reader = PdfReader(uploaded_file)
                     pdf_text = ""
                     for page in reader.pages:
                         pdf_text += page.extract_text()
                     
                     initial_prompt_parts.append("ANALYSEER DE VOLGENDE TEKST UIT EEN PDF DOCUMENT:")
                     initial_prompt_parts.append(pdf_text)
                 except Exception as err:
                     st.error(f"Kan PDF niet goed inlezen: {err}")
                     st.stop()

            # Start chat and send the first message to get the translation
            chat = model.start_chat(history=[])
            response = chat.send_message(initial_prompt_parts)
            
            st.session_state.current_text = response.text
            st.session_state.chat_session = chat # Store the active chat session
            st.session_state.analysis_done = True

        except Exception as e:
            st.error(f"Er is een fout opgetreden tijdens de analyse: {str(e)}")


# --- RESULTS & CHAT SECTION ---
if st.session_state.analysis_done:
    
    # Result Box
    st.subheader(f"✅ {T['result_header']}")
    with st.container(border=True):
        st.markdown(st.session_state.current_text)

    # Audio Utils
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button(T['audio_label'], icon="🔊", use_container_width=True):
             with st.spinner(T['audio_playing']):
                 try:
                    cleanup_audio() # Remove any previous audio
                    lang_map = {
                        "Nederlands": "nl", "English": "en", "Türkçe": "tr",
                        "العربية": "ar", "Polski": "pl", "Deutsch": "de",
                        "Français": "fr", "Español": "es"
                    }
                    code = lang_map.get(st.session_state.selected_lang_code, "en")
                    tts = gTTS(text=st.session_state.current_text, lang=code)
                    
                    # Save to a new temp file and track it
                    fd, path = tempfile.mkstemp(suffix=".mp3")
                    os.close(fd)
                    tts.save(path)
                    st.session_state.audio_file_path = path
                    
                    # st.audio doesn't officially support autoplay in all browsers, but we serve the file
                    st.audio(path, format="audio/mp3")
                 except Exception as e:
                     st.error(f"Audio failed: {e}")

    # Chat Interface
    st.divider()
    st.subheader(f"💬 {T['chat_header']}")

    # Display chat history (excluding the very first prompt/response)
    if st.session_state.chat_session:
        for message in st.session_state.chat_session.history[2:]: # Skip initial setup
            role = "assistant" if message.role == "model" else "user"
            with st.chat_message(role):
                # Parts can be files, text etc. Just display text for simplicity in history
                text_content = "".join([part.text for part in message.parts if hasattr(part, 'text')])
                st.markdown(text_content)

    # Chat Input
    if user_q := st.chat_input(T['chat_placeholder']):
        with st.chat_message("user"):
            st.markdown(user_q)

        with st.chat_message("assistant"):
            with st.spinner("✨..."):
                try:
                    # Instruct chat session to reply in user's language briefly
                    lang_instruction = f"Antwoord kort en begrijpelijk in het {st.session_state.selected_lang_code} op de volgende vraag: "
                    response = st.session_state.chat_session.send_message(lang_instruction + user_q)
                    st.markdown(response.text)
                except Exception as e:
                     st.error("Chat error. Probeer het opnieuw.")

    # Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption(f"<div style='text-align: center;'>{T['footer_disclaimer']}</div>", unsafe_allow_html=True)
