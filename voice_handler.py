import os
import speech_recognition as sr
from gtts import gTTS
import base64
from io import BytesIO

# Try importing Google Cloud Speech data types if available
try:
    from google.cloud import speech
except ImportError:
    speech = None

class VoiceHandler:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def transcribe_audio(self, audio_bytes, lang='en-IN'):
        """
        Transcribes audio bytes to text.
        Prioritizes Google Cloud if credentials exist, else uses SpeechRecognition (Web API).
        """
        # If Google Cloud Creds are set
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and speech:
            try:
                client = speech.SpeechClient()
                audio = speech.RecognitionAudio(content=audio_bytes)
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, # Adjust based on input
                    language_code=lang,
                )
                response = client.recognize(config=config, audio=audio)
                if response.results:
                    return response.results[0].alternatives[0].transcript, None
            except Exception as e:
                return None, f"Google Cloud Error: {str(e)}"
        
        try:
            # Fallback: SpeechRecognition (uses Google Web Speech API - free tier)
            import io
            import soundfile as sf
            import numpy as np
            
            # Convert audio to standard WAV PCM_16 using soundfile
            # This handles various input formats (float32, etc) and sample rates
            data, samplerate = sf.read(io.BytesIO(audio_bytes))
            
            # DIGNOSTIC: Check max amplitude
            max_val = np.max(np.abs(data))
            if max_val == 0:
                 return None, "Microphone sent silent audio (Volume is 0). Check input device."
            
            # Normalize (Amplify) logic: Scale to max potential of float range (-1.0 to 1.0)
            # If max_val is < 0.5, boost it.
            if max_val < 0.5:
                 normalization_factor = 0.8 / max_val
                 data = data * normalization_factor
                 
            # Write key audio parameters to a clean buffer
            with io.BytesIO() as wav_buffer:
                sf.write(wav_buffer, data, samplerate, format='WAV', subtype='PCM_16')
                wav_buffer.seek(0)
                
                with sr.AudioFile(wav_buffer) as source:
                    # Adjust for noise - reduced duration for responsiveness
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
                    # Increase timeout slightly
                    audio_data = self.recognizer.record(source)
                    
                    # Explicitly map session language to Google Speech Recognition codes
                    sr_lang = 'hi-IN' if lang.startswith('hi') else ('ta-IN' if lang.startswith('ta') else 'en-IN')
                    
                    try:
                        # Attempt 1: Contextual/Selected Language
                        text = self.recognizer.recognize_google(audio_data, language=sr_lang)
                        print(f"STT Result [{sr_lang}]: {text}")
                        return text, None
                    except sr.UnknownValueError:
                        # Attempt 2: Auto-Fallback (If Tamil context is likely, try Tamil even if set to English)
                        # We try Tamil then Hindi as fallbacks for Indian users
                        fallbacks = ['ta-IN', 'hi-IN', 'en-IN']
                        for f_lang in fallbacks:
                            if f_lang == sr_lang: continue
                            try:
                                text = self.recognizer.recognize_google(audio_data, language=f_lang)
                                print(f"STT Fallback Success [{f_lang}]: {text}")
                                return text, None
                            except:
                                continue
                        
                        return None, f"Unintelligible Audio. (Signal Max: {max_val:.2f}). Speak louder or closer to mic."
                    except sr.RequestError as e:
                        return None, f"Could not request results from Google Speech Recognition service; {e}"
                    except Exception as e:
                        return None, f"Recognition Error: {str(e)}"
        except Exception as e:
             return None, f"System Error (Audio Processing): {str(e)}"

    def text_to_speech(self, text, lang='en'):
        """
        Converts text to speech audio bytes.
        """
        try:
            import re
            # Strip Markdown symbols: #, *, _, ~, `, [links], etc.
            clean_text = re.sub(r'[*#_~`>]', '', text) # Remove common symbols
            clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text) # Remove markdown links
            
            # Map lang to gTTS codes
            gtts_lang = 'hi' if lang.startswith('hi') else ('ta' if lang.startswith('ta') else 'en')
            
            tts = gTTS(text=clean_text, lang=gtts_lang, slow=False)
            fp = BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp.read()
        except Exception as e:
            print(f"TTS Error: {e}")
            return None

    def get_audio_player_html(self, audio_bytes):
        """Generates HTML for auto-playing audio."""
        b64 = base64.b64encode(audio_bytes).decode()
        md = f"""
            <audio controls autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        return md

voice_handler = VoiceHandler()
