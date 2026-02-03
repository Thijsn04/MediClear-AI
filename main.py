import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from gtts import gTTS
import tempfile
from PIL import Image

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
st.set_page_config(
        page_title="MediClear AI",
        page_icon="🩺",
        layout="centered", # Centered layout is often cleaner for reading-heavy apps
        initial_sidebar_state="collapsed"
)

# --- TRANSLATIONS (Expanded & Polished) ---
TRANSLATIONS = {
    "Nederlands": {
        "header_title": "MediClear AI",
        "header_subtitle": "Uw Persoonlijke Medische Vertaler",
        "hero_text": "Medische taal is lastig. Wij maken het begrijpelijk.",
        "input_label": "Wat wilt u laten vertalen?",
        "tab_text": "✍️ Typ tekst",
        "tab_file": "📄 Upload bestand",
        "placeholder_text": "Plak hier de tekst van uw dokter of brief...",
        "upload_help": "Upload een PDF brief of een foto van een recept.",
        "btn_analyze": "Vertaal naar Begrijpelijke Taal",
        "btn_processing": "Bezig met analyseren...",
        "result_header": "Uw Begrijpelijke Uitleg",
        "audio_label": "🔊 Lees voor",
        "chat_header": "Heeft u nog vragen?",
        "chat_placeholder": "Vraag bijvoorbeeld: 'Moet ik me zorgen maken?'",
        "footer_disclaimer": "Disclaimer: Dit is een AI-hulpmiddel. Raadpleeg bij medische vragen altijd uw arts.",
        "settings_title": "Instellingen",
        "err_no_api": "⚠️ Systeem niet actief (API Key ontbreekt).",
        "err_no_input": "⚠️ Voer eerst tekst in of upload een bestand.",
        "success_upload": "Bestand succesvol ingelezen!",
    },
    "English": {
        "header_title": "MediClear AI",
        "header_subtitle": "Your Personal Medical Translator",
        "hero_text": "Medical jargon is hard. We make it simple.",
        "input_label": "What would you like to translate?",
        "tab_text": "✍️ Type Text",
        "tab_file": "📄 Upload File",
        "placeholder_text": "Paste the doctor's note or letter here...",
        "upload_help": "Upload a PDF letter or photo of a prescription.",
        "btn_analyze": "Translate to Simple Language",
        "btn_processing": "Analyzing...",
        "result_header": "Your Simple Explanation",
        "audio_label": "🔊 Read Aloud",
        "chat_header": "Any questions?",
        "chat_placeholder": "Ask something like: 'Should I be worried?'",
        "footer_disclaimer": "Disclaimer: AI tool. Always consult a doctor for medical advice.",
        "settings_title": "Settings",
        "err_no_api": "⚠️ System inactive (Missing API Key).",
        "err_no_input": "⚠️ Please enter text or upload a file first.",
        "success_upload": "File loaded successfully!",
    },
    "Türkçe": {
        "header_title": "MediClear AI", "header_subtitle": "Kişisel Tıbbi Tercümanınız",
        "hero_text": "Tıbbi dili anlamak zordur. Sizin için basitleştiriyoruz.", "input_label": "Neyi çevirmek istersiniz?",
        "tab_text": "✍️ Metin Yaz", "tab_file": "📄 Dosya Yükle", "placeholder_text": "Doktorun yazdıklarını buraya yapıştırın...",
        "upload_help": "PDF veya fotoğraf yükleyin.", "btn_analyze": "Basitçe Açıkla", "btn_processing": "İnceleniyor...",
        "result_header": "Anlaşılır Açıklama", "audio_label": "🔊 Sesli Oku", "chat_header": "Sorunuz var mı?",
        "chat_placeholder": "Örneğin: 'Endişelenmeli miyim?'", "footer_disclaimer": "Yapay zeka aracıdır. Doktora danışın.",
        "settings_title": "Ayarlar", "err_no_api": "⚠️ Sistem anahtarı eksik.", "err_no_input": "⚠️ Lütfen metin girin.", "success_upload": "Dosya yüklendi!"
    },
    "العربية": {
        "header_title": "MediClear AI", "header_subtitle": "مترجمك الطبي الشخصي",
        "hero_text": "المصطلحات الطبية صعبة. نحن نبسطها.", "input_label": "ماذا تريد أن تترجم؟",
        "tab_text": "✍️ كتابة نص", "tab_file": "📄 رفع ملف", "placeholder_text": "الصق نص الطبيب هنا...",
        "upload_help": "رفع ملف PDF أو صورة.", "btn_analyze": "شرح بـ لغة بسيطة", "btn_processing": "جاري التحليل...",
        "result_header": "الشرح المبسط", "audio_label": "🔊 قراءة بصوت عال", "chat_header": "هل لديك أسئلة؟",
        "chat_placeholder": "اسأل مثلا: 'هل يجب أن أقلق؟'", "footer_disclaimer": "تنويه: أداة ذكاء اصطناعي. استشر الطبيب دائما.",
        "settings_title": "الإعدادات", "err_no_api": "⚠️ مفتاح النظام مفقود.", "err_no_input": "⚠️ يرجى إدخال نص أو ملف.", "success_upload": "تم تحميل الملف!"
    },
    "Polski": {
        "header_title": "MediClear AI", "header_subtitle": "Twój Osobisty Tłumacz Medyczny",
        "hero_text": "Medyczny żargon jest trudny. My go upraszczamy.", "input_label": "Co chcesz przetłumaczyć?",
        "tab_text": "✍️ Wpisz tekst", "tab_file": "📄 Prześlij plik", "placeholder_text": "Wklej tutaj tekst od lekarza...",
        "upload_help": "Prześlij list PDF lub zdjęcie recepty.", "btn_analyze": "Przetłumacz na prosty język", "btn_processing": "Analizowanie...",
        "result_header": "Twoje Proste Wyjaśnienie", "audio_label": "🔊 Przeczytaj na głos", "chat_header": "Masz pytania?",
        "chat_placeholder": "Zapytaj np.: 'Czy mam się martwić?'", "footer_disclaimer": "Uwaga: Narzędzie AI. Skonsultuj się z lekarzem.",
        "settings_title": "Ustawienia", "err_no_api": "⚠️ Brak klucza API.", "err_no_input": "⚠️ Wpisz tekst lub prześlij plik.", "success_upload": "Plik wczytany!"
    },
    "Deutsch": {
        "header_title": "MediClear AI", "header_subtitle": "Ihr persönlicher medizinischer Übersetzer",
        "hero_text": "Medizinische Sprache ist schwer. Wir machen es einfach.", "input_label": "Was möchten Sie übersetzen?",
        "tab_text": "✍️ Text eingeben", "tab_file": "📄 Datei hochladen", "placeholder_text": "Fügen Sie hier den Arzttext ein...",
        "upload_help": "PDF oder Foto hochladen.", "btn_analyze": "Einfach erklären", "btn_processing": "Analysiere...",
        "result_header": "Ihre einfache Erklärung", "audio_label": "🔊 Vorlesen", "chat_header": "Haben Sie Fragen?",
        "chat_placeholder": "Fragen Sie z.B.: 'Muss ich mir Sorgen machen?'", "footer_disclaimer": "Hinweis: KI-Tool. Im Zweifel Arzt fragen.",
        "settings_title": "Einstellungen", "err_no_api": "⚠️ API-Schlüssel fehlt.", "err_no_input": "⚠️ Bitte Text eingeben.", "success_upload": "Datei geladen!"
    },
    "Français": {
        "header_title": "MediClear AI", "header_subtitle": "Votre traducteur médical personnel",
        "hero_text": "Le jargon médical est difficile. Nous le simplifions.", "input_label": "Que souhaitez-vous traduire ?",
        "tab_text": "✍️ Saisir le texte", "tab_file": "📄 Télécharger fichier", "placeholder_text": "Collez le texte du médecin ici...",
        "upload_help": "Téléchargez un PDF ou une photo.", "btn_analyze": "Expliquer simplement", "btn_processing": "Analyse en cours...",
        "result_header": "Votre explication simple", "audio_label": "🔊 Lire à haute voix", "chat_header": "Des questions ?",
        "chat_placeholder": "Demandez par ex. : 'Dois-je m'inquiéter ?'", "footer_disclaimer": "Avis : Outil IA. Consultez un médecin.",
        "settings_title": "Paramètres", "err_no_api": "⚠️ Clé API manquante.", "err_no_input": "⚠️ Veuillez saisir du texte.", "success_upload": "Fichier chargé !"
    },
    "Español": {
        "header_title": "MediClear AI", "header_subtitle": "Su traductor médico personal",
        "hero_text": "La jerga médica es difícil. Nosotros la simplificamos.", "input_label": "¿Qué desea traducir?",
        "tab_text": "✍️ Escribir texto", "tab_file": "📄 Subir archivo", "placeholder_text": "Pegue el texto del médico aquí...",
        "upload_help": "Suba un PDF o foto.", "btn_analyze": "Explicar simplemente", "btn_processing": "Analizando...",
        "result_header": "Su explicación simple", "audio_label": "🔊 Leer en voz alta", "chat_header": "¿Tiene preguntas?",
        "chat_placeholder": "Pregunte ej.: '¿Debo preocuparme?'", "footer_disclaimer": "Nota: Herramienta IA. Consulte a un médico.",
        "settings_title": "Ajustes", "err_no_api": "⚠️ Falta clave API.", "err_no_input": "⚠️ Por favor ingrese texto.", "success_upload": "¡Archivo cargado!"
    }
}

# --- STYLING (THEMES & CUSTOM CSS) ---
def local_css():
    st.markdown("""
    <style>
        /* IMPORT FONTS */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

        /* RESET & BASE VARS */
        :root {
            --primary-color: #005eb8; /* NVZ/Medical Blue */
            --secondary-color: #009688; /* Calm Teal */
            --bg-color: #f8f9fa;
            --card-bg: #ffffff;
            --text-dark: #1f2937;
            --text-light: #6b7280;
            --accent-bg: #e0f2f1;
        }

        /* PAGE BACKGROUND */
        .stApp {
            background-color: var(--bg-color);
            font-family: 'Inter', sans-serif;
        }

        /* HEADER REMOVAL (Streamlit default) */
        header[data-testid="stHeader"] {
            background-color: transparent;
        }

        /* CUSTOM TITLE BAR */
        .main-header {
            background: white;
            padding: 1.5rem 0;
            margin-bottom: 2rem;
            border-bottom: 1px solid #e5e7eb;
            text-align: center;
            border-radius: 0 0 20px 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }
        .main-header h1 {
            color: var(--primary-color);
            font-weight: 800;
            font-size: 2.2rem;
            margin: 0;
            letter-spacing: -0.02em;
        }
        .main-header p {
            color: var(--text-light);
            font-size: 1.1rem;
            margin-top: 0.5rem;
        }

        /* CARDS (Containers) */
        .css-1r6slb0, .stTabs, [data-testid="stVerticalBlock"] > div {
           /* General container tweaks if needed */
        }
        
        div[data-testid="stForm"] {
            background-color: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            border: 1px solid #f3f4f6;
        }

        /* INPUT FIELDS */
        .stTextArea textarea {
            border-radius: 12px;
            border: 2px solid #e5e7eb;
            font-size: 16px;
            padding: 1rem;
            color: var(--text-dark);
        }
        .stTextArea textarea:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(0, 94, 184, 0.1);
        }

        /* TABS */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            margin-bottom: 1rem;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: white;
            border-radius: 50px;
            padding: 0.5rem 1.5rem;
            border: 1px solid #e5e7eb;
            font-weight: 600;
            color: var(--text-light);
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--primary-color);
            color: white !important;
            border-color: var(--primary-color);
        }

        /* BUTTONS */
        .stButton > button {
            width: 100%;
            border-radius: 12px;
            height: 3.5rem;
            font-weight: 700;
            font-size: 1.1rem;
            transition: all 0.2s;
        }
        /* Primary Action Button */
        div[data-testid="stVerticalBlock"] > .stButton > button[kind="primary"] { 
            background: linear-gradient(135deg, #005eb8 0%, #004494 100%);
            border: none;
            box-shadow: 0 4px 12px rgba(0, 94, 184, 0.3);
        }
        div[data-testid="stVerticalBlock"] > .stButton > button[kind="primary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0, 94, 184, 0.4);
        }

        /* ALERTS */
        [data-testid="stAlert"] {
            padding: 1rem;
            border-radius: 12px;
            border: none;
        }

        /* RESULT PREVIEW */
        .result-card {
            background-color: white;
            padding: 2.5rem;
            border-radius: 16px;
            border-left: 6px solid var(--secondary-color);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            margin-top: 2rem;
            font-size: 1.1rem;
            line-height: 1.7;
            color: #374151;
        }
        .result-card h3 {
            color: var(--secondary-color);
            margin-top: 0;
        }

        /* CHAT BUBBLES */
        .stChatMessage {
            background: white;
            border-radius: 12px;
            border: 1px solid #f3f4f6;
            margin-bottom: 1rem;
        }
        [data-testid="stChatMessageContent"] {
            color: var(--text-dark);
        }
        
        /* FOOTER */
        .footer {
            text-align: center;
            color: #9ca3af;
            font-size: 0.8rem;
            margin-top: 4rem;
            padding-bottom: 2rem;
        }
        
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- STATE MANAGEMENT ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_text" not in st.session_state:
    st.session_state.current_text = ""
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "selected_lang_code" not in st.session_state:
    st.session_state.selected_lang_code = "Nederlands"

# --- TOP NAVIGATION BAR ---
col_logo, col_spacer, col_lang = st.columns([2, 3, 2])

with col_logo:
    # Simulating a logo/title area
    st.markdown(f"### 🩺 MediClear")

with col_lang:
    # Minimal dropdown for language
    # Using 'key' binds the selection directly to st.session_state.selected_lang_code
    st.selectbox(
        "Language",
        options=list(TRANSLATIONS.keys()),
        key="selected_lang_code",
        label_visibility="collapsed"
    )

T = TRANSLATIONS[st.session_state.selected_lang_code]

# --- HERO SECTION ---
st.markdown(f"""
<div class="main-header">
    <h1>{T['header_title']}</h1>
    <p>{T['header_subtitle']}</p>
</div>
""", unsafe_allow_html=True)

# --- MAIN INPUT CARD ---
# Use a container to group the input nicely
with st.container():
    st.markdown(f"#### {T['input_label']}")

    tab1, tab2 = st.tabs([T['tab_text'], T['tab_file']])

    extracted_input = ""
    input_type = "text"
    final_image = None

    with tab1:
        text_val = st.text_area(
            "Input Text",
            height=180,
            placeholder=T['placeholder_text'],
            label_visibility="collapsed"
        )
        if text_val:
            extracted_input = text_val

    with tab2:
        file_val = st.file_uploader(
            "Upload File",
            type=['pdf', 'jpg', 'jpeg', 'png'],
            label_visibility="collapsed"
        )
        if file_val:
            st.info(T['success_upload'])
            if file_val.type == "application/pdf":
                try:
                    reader = PdfReader(file_val)
                    pdf_text = ""
                    for page in reader.pages:
                        pdf_text += page.extract_text()
                    extracted_input = pdf_text
                    input_type = "pdf"
                except:
                    st.error("Error reading PDF")
            elif file_val.type.startswith("image"):
                final_image = Image.open(file_val)
                st.image(final_image, width=200)
                input_type = "image"

    # Action Button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(T['btn_analyze'], type="primary"):

        # 1. API Key Check
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            # Fallback to user input if env var missing (Demo mode)
            if "user_api_key" in st.session_state and st.session_state.user_api_key:
                api_key = st.session_state.user_api_key
            else:
                 st.error(T['err_no_api'])
                 st.stop()

        # 2. Input Check
        if not extracted_input and not final_image:
            st.warning(T['err_no_input'])
        else:
            # 3. Process
            with st.spinner(f"✨ {T['btn_processing']}"):
                try:
                    genai.configure(api_key=api_key)

                    # Model Selection Logic (Robust fallback)
                    def get_model():
                        models = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-pro']
                        for m in models:
                            try:
                                model = genai.GenerativeModel(m)
                                return model
                            except:
                                continue
                        return genai.GenerativeModel('gemini-pro')

                    model = get_model()

                    prompt_text = f"""
                    ROLE: Medical Communicator for Patients.
                    TASK: Simplify the following medical text.
                    TARGET LANGUAGE: {st.session_state.selected_lang_code}.
                    READING LEVEL: B1 (Plain language / Jip en Janneke).
                    STYLE: Reassuring, clear unstructured layout is fine but use paragraphs.
                    
                    OUTPUT FORMAT:
                    ## Samenvatting
                    (What is happening?)
                    
                    ## Uitleg
                    (Detailed simple explanation)
                    
                    ## Belangrijke Begrippen
                    (Bullet points of difficult terms)

                    INPUT TEXT:
                    {extracted_input if extracted_input else "Analyze the medical image."}
                    """

                    inputs = [prompt_text]
                    if final_image:
                        inputs.append(final_image)

                    response = model.generate_content(inputs)

                    st.session_state.current_text = response.text
                    st.session_state.analysis_done = True
                    st.session_state.chat_history = [] # Reset chat

                except Exception as e:
                    st.error(f"Error: {str(e)}")


# --- RESULTS SECTION ---
if st.session_state.analysis_done:

    # Improved Result Display (Native Markdown Support)
    st.markdown(f"### ✅ {T['result_header']}")
    with st.container(border=True):
        st.markdown(st.session_state.current_text)

    # Utilities Row
    col_audio, col_copy = st.columns([1, 4])
    with col_audio:
        if st.button(T['audio_label']):
             try:
                # Expanded lang mapping
                lang_map = {
                    "Nederlands": "nl", "English": "en", "Türkçe": "tr",
                    "العربية": "ar", "Polski": "pl", "Deutsch": "de",
                    "Français": "fr", "Español": "es"
                }
                code = lang_map.get(st.session_state.selected_lang_code, "en")
                tts = gTTS(text=st.session_state.current_text, lang=code)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    tts.save(fp.name)
                    st.audio(fp.name, format="audio/mp3")
             except:
                 st.error("Audio failed")

    # --- CHAT INTERFACE ---
    st.markdown("---")
    st.subheader(f"💬 {T['chat_header']}")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_q := st.chat_input(T['chat_placeholder']):
        st.session_state.chat_history.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.markdown(user_q)

        with st.chat_message("assistant"):
            with st.spinner("..."):
                try:
                    # Chat Logic (Simplified reused context)
                    api_key = os.getenv("GOOGLE_API_KEY") or st.session_state.get("user_api_key")
                    genai.configure(api_key=api_key)
                    model_chat = genai.GenerativeModel('gemini-2.5-flash') # Or fallback

                    chat_prompt = f"""
                    CONTEXT: The user asks about the previous translation.
                    TRANSLATION: {st.session_state.current_text}
                    QUESTION: {user_q}
                    LANGUAGE: {st.session_state.selected_lang_code}
                    Keep it short and helpful.
                    """
                    resp = model_chat.generate_content(chat_prompt)
                    st.markdown(resp.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": resp.text})
                except Exception as e:
                     st.error("Chat error.")

# --- FOOTER & TECH DETAILS ---
st.markdown(f"<div class='footer'>{T['footer_disclaimer']}</div>", unsafe_allow_html=True)

# Secret/Advanced Settings Expander (Bottom of page to keep top clean)
with st.expander("⚙️ System / Admin"):
    st.caption("Technical Configuration")
    user_key = st.text_input("Manually enter API Key (if not in env)", type="password")
    if user_key:
        st.session_state.user_api_key = user_key

    if st.button("Clear History"):
        st.session_state.chat_history = []
        st.session_state.analysis_done = False
        st.rerun()
