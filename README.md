# 🏥 MediClear AI

**Your Personal Medical Translator**

MediClear AI is an intelligent web application designed to bridge the gap between complex medical jargon and patient understanding. Powered by Google's advanced **Gemini 2.5 Flash** models, it translates clinical notes, doctor's letters, and medical terminology into simple, reassuring language (B1 level).

## ✨ Features

- **📄 Multi-Source Input**:
  - Type or paste text directly.
  - Upload **PDFs** (medical letters).
  - Upload **Images/Photos** (scans, prescriptions) with built-in OCR.
- **🌍 Multi-Language Support**: Instant translation into Dutch, English, Turkish, Arabic, Polish, German, French, and Spanish.
- **🧠 Advanced AI Analysis**: Uses `gemini-2.5-flash` for high-speed, multimodal understanding.
- **🔊 Text-to-Speech**: Listen to the simplified explanation with one click.
- **💬 Interactive Chat**: Ask follow-up questions about the translation in a conversational interface.
- **♿ Accessible Design**: High-contrast UI, clear typography, and simplified navigation suitable for all users.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- A Google Gemini API Key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mediclear-ai.git
   cd mediclear-ai
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - Create a `.env` file in the root directory.
   - Add your API key:
     ```
     GOOGLE_API_KEY=your_api_key_here
     ```

### Running the App

```bash
streamlit run main.py
```

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **AI Engine**: [Google Gemini](https://ai.google.dev/) (via `google-generativeai`)
- **Audio**: gTTS (Google Text-to-Speech)
- **PDF Processing**: PyPDF2
- **Image Processing**: Pillow (PIL)

## ⚠️ Disclaimer

This tool is an AI assistant meant for educational and informational purposes only. It does not replace professional medical advice. Always consult a doctor for medical concerns.
