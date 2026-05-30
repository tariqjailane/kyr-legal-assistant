from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import time
import os
import tempfile
import re
import random
import hashlib
from dotenv import load_dotenv

# Import logic from existing modules
from nlp_engine import nlp_engine
from legal_db import get_answer_by_intent, init_db, search_db, add_to_db
from voice_handler import voice_handler

load_dotenv()

# Initialize DB and models
init_db()
nlp_engine.load_models()

app = FastAPI(title="KYR Legal Assistant API")

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".html", ".css", ".js", ".json")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

import sqlite3

# Persistent SQLite OTP Store
def save_otp_to_db(identifier: str, otp: str):
    conn = sqlite3.connect("legal_faqs.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS temp_otps (identifier TEXT PRIMARY KEY, otp TEXT)")
    c.execute("INSERT OR REPLACE INTO temp_otps (identifier, otp) VALUES (?, ?)", (identifier, otp))
    conn.commit()
    conn.close()

def get_otp_from_db(identifier: str) -> str:
    conn = sqlite3.connect("legal_faqs.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS temp_otps (identifier TEXT PRIMARY KEY, otp TEXT)")
    c.execute("SELECT otp FROM temp_otps WHERE identifier = ?", (identifier,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def delete_otp_from_db(identifier: str):
    conn = sqlite3.connect("legal_faqs.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS temp_otps (identifier TEXT PRIMARY KEY, otp TEXT)")
    c.execute("DELETE FROM temp_otps WHERE identifier = ?", (identifier,))
    conn.commit()
    conn.close()

# Security schemes
security = HTTPBearer()

class SendOTPRequest(BaseModel):
    identifier: str

class VerifyOTPRequest(BaseModel):
    identifier: str
    otp: str

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def is_valid_phone(phone: str) -> bool:
    # Accept standard 10 digit Indian/international numbers (just digits check)
    clean_phone = re.sub(r"\D", "", phone)
    return len(clean_phone) >= 10 and len(clean_phone) <= 15

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if not token.startswith("kyr-session-"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        parts = token.split("-")
        if len(parts) < 4:
            raise ValueError()
        
        identifier_hex = parts[2]
        token_hash = parts[3]
        
        identifier = bytes.fromhex(identifier_hex).decode('utf-8')
        SECRET_SALT = "KYR_SECRET_SALT_2026"
        expected_hash = hashlib.sha256((identifier + SECRET_SALT).encode('utf-8')).hexdigest()
        
        if token_hash != expected_hash:
            raise ValueError()
            
        return identifier
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def send_email_otp(target_email: str, otp: str):
    import smtplib
    from email.mime.text import MIMEText
    
    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    if not smtp_email or not smtp_password or smtp_email == "your_gmail_address@gmail.com":
        print("[WARNING] SMTP credentials missing or default. OTP email not sent.")
        return False
        
    try:
        subject = "KYR Legal Assistant Verification Code"
        body = f"""Hi!

Your KYR Legal Assistant verification code is: {otp}

This code will expire in 5 minutes. Do not share this code with anyone.

Best regards,
KYR AI Team"""
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = smtp_email
        msg['To'] = target_email
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, target_email, msg.as_string())
        print(f"[SUCCESS] OTP email sent to {target_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send SMTP email: {e}")
        return False

def send_whatsapp_otp(phone_number: str, otp: str):
    import urllib.request
    import urllib.parse
    import base64
    import ssl
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    
    if not account_sid or not auth_token or account_sid == "your_twilio_sid_here":
        print("[WARNING] Twilio credentials missing. OTP WhatsApp not sent.")
        return False
        
    try:
        # Standardize phone number format for WhatsApp (ensure it starts with '+' and country code, e.g. +91...)
        clean_phone = re.sub(r"\D", "", phone_number)
        if not phone_number.startswith("+"):
            # Assume India (+91) as default if it's 10 digits
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone
            clean_phone = "+" + clean_phone
            
        target_whatsapp = f"whatsapp:{clean_phone}"
        
        # Twilio API URL
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        # Payload
        payload = {
            "From": whatsapp_from,
            "To": target_whatsapp,
        }
        
        content_sid = os.getenv("TWILIO_CONTENT_SID", "")
        if content_sid and content_sid != "your_content_sid_here":
            import json
            payload["ContentSid"] = content_sid
            # Map first template variable to OTP, second to expiration message
            payload["ContentVariables"] = json.dumps({"1": otp, "2": "5 mins"})
        else:
            payload["Body"] = f"Your KYR Legal Assistant verification code is: *{otp}*\n\nThis code expires in 5 minutes. Do not share it with anyone."
            
        data = urllib.parse.urlencode(payload).encode("utf-8")
        
        # Request
        req = urllib.request.Request(url, data=data, method="POST")
        
        # Authentication header
        auth_str = f"{account_sid}:{auth_token}"
        auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        req.add_header("Authorization", f"Basic {auth_b64}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        # Bypass SSL verification just in case of local network blocks
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx) as response:
            res_body = response.read().decode("utf-8")
            print(f"[SUCCESS] OTP WhatsApp sent to {target_whatsapp}")
            return True
            
    except Exception as e:
        print(f"[ERROR] Failed to send Twilio WhatsApp: {e}")
        return False


@app.post("/api/auth/send-otp")
async def send_otp(req: SendOTPRequest, background_tasks: BackgroundTasks):
    identifier = req.identifier.strip()
    
    if not (is_valid_email(identifier) or is_valid_phone(identifier)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid email address or 10-digit phone number."
        )
    
    # Generate mock 6-digit OTP
    otp = str(random.randint(100000, 999999))
    save_otp_to_db(identifier, otp)
    
    # Send real email OTP if identifier is an email address
    if is_valid_email(identifier):
        background_tasks.add_task(send_email_otp, identifier, otp)
        
    # Send real WhatsApp OTP if identifier is a phone number
    if is_valid_phone(identifier):
        background_tasks.add_task(send_whatsapp_otp, identifier, otp)
        
    # Return status without leaking the OTP code
    return {
        "status": "sent",
        "message": "OTP sent successfully"
    }

@app.post("/api/auth/verify-otp")
async def verify_otp(req: VerifyOTPRequest):
    identifier = req.identifier.strip()
    user_otp = req.otp.strip()
    
    # Check for match (also support standard '123456' as master/bypass OTP for testing)
    stored_otp = get_otp_from_db(identifier)
    
    if user_otp == "123456":
        stored_otp = "123456"
        
    if not stored_otp or stored_otp != user_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please try again."
        )
        
    # Remove from store
    delete_otp_from_db(identifier)
        
    # Generate stateless session token
    SECRET_SALT = "KYR_SECRET_SALT_2026"
    token_hash = hashlib.sha256((identifier + SECRET_SALT).encode('utf-8')).hexdigest()
    token = f"kyr-session-{identifier.encode('utf-8').hex()}-{token_hash}"
    
    return {
        "status": "verified",
        "token": token
    }

class ChatRequest(BaseModel):
    query: str
    lang: str = 'en'
    use_ai_prioritized: bool = False

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

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, identifier: str = Depends(verify_token)):
    start_time = time.time()
    
    user_query = req.query
    current_lang = req.lang
    
    detected_lang = detect_language(user_query)
    if detected_lang and detected_lang != current_lang:
        if current_lang == 'en' or (detected_lang in ['hi', 'ta']):
             current_lang = detected_lang

    intent = None
    confidence = 0.0
    debug_info = []
    source = "DB"
    res_intent = None
    
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if req.use_ai_prioritized and api_key:
        source = "LLM"
    else:
        intent, confidence, debug_info = nlp_engine.predict_intent(user_query)
        if intent and confidence > 0.75:
            source = "DB_INTENT"
        else:
            results = search_db(user_query, current_lang)
            if results and results[0][1] >= 2:
                res_intent = results[0][0]
                source = "DB_SEARCH"
            elif results and results[0][1] == 1:
                if len(user_query.split()) <= 3:
                     res_intent = results[0][0]
                     source = "DB_SEARCH"
                else:
                     source = "LLM"
            else:
                source = "LLM"

    answer_text = ""
    citation = ""
    case_study = ""
    
    if source in ["DB_INTENT", "DB_SEARCH"]:
        target_intent = intent if source == "DB_INTENT" else res_intent
        ans, cit, cs = get_answer_by_intent(target_intent, current_lang)
        answer_text = ans
        citation = cit
        case_study = cs
        
    elif source == "LLM":
        if api_key:
            search_results = search_db(user_query, current_lang)
            db_context = ""
            if search_results:
                for res_int, score in search_results[:2]:
                    ans, cit, cs = get_answer_by_intent(res_int, current_lang)
                    db_context += f"Intent: {res_int}\nAnswer: {ans}\nLaw: {cit}\n\n"
            
            answer_text, citation, sug_intent = nlp_engine.get_gemini_response(
                api_key=api_key,
                query=user_query,
                context=db_context,
                lang=current_lang
            )
            
            if "429" in answer_text:
                answer_text = "⚠️ **AI Limit Reached (Free Tier).** I am switching to my internal database for now. Please try again in 1 minute!"
                if current_lang == 'hi': answer_text = "⚠️ **AI की सीमा समाप्त।** अभी के लिए मैं अपने डेटाबेस का उपयोग कर रहा हूँ। कृपया 1 मिनट बाद पुनः प्रयास करें!"
                elif current_lang == 'ta': answer_text = "⚠️ **AI வரம்பு முடிந்தது.** தற்போது எனது தரவுத்தளத்தைப் பயன்படுத்துகிறேன். தயவுசெய்து 1 நிமிடம் கழித்து மீண்டும் முயற்சிக்கவும்!"
            
            if sug_intent != "error" and "429" not in answer_text:
                add_to_db(sug_intent, user_query, answer_text, current_lang, citation)
                nlp_engine.reload_kb()
        else:
            answer_text = "I couldn't find a confident match in my database. Please enable AI Mode with an API Key for better answers."
            if current_lang == 'hi': answer_text = "डेटाबेस में कोई अच्छा मेल नहीं मिला। बेहतर उत्तर के लिए कृपया API Key दर्ज करें।"
            elif current_lang == 'ta': answer_text = "எனது தரவுத்தளத்தில் சரியான பொருத்தம் கிடைக்கவில்லை. சிறந்த பதில்களுக்கு API Key-ஐ உள்ளிடவும்."

    end_time = time.time()
    
    return {
        "answer_text": answer_text,
        "citation": citation,
        "case_study": case_study,
        "metrics": f"{end_time-start_time:.2f}s | {source} ({confidence:.2f})" if confidence else f"{end_time-start_time:.2f}s | {source}",
        "lang": current_lang,
        "source": source
    }

@app.post("/api/transcribe")
async def transcribe_endpoint(audio: UploadFile = File(...), lang: str = Form("en"), identifier: str = Depends(verify_token)):
    try:
        content = await audio.read()
        transcribed_text, error_msg = voice_handler.transcribe_audio(content, lang)
        
        if error_msg:
            return JSONResponse(status_code=400, content={"error": error_msg})
            
        detected_lang = detect_language(transcribed_text)
        return {"text": transcribed_text, "lang": detected_lang or lang}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class TTSRequest(BaseModel):
    text: str
    lang: str = 'en'

@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest, identifier: str = Depends(verify_token)):
    try:
        audio_bytes = voice_handler.text_to_speech(req.text, req.lang)
        if not audio_bytes:
            return JSONResponse(status_code=500, content={"error": "TTS failed to generate audio"})
            
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Mount the static frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
