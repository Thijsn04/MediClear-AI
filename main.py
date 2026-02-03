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

# --- CONFIGURATION & TRANSLATIONS ---

st.set_page_config(
        page_title="MediClear AI",
        page_icon="🏥",
        layout="wide"
)

# UI Translations Dictionary
TRANSLATIONS = {
    "Nederlands": {
        "title": "MediClear AI",
        "subtitle": "Uw Persoonlijke Medische Vertaler",
        "intro": "Heeft u een medische brief of tekst die moeilijk te begrijpen is? Wij leggen het simpel uit.",
        "step1": "1. Kies uw methode",
        "tab_text": "✍️ Typ of Plak Tekst",
        "tab_upload": "📸 Upload Foto of PDF",
        "input_placeholder": "Typ hier de tekst van de dokter...",
        "upload_label": "Kies een bestand van uw computer",
        "image_caption": "Geüploade afbeelding",
        "analyze_btn": "Leg dit simpel uit",
        "analyzing": "Moment geduld, ik lees de tekst...",
        "result_title": "Begrijpelijke Uitleg",
        "listen_btn": "🔊 Lees voor",
        "chat_title": "Heeft u nog vragen?",
        "chat_placeholder": "Typ hier uw vraag...",
        "settings_header": "Instellingen",
        "lang_select": "Kies uw taal / Choose your language:",
        "footer": "Let op: Dit is een AI-assistent. Raadpleeg bij twijfel altijd uw arts.",
        "error_api": "Let op: De 'sleutel' voor het systeem ontbreekt.",
        "warn_no_input": "Vergeet niet om eerst tekst in te voeren of een bestand te kiezen.",
        "success_pdf": "Document gelezen! Klik op de knop om te vertalen.",
        "img_success": "Foto ontvangen. Ik ga de tekst lezen.",
        "clear_btn": "Opnieuw beginnen"
    },
    "English": {
        "title": "MediClear AI",
        "subtitle": "Your Personal Medical Translator",
        "intro": "Do you have a medical letter or text that is hard to understand? We explain it simply.",
        "step1": "1. Choose your method",
        "tab_text": "✍️ Type or Paste Text",
        "tab_upload": "📸 Upload Photo or PDF",
        "input_placeholder": "Type the doctor's text here...",
        "upload_label": "Choose a file from your computer",
        "image_caption": "Uploaded image",
        "analyze_btn": "Explain Simply",
        "analyzing": "One moment, reading the text...",
        "result_title": "Understandable Explanation",
        "listen_btn": "🔊 Read Aloud",
        "chat_title": "Any questions?",
        "chat_placeholder": "Type your question here...",
        "settings_header": "Settings",
        "lang_select": "Choose your language:",
        "footer": "Note: This is an AI assistant. Always consult your doctor in case of doubt.",
        "error_api": "Warning: System key is missing.",
        "warn_no_input": "Please enter text or choose a file first.",
        "success_pdf": "Document loaded! Click the button to translate.",
        "img_success": "Photo received. I will read the text.",
        "clear_btn": "Start Over"
    },
    "Türkçe": {
        "title": "MediClear AI",
        "subtitle": "Kişisel Tıbbi Tercümanınız",
        "intro": "Anlaması zor bir tıbbi mektubunuz veya metniniz mi var? Sizin için basitleştiriyoruz.",
        "step1": "1. Yönteminizi seçin",
        "tab_text": "✍️ Metin Yaz veya Yapıştır",
        "tab_upload": "📸 Fotoğraf veya PDF Yükle",
        "input_placeholder": "Doktorun metnini buraya yazın...",
        "upload_label": "Bilgisayarınızdan bir dosya seçin",
        "image_caption": "Yüklenen fotoğraf",
        "analyze_btn": "Bunu Basitçe Açıkla",
        "analyzing": "Bir dakika, metni okuyorum...",
        "result_title": "Anlaşılır Açıklama",
        "listen_btn": "🔊 Sesli Oku",
        "chat_title": "Başka sorunuz var mı?",
        "chat_placeholder": "Sorunuzu buraya yazın...",
        "settings_header": "Ayarlar",
        "lang_select": "Dilinizi seçin:",
        "footer": "Not: Bu bir yapay zeka asistanıdır. Şüphe durumunda daima doktorunuza danışın.",
        "error_api": "Uyarı: Sistem anahtarı eksik.",
        "warn_no_input": "Lütfen önce metin girin veya bir dosya seçin.",
        "success_pdf": "Belge yüklendi! Çevirmek için butona tıklayın.",
        "img_success": "Fotoğraf alındı. Metni okuyacağım.",
        "clear_btn": "Baştan Başla"
    },
    "العربية": {
        "title": "MediClear AI",
        "subtitle": "مترجمك الطبي الشخصي",
        "intro": "هل لديك رسالة طبية أو نص يصعب فهمه؟ نحن نوضح ذلك ببساطة.",
        "step1": "1. اختر طريقتك",
        "tab_text": "✍️ اكتب أو الصق النص",
        "tab_upload": "📸 تحميل صورة أو PDF",
        "input_placeholder": "اكتب نص الطبيب هنا...",
        "upload_label": "اختر ملفًا من جهاز الكمبيوتر الخاص بك",
        "image_caption": "الصورة المحملة",
        "analyze_btn": "اشرح بساطة",
        "analyzing": "لحظة واحدة ، أقرأ النص...",
        "result_title": "تفسير مفهوم",
        "listen_btn": "🔊 اقرأ بصوت عال",
        "chat_title": "أي أسئلة؟",
        "chat_placeholder": "اكتب سؤالك هنا...",
        "settings_header": "إعدادات",
        "lang_select": "اختر لغتك:",
        "footer": "ملاحظة: هذا مساعد ذكاء اصطناعي. استشر طبيبك دائمًا في حالة الشك.",
        "error_api": "تحذير: مفتاح النظام مفقود.",
        "warn_no_input": "يرجى إدخال نص أو اختيار ملف أولاً.",
        "success_pdf": "تم تحميل المستند! انقر فوق الزر للترجمة.",
        "img_success": "تم استلام الصورة. سأقرأ النص.",
        "clear_btn": "ابدأ من جديد"
    },
    "Polski": {
        "title": "MediClear AI",
        "subtitle": "Twój Osobisty Tłumacz Medyczny",
        "intro": "Masz list medyczny lub tekst, który trudno zrozumieć? Wyjaśnimy to prosto.",
        "step1": "1. Wybierz metodę",
        "tab_text": "✍️ Wpisz tekst",
        "tab_upload": "📸 Prześlij zdjęcie/PDF",
        "input_placeholder": "Wpisz tutaj tekst od lekarza...",
        "upload_label": "Wybierz plik",
        "image_caption": "Przesłane zdjęcie",
        "analyze_btn": "Wyjaśnij to prosto",
        "analyzing": "Chwilkę, czytam tekst...",
        "result_title": "Zrozumiałe Wyjaśnienie",
        "listen_btn": "🔊 Przeczytaj na głos",
        "chat_title": "Masz pytania?",
        "chat_placeholder": "Wpisz swoje pytanie...",
        "settings_header": "Ustawienia",
        "lang_select": "Wybierz język:",
        "footer": "Uwaga: To asystent AI. W razie wątpliwości skonsultuj się z lekarzem.",
        "error_api": "Błąd: Brak klucza API.",
        "warn_no_input": "Proszę najpierw wpisać tekst lub wybrać plik.",
        "success_pdf": "Dokument wczytany! Kliknij przycisk.",
        "img_success": "Zdjęcie odebrane.",
        "clear_btn": "Zacznij od nowa"
    },
    "Deutsch": { "title": "MediClear AI", "subtitle": "Ihr persönlicher medizinischer Übersetzer", "intro": "Haben Sie einen medizinischen Text, der schwer zu verstehen ist?", "step1": "1. Methode wählen", "tab_text": "✍️ Text eingeben", "tab_upload": "📸 Foto/PDF hochladen", "input_placeholder": "Arztbrief hier eingeben...", "upload_label": "Datei wählen", "image_caption": "Hochgeladenes Bild", "analyze_btn": "Einfach erklären", "analyzing": "Einen Moment...", "result_title": "Erklärung", "listen_btn": "🔊 Vorlesen", "chat_title": "Fragen?", "chat_placeholder": "Frage eingeben...", "settings_header": "Einstellungen", "lang_select": "Sprache wählen:", "footer": "Hinweis: KI-Assistent. Im Zweifelsfall Arzt fragen.", "error_api": "API Key fehlt.", "warn_no_input": "Bitte Text eingeben.", "success_pdf": "PDF geladen.", "img_success": "Bild geladen.", "clear_btn": "Neustart" },
    "Français": { "title": "MediClear AI", "subtitle": "Votre traducteur médical personnel", "intro": "Avez-vous un texte médical difficile à comprendre?", "step1": "1. Choisissez votre méthode", "tab_text": "✍️ Saisir le texte", "tab_upload": "📸 Télécharger Photo/PDF", "input_placeholder": "Saisissez le texte ici...", "upload_label": "Choisir un fichier", "image_caption": "Image téléchargée", "analyze_btn": "Expliquer simplement", "analyzing": "Un instant...", "result_title": "Explication", "listen_btn": "🔊 Lire à haute voix", "chat_title": "Des questions?", "chat_placeholder": "Posez votre question...", "settings_header": "Paramètres", "lang_select": "Choisissez votre langue:", "footer": "Note: Assistant IA. Consultez un médecin en cas de doute.", "error_api": "Clé API manquante.", "warn_no_input": "Veuillez saisir du texte.", "success_pdf": "PDF chargé.", "img_success": "Image chargée.", "clear_btn": "Recommencer" },
    "Español": { "title": "MediClear AI", "subtitle": "Su traductor médico personal", "intro": "¿Tiene un texto médico difícil de entender?", "step1": "1. Elija su método", "tab_text": "✍️ Escribir texto", "tab_upload": "📸 Subir Foto/PDF", "input_placeholder": "Escriba el texto aquí...", "upload_label": "Elegir archivo", "image_caption": "Imagen subida", "analyze_btn": "Explicar simplemente", "analyzing": "Un momento...", "result_title": "Explicación", "listen_btn": "🔊 Leer en voz alta", "chat_title": "¿Preguntas?", "chat_placeholder": "Escriba su pregunta...", "settings_header": "Ajustes", "lang_select": "Elija su idioma:", "footer": "Nota: Asistente de IA. Consulte a su médico.", "error_api": "Falta la clave API.", "warn_no_input": "Por favor ingrese texto.", "success_pdf": "PDF cargado.", "img_success": "Imagen cargada.", "clear_btn": "Reiniciar" },
}

# --- CUSTOM CSS FOR ACCESSABILITY & MODERN UX ---
st.markdown("""
<style>
    /* 1. Global App Background & Font */
    [data-testid="stAppViewContainer"] {
        background-color: #f0f2f6;
    }
    
    html, body, [class*="css"]  {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        color: #1f2937; /* Forceer donkergrijze tekst */
    }

    /* 2. Typography */
    h1 { 
        color: #1e3a8a !important; 
        font-weight: 700 !important;
    }
    h2, h3 { 
        color: #334155 !important; 
        font-weight: 600 !important;
    }
    p, li, span, div {
        color: #1f2937; /* Leesbaarheid garanderen */
    }

    /* 3. Cards / Containers */
    /* Zorg dat input velden duidelijk begrensd zijn */
    .stTextArea, .stFileUploader {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Zorg dat tekst IN textareas ook donker is */
    .stTextArea textarea {
        color: #1f2937 !important;
        background-color: #ffffff !important; 
    }

    /* Result Block */
    [data-testid="stMarkdownContainer"] p {
        font-size: 18px;
    }

    /* 4. Buttons */
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white !important;
        font-size: 20px !important;
        padding: 0.75rem 2rem !important;
        border-radius: 50px !important;
        border: none;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.2);
        transition: transform 0.2s;
        display: block;
        margin: 0 auto;
    }
    .stButton button[kind="primary"]:hover {
        transform: scale(1.02);
    }
    
    .stButton button[kind="secondary"] {
        background-color: white;
        color: #1f2937 !important;
        border: 2px solid #e5e7eb;
    }

    /* 5. Sidebar Polish */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    [data-testid="stSidebar"] h1 {
        font-size: 1.5rem !important;
    }
    /* Fix voor witte tekst in sidebar */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #374151 !important;
    }
    
    /* 6. Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #ffffff;
        border-radius: 8px 8px 0 0;
        border: 1px solid #e5e7eb;
        border-bottom: none;
        color: #6b7280; 
    }
    .stTabs [aria-selected="true"] {
        background-color: #eff6ff;
        color: #1d4ed8 !important;
        border-color: #bfdbfe;
        font-weight: 600;
    }

</style>
""", unsafe_allow_html=True)


# --- STATE MANAGEMENT ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_text" not in st.session_state:
    st.session_state.current_text = ""
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "selected_language" not in st.session_state:
    st.session_state.selected_language = "Nederlands"

# --- SIDEBAR (Minimal Technical Settings) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=100) # Generic medical icon
    st.title("Admin")

    # Secure API Key handling
    with st.expander("🔐 Technische Instellingen (API)", expanded=False):
        api_key_input = st.text_input("Google API Key", type="password")
        if api_key_input:
            api_key = api_key_input
        else:
            # DO NOT HARDCODE YOUR KEY HERE. Use .env file or Streamlit secrets.
            api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            st.error("⚠️ API Key nodig!")

    st.markdown("---")
    if st.button("🗑️ " + TRANSLATIONS[st.session_state.selected_language]["clear_btn"]):
        st.session_state.chat_history = []
        st.session_state.current_text = ""
        st.session_state.analysis_done = False
        st.rerun()

# --- MAIN HEADER AREA (Language & Title) ---

# Language selector promimently at the top
col_title, col_lang = st.columns([3, 1])

with col_lang:
    # Update language based on selection
    selected_lang = st.selectbox(
        "🌍 Language / Taal",
        options=list(TRANSLATIONS.keys()),
        index=0
    )
    st.session_state.selected_language = selected_lang

# Shortcut to current translations
T = TRANSLATIONS[st.session_state.selected_language]

with col_title:
    st.title(f"🏥 {T['title']}")
    st.markdown(f"**{T['subtitle']}**")

st.markdown("---")
st.info(f"ℹ️ {T['intro']}")

# --- INPUT SECTION ---
st.subheader(T['step1'])

tab_text, tab_upload = st.tabs([T['tab_text'], T['tab_upload']])

extracted_text = ""
input_image = None
has_input = False

with tab_text:
    text_input = st.text_area("invoer", label_visibility="collapsed", height=200, placeholder=T['input_placeholder'])
    if text_input:
        extracted_text = text_input
        has_input = True

with tab_upload:
    uploaded_file = st.file_uploader(
        T['upload_label'],
        type=['pdf', 'png', 'jpg', 'jpeg'],
        label_visibility="visible"
    )

    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            try:
                reader = PdfReader(uploaded_file)
                pdf_text = ""
                for page in reader.pages:
                    pdf_text += page.extract_text()
                extracted_text = pdf_text
                has_input = True
                st.success(f"📄 {T['success_pdf']}")
            except Exception as e:
                st.error(f"❌ PDF Error: {e}")

        elif uploaded_file.type.startswith('image'):
            input_image = Image.open(uploaded_file)
            st.image(input_image, caption=T['image_caption'], width=300)
            st.success(f"🖼️ {T['img_success']}")
            has_input = True

st.markdown("<br>", unsafe_allow_html=True) # Spacer

# --- ACTION BUTTON ---
col_L, col_btn, col_R = st.columns([1, 2, 1])
with col_btn:
    process_btn = st.button(f"✨ {T['analyze_btn']}", use_container_width=True, type="primary")

# --- PROCESSING ---
if process_btn:
    if not api_key:
        st.error(T['error_api'])
    elif not has_input and not input_image:
        st.warning(T['warn_no_input'])
    else:
        try:
            # Configure Gemini
            genai.configure(api_key=api_key)

            # Helper to try generating content with fallback
            def generate_with_fallback(prompt_parts, is_image=False):
                # Updated model list based on available models
                models_to_try = [
                    'gemini-2.5-flash',
                    'gemini-2.0-flash',
                    'gemini-pro-latest'
                ]

                last_error = None
                for model_name in models_to_try:
                    try:
                        model = genai.GenerativeModel(model_name)
                        return model.generate_content(prompt_parts)
                    except Exception as e:
                        last_error = e
                        # If it's a 404 or specific error, continue to next model
                        if "404" in str(e) or "not found" in str(e).lower():
                            continue
                        else:
                            # If it's another error (like auth), raise it
                            raise e
                raise last_error

            with st.spinner(f"🕵️ {T['analyzing']}"):

                # Prompt depends on language
                base_prompt = f"""
                Je bent een behulpzame, geduldige medische assistent.
                DOEL: Vertaal de volgende medische informatie naar zeer eenvoudige, geruststellende taal voor een patiënt.
                TAAL: Ik wil het antwoord in het: {st.session_state.selected_language}.
                NIVEAU: Basisschool niveau (B1). Geen moeilijke woorden, of leg ze uit.
                
                STRUCTUUR:
                1. Wat is er aan de hand? (Samenvatting)
                2. Wat betekent dit voor mij?
                3. Begrippenlijstje (indien nodig)
                
                (Geef geen medisch advies, verwijs altijd door naar de arts).
                """

                # Generate
                if input_image:
                    response = generate_with_fallback([base_prompt, input_image], is_image=True)
                else:
                    response = generate_with_fallback(f"{base_prompt}\n\nTEKST:\n{extracted_text}", is_image=False)

                st.session_state.current_text = response.text
                st.session_state.analysis_done = True

                # Reset chat on new analysis
                st.session_state.chat_history = []
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})

        except Exception as e:
            st.error(f"Error ({e})")

# --- RESULTS SECTION ---
if st.session_state.analysis_done:
    st.divider()

    st.markdown(f"## ✅ {T['result_title']}")

    # Result Container with white background
    with st.container(border=True):
        st.markdown(st.session_state.current_text)

    # Audio Button
    if st.button(f"🔊 {T['listen_btn']}"):
         try:
            # Map full language name to IO code roughly
            lang_map = {
                "Nederlands": "nl", "English": "en", "Türkçe": "tr",
                "العربية": "ar", "Polski": "pl", "Deutsch": "de",
                "Français": "fr", "Español": "es"
            }
            code = lang_map.get(st.session_state.selected_language, "nl")

            tts = gTTS(text=st.session_state.current_text, lang=code)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                tts.save(fp.name)
                st.audio(fp.name, format="audio/mp3")
         except Exception as e:
             st.error(f"Audio error: {e}")

    # --- CHAT SECTION ---
    st.divider()
    st.subheader(f"💬 {T['chat_title']}")

    # Clean Chat Interface
    for message in st.session_state.chat_history:
        if message["role"] != "assistant" or message["content"] != st.session_state.current_text:
             with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input(T['chat_placeholder']):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                 # Helper to try generating content with fallback (redefined here or moved to scope)
                 # Since it's inside another scope, let's just do a simple try/except fallback for chat
                 try:
                    # Upgrade to valid available models
                    model_chat = genai.GenerativeModel('gemini-2.5-flash')
                    chat_context = f"""
                    Context: De gebruiker stelt een vraag over de vertaalde medische tekst.
                    Huidige Vertaling: {st.session_state.current_text}
                    Gebruikersvraag: "{prompt}"
                    
                    Antwoord in het {st.session_state.selected_language}. Houd het kort, simpel en vriendelijk.
                    """
                    response_stream = model_chat.generate_content(chat_context)
                 except Exception as e:
                    if "404" in str(e) or "not found" in str(e).lower():
                        # Fallback to 2.0 if 2.5 fails
                        model_chat = genai.GenerativeModel('gemini-2.0-flash')
                        chat_context = f"""
                        Context: De gebruiker stelt een vraag over de vertaalde medische tekst.
                        Huidige Vertaling: {st.session_state.current_text}
                        Gebruikersvraag: "{prompt}"
                        
                        Antwoord in het {st.session_state.selected_language}. Houd het kort, simpel en vriendelijk.
                        """
                        response_stream = model_chat.generate_content(chat_context)
                    else:
                        raise e

                 st.markdown(response_stream.text)
                 st.session_state.chat_history.append({"role": "assistant", "content": response_stream.text})
            except Exception as e:
                st.error(f"Chat error: {e}")

# Footer
st.markdown("---")
st.caption(f"🏥 MediClear AI - {T['footer']}")
