import spacy
import torch
from transformers import AutoModel, AutoTokenizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
import os
import re
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Logic to handle different environments (CPU vs CUDA)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

class NLPEngine:
    def __init__(self):
        self.model_name = "ai4bharat/indic-bert" # Or 'bert-base-multilingual-cased'
        self.tokenizer = None
        self.model = None
        self.nlp = None
        self.kb_embeddings = {}
        self.kb_questions = []
        self.kb_intents = []
        self.is_ready = False
        self._gemini_model = None
        self._last_api_key = None
        
        # Load FAQ data
        try:
            with open("faqs.json", "r", encoding="utf-8") as f:
                self.faqs = json.load(f)
        except Exception:
            self.faqs = []

    def load_models(self):
        """Loads models. This might take time."""
        print("Loading NLP models...")
        try:
            # Load spaCy
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except:
                print("Spacy model not found. Run: python -m spacy download en_core_web_sm")
                self.nlp = None

            # Load SentenceTransformer
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device=DEVICE)
                self.is_ready = True
                self._build_kb_index()
                print("NLP Models loaded successfully.")
            except ImportError:
                print("Warning: Advanced NLP models could not be loaded due to environment issues. Falling back to keyword matching.")
                self.is_ready = False
            except Exception as e:
                print(f"Warning: NLP Model load failed ({str(e)}). Using keyword fallback.")
                self.is_ready = False

        except Exception as e:
            print(f"NLP Engine Initialization Error: {e}")
            self.is_ready = False

    def _get_embedding(self, text):
        if not self.is_ready:
            return np.zeros(384)
            
        # SentenceTransformer encode returns numpy array by default
        return self.model.encode(text)

    def _build_kb_index(self):
        # We index all questions (Hi, Ta, En) pointing to the same intent
        for item in self.faqs:
            intent = item['intent']
            for lang in ['question_hi', 'question_ta', 'question_en']:
                q = item.get(lang)
                if q:
                    emb = self._get_embedding(q)
                    self.kb_questions.append(emb)
                    self.kb_intents.append(intent)
        
        if self.kb_questions:
            self.kb_embeddings = np.array(self.kb_questions)

    def reload_kb(self):
        """Reloads the FAQs from JSON and re-builds the index."""
        try:
            with open("faqs.json", "r", encoding="utf-8") as f:
                self.faqs = json.load(f)
            self.kb_questions = []
            self.kb_intents = []
            if self.is_ready:
                self._build_kb_index()
            print("NLP Knowledge Base reloaded successfully.")
        except Exception as e:
            print(f"Error reloading KB: {e}")

    def predict_intent(self, text):
        """Returns (intent, confidence)."""
        if not self.is_ready or len(self.kb_embeddings) == 0:
            # Fallback: Simple keyword match (Improved)
            text_lower = text.lower()
            for item in self.faqs:
                # Check English question
                if item['question_en'].lower() in text_lower or text_lower in item['question_en'].lower():
                    return item['intent'], 1.0, [("keyword_match_en", 1.0)]
                # Check Hindi (partial)
                if item['question_hi'] and (item['question_hi'] in text or text in item['question_hi']):
                     return item['intent'], 1.0, [("keyword_match_hi", 1.0)]
                # Check Tamil (partial)
                if item['question_ta'] and (item['question_ta'] in text or text in item['question_ta']):
                     return item['intent'], 1.0, [("keyword_match_ta", 1.0)]
            
            return None, 0.0, [("no_match", 0.0)]

        target_emb = self._get_embedding(text)
        
        # Cosine similarity
        sims = cosine_similarity([target_emb], self.kb_embeddings)[0]
        max_idx = np.argmax(sims)
        score = sims[max_idx]
        
        # Get top 3 for debug
        top_indices = sims.argsort()[-3:][::-1]
        debug_info = [(self.kb_intents[i], float(sims[i])) for i in top_indices]

        if score > 0.3: # Lowered threshold from 0.4 to 0.3
             return self.kb_intents[max_idx], float(score), debug_info
        
        return None, float(score), debug_info

    def get_gemini_response(self, api_key, query, context=None, lang='en'):
        """Generates a response using Gemini API with optional RAG context."""
        if not genai:
            return "Error: google-generativeai package not installed.", "Error"

        try:
            # Only re-configure if API key changes or model isn't loaded
            if api_key != self._last_api_key or self._gemini_model is None:
                genai.configure(api_key=api_key)
                self._gemini_model = genai.GenerativeModel('gemini-flash-latest')
                self._last_api_key = api_key

            lang_names = {'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil'}
            target_lang = lang_names.get(lang, 'English')

            system_prompt = f"""
            You are a helpful and accurate Indian Legal Assistant. 
            Your goal is to provide legal information based on Indian Laws (BNS, CrPC, IPC, etc.).
            
            Strict Guidelines:
            1. Answer ALWAYS in {target_lang}.
            2. Be concise and professional.
            3. If context is provided below, use it to ensure accuracy. 
            4. If the question is outside legal scope, politely say you can only help with legal queries.
            5. Always cite the relevant sections or laws if known.
            6. If you do not know the answer, do not guess or provide incorrect information. Simply reply with 'I need more info'.
            """

            full_prompt = f"{system_prompt}\n\n"
            if context:
                full_prompt += f"--- CONTEXT FROM DATABASE ---\n{context}\n-----------------------------\n\n"
            
            full_prompt += f"User Query: {query}"

            response = self._gemini_model.generate_content(full_prompt)
            
            # Simple logic to generate a slug-like intent from query
            suggested_intent = re.sub(r'[^a-zA-Z0-9]', '_', query.lower())[:30].strip('_')
            
            if response and hasattr(response, 'text'):
                return response.text, "Generated by Gemini AI", suggested_intent
            else:
                return "I'm sorry, I couldn't generate a response. Please try again.", "AI Error", "error"

        except Exception as e:
            return f"Gemini AI Error: {str(e)}", "Error", "error"

    def extract_entities(self, text):
        """Extracts entities using spaCy and regex."""
        entities = {}
        
        # Regex for common legal keywords
        legal_terms = re.findall(r'(FIR|arrest|bail|divorce|dowry|landlord|deposit|wages|salary)', text, re.IGNORECASE)
        if legal_terms:
            entities['legal_terms'] = legal_terms

        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                entities[ent.label_] = ent.text
                
        return entities

# Singleton instance
nlp_engine = NLPEngine()
