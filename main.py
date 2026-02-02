import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure page settings
st.set_page_config(
    page_title="MediClear AI",
    page_icon="🏥",
    layout="wide"
)

# Sidebar for API Key configuration
with st.sidebar:
    st.header("Instellingen")
    # Try to get key from input, otherwise from env
    api_key_input = st.text_input("Google Gemini API Key", type="password", help="Voer je Google Gemini API key in.")

    if api_key_input:
        api_key = api_key_input
    else:
        api_key = os.getenv("GOOGLE_API_KEY")

    st.markdown("---")
    st.markdown("""
    **Over MediClear AI**
    
    Een intelligente "medische vertaalmachine" die complexe klinische verslagen en jargon omzet naar begrijpelijke taal (B1-niveau) voor patiënten.
    
    **Tech Stack:**
    - Engine: Google Gemini API
    - Backend: Python
    - Frontend: Streamlit
    """)

# Main content
st.title("🏥 MediClear AI")
st.subheader("Powered by Google Gemini")

st.markdown("""
Welkom bij **MediClear AI**. Plak hieronder een medische tekst, en wij vertalen het naar begrijpelijke taal.
""")

# Input area
medical_text = st.text_area("Voer de medische tekst in:", height=200, placeholder="Bijvoorbeeld: Patiënt vertoont symptomen van acute bronchitis met dyspneu...")

# Button to trigger translation
if st.button("Vertaal naar begrijpelijke taal"):
    if not api_key:
        st.error("⚠️ Geen API key gevonden. Voer deze in via de sidebar of stel de GOOGLE_API_KEY omgevingsvariabele in (bijv. in een .env bestand).")
    elif not medical_text:
        st.warning("⚠️ Voer alstublieft een tekst in om te vertalen.")
    else:
        try:
            # Configure Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')

            # Construct the prompt
            prompt = f"""
            Je bent een behulpzame medische assistent. Jouw taak is om de onderstaande medische tekst te herschrijven naar begrijpelijke taal (taalniveau B1) voor een patiënt.
            
            Richtlijnen:
            1. Gebruik eenvoudige woorden in plaats van medisch jargon.
            2. Leg moeilijke begrippen kort uit als ze niet te vermijden zijn.
            3. Houd de toon empathisch en geruststellend, maar professioneel.
            4. Zorg dat de feitelijke medische informatie 100% correct blijft.
            5. Structureer de tekst met duidelijke alinea's of opsommingstekens indien nodig.

            Hier is de medische tekst:
            "{medical_text}"
            """

            with st.spinner("Bezig met analyseren en vertalen..."):
                response = model.generate_content(prompt)

                st.success("✅ Vertaling voltooid!")
                st.markdown("### Begrijpelijke uitleg:")
                st.write(response.text)

        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verbinden met Gemini: {str(e)}")
