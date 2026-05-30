# Multilingual KYR (Know Your Rights) Legal Assistant

A mobile-first, voice-enabled chatbot for legal assistance in India, supporting Hindi and Tamil.

## Features
- **Voice/Text Interface**: Speak or type queries.
- **Multilingual**: Hindi, Tamil, English support.
- **Legal Knowledge Base**: Answers based on Constitution, IPC, and Labor Laws.
- **Escalation**: Connect to lawyers for complex cases.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

2. Run the app:
   ```bash
   streamlit run app.py
   ```

## Files
- `app.py`: Main application.
- `nlp_engine.py`: Intent and entity recognition.
- `legal_db.py`: SQLite database handler.
- `voice_handler.py`: TTS and STT utilities.
- `faqs.json`: Legal knowledge base.

## Deployment
Ready for Vercel or Streamlit Cloud.
