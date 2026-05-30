# KYR (Know Your Rights) Legal Assistant - Presentation Material

This document contains everything you need to create your college presentation slides, including how the project works, the tech stack used, and potential viva/defense questions from external examiners.

---

## Part 1: How the Project is Made (Architecture & Workflow)

**1. User Interface (Frontend)**
- The frontend is built using **Streamlit**, customized with CSS to look like a modern, mobile-friendly chat application (similar to WhatsApp). 
- It supports Text input and Voice input, making it accessible to a wider audience.

**2. Query Processing & Language Detection**
- When a user asks a question, the system first detects the language (English, Hindi, or Tamil).
- It checks if the query can be answered using the local, offline database to save time and API costs.

**3. NLP Engine & Intent Matching (The Core Brain)**
- The user's query is converted into mathematical vectors (embeddings) using **Sentence-Transformers** (`paraphrase-multilingual-MiniLM-L12-v2`).
- The system calculates the `cosine similarity` between the user's query and pre-stored legal questions in the knowledge base (`faqs.json`).
- If there's a strong match (confidence > 0.6), it fetches the verified legal answer from the **SQLite Database**.

**4. Retrieval-Augmented Generation (RAG) & Gemini LLM (The Smart Fallback)**
- If the offline database doesn't have a clear answer, the system searches the database for relevant "context" and sends both the user's query and the context to the **Google Gemini API**.
- Gemini generates a highly accurate, conversational response based on Indian Law, strictly citing the context provided.
- Valid AI answers are automatically saved back to the local database for future use!

**5. Voice Processing (Accessibility)**
- The chatbot uses **SpeechRecognition** to transcribe user voice to text (Speech-to-Text).
- It normalizes quiet audio automatically using `soundfile` and `numpy`.
- Answers are spoken back to the user using **gTTS (Google Text-to-Speech)**.

---

## Part 2: What Things are Used in this Project (Tech Stack)

### 1. Frontend / UI
- **Streamlit**: For the web interface.
- **Vanilla CSS**: Custom styling to hide sidebars and make it look like a mobile chat app.

### 2. Machine Learning & NLP
- **Hugging Face Transformers / Sentence-Transformers**: Used for creating multilingual text embeddings to understand the "intent" of a sentence.
- **spaCy & NLTK**: For basic Natural Language Processing and entity extraction.
- **Scikit-Learn**: Specifically used for `cosine_similarity` to match vectors.
- **PyTorch**: Deep learning backend for running the sentence transformers.

### 3. Generative AI
- **Google Generative AI (Gemini Flash)**: Used as the Large Language Model (LLM) to generate conversational answers when standard database queries fail.

### 4. Database & Storage
- **SQLite**: A lightweight, serverless relational database (`legal_db.py`) used to store FAQs, laws, citations, and dynamically cache AI responses.
- **JSON**: Used as the initial knowledge base configuration (`faqs.json`).

### 5. Audio & Voice Processing
- **SpeechRecognition**: For capturing microphone input and converting speech to text.
- **gTTS (Google Text-to-Speech)**: For converting the bot's text responses into playable audio.
- **Soundfile & Numpy**: For reading and amplifying raw audio bytes.

---

## Part 3: External Examiner FAQs (Defense / Viva Questions)

Here are the questions an external examiner is most likely to ask you, along with how to answer them confidently.

**Q1: Why did you use both a local NLP Engine (Sentence Transformers) AND the Gemini API? Why not just use Gemini for everything?**
> **Answer:** Cost, speed, and reliability. Using an LLM for every single query is expensive and slow. By using local Sentence Transformers and a SQLite database for common questions (Intent Matching), we provide instant, free, and 100% verified answers. We only use Gemini as a "smart fallback" when a user asks a complex or highly specific question not found in our database.

**Q2: LLMs are known to hallucinate (make up facts). How do you ensure your legal bot gives accurate Indian law advice?**
> **Answer:** We implemented a RAG (Retrieval-Augmented Generation) pipeline. Before we send the prompt to Gemini, we search our local database for relevant laws. We inject this context into the system prompt and strictly instruct Gemini to only use the provided context or say "I need more information." This drastically reduces hallucinations.

**Q3: How does your system handle different languages? Did you train a custom model?**
> **Answer:** We didn't train a model from scratch. Instead, we used a pre-trained multilingual embedding model (`paraphrase-multilingual-MiniLM-L12-v2`). Our database has questions and answers stored in English, Hindi, and Tamil. The system detects the script of the user's input and uses multilingual embeddings to match the intent, regardless of the language.

**Q4: How does the voice feature handle background noise or low microphone volumes?**
> **Answer:** In `voice_handler.py`, we implemented audio normalization using the `soundfile` and `numpy` libraries. If the microphone records at a very low volume, the system mathematically scales up the amplitude before sending it to the SpeechRecognition engine. The engine also runs an `adjust_for_ambient_noise` function to handle static.

**Q5: What happens if the internet goes down or the Gemini API rate limit is reached? Will the app crash?**
> **Answer:** No, the app is highly resilient. If the Gemini API returns a 429 Rate Limit error, our system intercepts the error and gracefully falls back to the local SQLite database. It informs the user that AI is temporarily down but continues to serve standard legal questions offline.

**Q6: Why did you choose SQLite instead of a cloud database like MongoDB or Firebase?**
> **Answer:** Since this project is focused on immediate accessibility and privacy, a local SQLite database is perfect. It requires zero cloud configuration, operates offline, and is extremely fast for querying structured data like FAQs and intent labels.

**Q7: How does your system learn over time?**
> **Answer:** We implemented a persistence mechanism. When a user asks a new question and the Gemini API successfully generates an accurate response, the system dynamically saves that new Question-Answer pair into the SQLite database. The next time someone asks the same question, it is answered instantly from the local database without needing the LLM.

**Q8: What happens if the Gemini model gives a completely wrong or harmful legal answer (Hallucination)?**
> **Answer:** To prevent this, we use a three-layered safeguard:
> 1. **Retrieval-Augmented Generation (RAG):** We feed local, verified laws from our database as "context" to the LLM so it answers based on facts, not its own generic training data.
> 2. **Strict Prompt Engineering:** The system prompt forces the AI to reply with "I need more information" instead of guessing if it doesn't know the exact law. It is also required to cite its sources.
> 3. **Authoritative Fallback:** The user interface constantly displays the official **NALSA (National Legal Services Authority)** helpline (15100). If the user is unsure about the AI's answer, they are heavily encouraged to call the official human helpline, ensuring they always have access to a real lawyer.

**Q9: How does the system know the Gemini answer is "accurate" enough to save it into the database permanently?**
> **Answer:** In this prototype, the system relies on the strict boundaries we set via **Prompt Engineering and RAG**. Because we explicitly instruct Gemini to *only* answer using the provided database context and to say "I don't know" if unsure, we treat any successful, non-error text generation from the API as a valid cacheable response. 
> *Note for defense:* If they ask how to improve this for a real-world application, you can say: "For a production-ready application, we would add an 'Admin Approval Panel' or a 'Human-in-the-Loop' step, where a real lawyer quickly reviews and approves the AI's answer before it is permanently committed to the public database."
