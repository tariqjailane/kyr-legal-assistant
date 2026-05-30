import streamlit as st
import time
from nlp_engine import nlp_engine
from legal_db import get_answer_by_intent, init_db, search_db, add_to_db
from voice_handler import voice_handler
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Load environment variables (API Keys, etc.)
load_dotenv()

# Page Config
st.set_page_config(
    page_title="KYR Legal Assistant",
    page_icon="⚖️",
    layout="centered", # Better for mobile/whatsapp simulation
    initial_sidebar_state="collapsed"
)

# Load Custom CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

# CSS to hide sidebar arrow for a cleaner "No Sidebar" experience
st.markdown("""
<style>
    [data-testid="collapsedControl"] {
        display: none
    }
</style>
""", unsafe_allow_html=True)

# Initialize DB and NLP
init_db()

@st.cache_resource
def load_nlp_system_v2():
    nlp_engine.load_models()
    return nlp_engine

with st.spinner("Connecting..."):
    nlp_engine = load_nlp_system_v2()

if 'messages' not in st.session_state:
    st.session_state['messages'] = []
    st.session_state['lang'] = 'en'
    # Initialize API key from ENV if available
    st.session_state['gemini_api_key'] = os.getenv("GEMINI_API_KEY", "")
    # Prioritize DB (Free & Unlimited), with AI as Smart Fallback
    st.session_state['use_ai_prioritized'] = False
    # Welcom message
    st.session_state['messages'].append({
        "role": "assistant",
        "content": "Hi! I am your KYR Legal Assistant.\nAsk me about your rights (e.g., Arrest, FIR, or even Ragging in college!)."
    })

# --- Localization ---
TRANSLATIONS = {
    'en': {
        'title': "Legal Assistant",
        'subtitle': "Online",
        'placeholder': "Type a message",
        'mic_label': "Record",
        'lawyer_btn': "Call Lawyer",
        'feedback': "Rate Us",
        'response_time': "Response time",
        'processing': "Processing...",
        'escalation': "Connecting to a lawyer...",
        'rights_page': "Your Rights"
    },
    'hi': {
        'title': "कानूनी सहायक",
        'subtitle': "ऑनलाइन",
        'placeholder': "संदेश लिखें...",
        'mic_label': "रिकॉर्ड",
        'lawyer_btn': "वकील का नंबर",
        'feedback': "रेट करें",
        'response_time': "प्रतिक्रिया समय",
        'processing': "प्रक्रिया चल रही है...",
        'escalation': "वकील से संपर्क किया जा रहा है...",
        'rights_page': "आपके अधिकार"
    },
    'ta': {
        'title': "சட்ட உதவியாளர்",
        'subtitle': "ஆன்லைனில்",
        'placeholder': "செய்தியை தட்டச்சு செய்க...",
        'mic_label': "பதிவு",
        'lawyer_btn': "வழக்கறிஞரை அழை",
        'feedback': "மதிப்பிடுங்கள்",
        'response_time': "பதில் நேரம்",
        'processing': "செயலாக்கப்படுகிறது...",
        'escalation': "வழக்கறிஞரை இணைக்கிறது...",
        'rights_page': "உங்கள் உரிமைகள்"
    }
}

def get_text(key):
    return TRANSLATIONS[st.session_state['lang']].get(key, key)

# --- Top Header (WhatsApp Style) ---
html_header = f"""
<div class="whatsapp-header">
    <div class="header-avatar">⚖️</div>
    <div class="header-info">
        <div class="header-name">{get_text('title')}</div>
        <div class="header-status">{get_text('subtitle')}</div>
    </div>
</div>
"""
st.markdown(html_header, unsafe_allow_html=True)

# --- Settings Expander (Replaces Sidebar) ---
with st.expander("⚙️ Settings / செட்டிங்ஸ் / सेटिंग"):
    st.caption("🌐 Language / भाषा")
    lang_options = ["English", "हिंदी (Hindi)", "தமிழ் (Tamil)"]
    # Sync radio with current session state
    lang_idx = 0
    if st.session_state['lang'] == 'hi': lang_idx = 1
    elif st.session_state['lang'] == 'ta': lang_idx = 2
    
    lang = st.radio("Select Language", lang_options, index=lang_idx, horizontal=True)
    if lang.startswith("English"): st.session_state['lang'] = 'en'
    elif lang.startswith("हिंदी"): st.session_state['lang'] = 'hi'
    elif lang.startswith("தமிழ்"): st.session_state['lang'] = 'ta'
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Chat", type="primary"):
            st.session_state['messages'] = []
            st.rerun()
    with col2:
        st.caption("AI Mode: **Priority**")
        st.caption("Language Detection: **Active**")
    st.markdown("### 📞 Helpline")
    st.info("**NALSA Free Legal Aid**\n\nCall: **15100**\nWebsite: [nalsa.gov.in](https://nalsa.gov.in)")

# --- Footer (Fixed) ---
footer_html = """
<div style='position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f1f1f1; color: black; text-align: center; padding: 10px; font-size: 14px; z-index: 1000;'>
    ⚖️ <strong>NALSA Free Legal Aid Helpline: 15100</strong> | Service is free for eligible persons
</div>
<br><br><br>
"""
st.markdown(footer_html, unsafe_allow_html=True)

# --- Chat Logic ---
def detect_language(text):
    hindi_score = 0
    tamil_score = 0
    english_score = 0
    
    for char in text:
        if '\u0900' <= char <= '\u097F': hindi_score += 1
        elif '\u0B80' <= char <= '\u0BFF': tamil_score += 1
        elif 'a' <= char.lower() <= 'z': english_score += 1
        
    if hindi_score > 0: return 'hi'
    if tamil_score > 0: return 'ta'
    if english_score > 0: return 'en'
    return None 

def process_query(user_query, input_type="text"):
    start_time = time.time()
    
    # Defaults
    intent = None
    confidence = 0.0
    debug_info = []
    source = "DB"
    res_intent = None

    detected_lang = detect_language(user_query)
    # Only switch if current is 'en' and we detect Hi/Ta, OR if signal is very strong
    if detected_lang and detected_lang != st.session_state['lang']:
        if st.session_state['lang'] == 'en' or (detected_lang in ['hi', 'ta']):
             st.session_state['lang'] = detected_lang

    # 2. If AI Prioritized and Key present -> Skip DB
    if st.session_state.get('use_ai_prioritized') and st.session_state.get('gemini_api_key'):
        source = "LLM"
    else:
        # 3. Intent Recognition (Database)
        intent, confidence, debug_info = nlp_engine.predict_intent(user_query)
        
        # Threshold increased to 0.6 to avoid "Wrong Law" (False Positives)
        if intent and confidence > 0.6:
            source = "DB_INTENT"
        else:
            # 3. Fallback Search
            results = search_db(user_query, st.session_state['lang'])
            if results and results[0][1] >= 2: # High confidence keyword match
                res_intent = results[0][0]
                source = "DB_SEARCH"
            elif results and results[0][1] == 1:
                # Only 1 match - check if it's a very short query
                if len(user_query.split()) <= 3:
                     res_intent = results[0][0]
                     source = "DB_SEARCH"
                else:
                     source = "LLM" # Ambiguous, use AI
            else:
                source = "LLM" # Last resort

    # Fetching Content
    answer_text = ""
    citation = ""
    case_study = ""
    
    # Execute Logic
    if source in ["DB_INTENT", "DB_SEARCH"]:
        target_intent = intent if source == "DB_INTENT" else res_intent
        ans, cit, cs = get_answer_by_intent(target_intent, st.session_state['lang'])
        answer_text = ans
        citation = cit
        case_study = cs
        
    elif source == "LLM":
        api_key = st.session_state.get('gemini_api_key')
        if api_key:
            with st.spinner("AI is thinking..."):
                # RAG: Let's get some context from DB even if intent wasn't clear
                search_results = search_db(user_query, st.session_state['lang'])
                db_context = ""
                if search_results:
                    # Get top 2 results for context
                    for res_intent, score in search_results[:2]:
                        ans, cit, cs = get_answer_by_intent(res_intent, st.session_state['lang'])
                        db_context += f"Intent: {res_intent}\nAnswer: {ans}\nLaw: {cit}\n\n"
                
                answer_text, citation, sug_intent = nlp_engine.get_gemini_response(
                    api_key=api_key,
                    query=user_query,
                    context=db_context,
                    lang=st.session_state['lang']
                )
                case_study = ""
                
                if "429" in answer_text:
                    answer_text = "⚠️ **AI Limit Reached (Free Tier).** I am switching to my internal database for now. Please try again in 1 minute!"
                    if st.session_state['lang'] == 'hi': answer_text = "⚠️ **AI की सीमा समाप्त।** अभी के लिए मैं अपने डेटाबेस का उपयोग कर रहा हूँ। कृपया 1 मिनट बाद पुनः प्रयास करें!"
                    elif st.session_state['lang'] == 'ta': answer_text = "⚠️ **AI வரம்பு முடிந்தது.** தற்போது எனது தரவுத்தளத்தைப் பயன்படுத்துகிறேன். தயவுசெய்து 1 நிமிடம் கழித்து மீண்டும் முயற்சிக்கவும்!"
                
                # PERSISTENCE: Save to DB if Gemini gave a valid answer
                if sug_intent != "error" and "429" not in answer_text:
                    add_to_db(sug_intent, user_query, answer_text, st.session_state['lang'], citation)
                    nlp_engine.reload_kb()
                    st.toast("✅ Knowledge saved to database for future use!")
        else:
            answer_text = "I couldn't find a confident match in my database. Please enable AI Mode with an API Key for better answers."
            if st.session_state['lang'] == 'hi': answer_text = "डेटाबेस में कोई अच्छा मेल नहीं मिला। बेहतर उत्तर के लिए कृपया API Key दर्ज करें।"
            elif st.session_state['lang'] == 'ta': answer_text = "எனது தரவுத்தளத்தில் சரியான பொருத்தம் கிடைக்கவில்லை. சிறந்த பதில்களுக்கு API Key-ஐ உள்ளிடவும்."

    end_time = time.time()
    
    metrics_str = f"{end_time-start_time:.2f}s | {source}"
    if confidence: metrics_str += f" ({confidence:.2f})"

    response = {
        "role": "assistant",
        "content": answer_text,
        "citation": citation,
        "case_study": case_study,
        "metrics": metrics_str,
        "debug": debug_info,
        "audio": False,
        "lang": st.session_state['lang'] # Store language for TTS
    }
    st.session_state['messages'].append(response)
    st.session_state['last_msg_idx'] = len(st.session_state['messages']) - 1 # Track for autoplay

# --- Chat Interface ---
for msg in st.session_state['messages']:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "citation" in msg and msg["citation"]:
            if msg["citation"] not in ["Generated by Gemini AI", "Generated by AI"]:
                st.markdown(f"**📜 Law:** {msg['citation']}")
        if "case_study" in msg and msg["case_study"]:
            st.markdown(f"**🧑‍⚖️ Case:** {msg['case_study']}")
        
        # Audio icon if user wants to hear it (Manual play)
        if msg["role"] == "assistant":
            col1, col2 = st.columns([1, 5])
            msg_idx = st.session_state['messages'].index(msg)
            msg_lang = msg.get("lang", st.session_state['lang'])
            
            with col1:
                if st.button("🔊", key=f"tts_{msg_idx}"):
                    audio_bytes = voice_handler.text_to_speech(msg["content"], msg_lang)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
            
            # AUTOPLAY: Trigger for the most recent message only
            if st.session_state.get('last_msg_idx') == msg_idx:
                with st.spinner("🔊 Speaking..."):
                    audio_bytes = voice_handler.text_to_speech(msg["content"], msg_lang)
                    if audio_bytes:
                        st.markdown(voice_handler.get_audio_player_html(audio_bytes), unsafe_allow_html=True)
                st.session_state['last_msg_idx'] = -1 # Prevent repeat on re-run
            with col2:
                # Add "Not satisfied? Ask AI" button if source was DB
                metrics = msg.get("metrics", "")
                if "DB" in metrics and st.button("Get more info", key=f"force_ai_{st.session_state['messages'].index(msg)}", type="primary"):
                    # Find the last user message to re-process
                    user_msgs = [m for m in st.session_state['messages'][:st.session_state['messages'].index(msg)] if m['role'] == 'user']
                    if user_msgs:
                        last_query = user_msgs[-1]['content'].replace("🎤 ", "")
                        st.info("Querying AI for better accuracy...")
                        st.session_state['use_ai_prioritized'] = True # Temporary force
                        process_query(last_query, "text")
                        st.session_state['use_ai_prioritized'] = False # Reset
                        st.rerun()

# --- Input Area ---
# Wrapper for fixed bottom input
st.markdown('<div class="input-spacer"></div>', unsafe_allow_html=True)

# Audio Input: We place it in a container that we will float with CSS
with st.container():
    try:
        # Show current language to user
        cur_lang_code = st.session_state.get('lang', 'en')
        lang_map = {'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil'}
        sr_code = 'ta-IN' if cur_lang_code == 'ta' else ('hi-IN' if cur_lang_code == 'hi' else 'en-IN')
        st.caption(f"🎙️ Listening in: **{lang_map.get(cur_lang_code)} ({sr_code})**")
        
        audio_value = st.audio_input(get_text('mic_label'))
        if audio_value:
            audio_bytes = audio_value.read()
            import hashlib
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            
            if st.session_state.get('last_audio_hash') != audio_hash:
                st.session_state['last_audio_hash'] = audio_hash
                with st.spinner(get_text('processing')):
                    transcribed_text, error_msg = voice_handler.transcribe_audio(audio_bytes, st.session_state['lang'])
                    if transcribed_text:
                        # Auto-detect language from transcription to keep things in sync
                        new_lang = detect_language(transcribed_text)
                        if new_lang:
                             st.session_state['lang'] = new_lang
                        
                        st.session_state['messages'].append({"role": "user", "content": f"🎤 {transcribed_text}"})
                        process_query(transcribed_text, "voice")
                        st.rerun()
                    else:
                        st.error(f"Error: {error_msg}")
    except AttributeError:
        st.warning("Update Streamlit for Voice Input.")

# Text Input (Fixed at bottom by Streamlit default)
user_input = st.chat_input(get_text('placeholder')) 

if user_input:
    st.session_state['messages'].append({"role": "user", "content": user_input})
    process_query(user_input, "text")
    st.rerun()

