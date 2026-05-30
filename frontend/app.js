console.log("🚀 KYR Frontend Version 1.0.8 Loaded");
const chatbox = document.getElementById('chatbox');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const settingsBtn = document.getElementById('settingsBtn');
const settingsPanel = document.getElementById('settingsPanel');
const langSelect = document.getElementById('langSelect');
const aiToggle = document.getElementById('aiToggle');
const clearChatBtn = document.getElementById('clearChatBtn');

// Auth DOM Elements
const mainHeader = document.getElementById('mainHeader');
const mainFooter = document.getElementById('mainFooter');
const loginScreen = document.getElementById('loginScreen');
const identifierPanel = document.getElementById('identifierPanel');
const otpPanel = document.getElementById('otpPanel');
const loginIdentifier = document.getElementById('loginIdentifier');
const sendOtpBtn = document.getElementById('sendOtpBtn');
const verifyOtpBtn = document.getElementById('verifyOtpBtn');
const resendOtpBtn = document.getElementById('resendOtpBtn');
const loginError = document.getElementById('loginError');
const errorMessage = document.getElementById('errorMessage');
const logoutBtn = document.getElementById('logoutBtn');
const mockToast = document.getElementById('mockToast');
const mockToastOtp = document.getElementById('mockToastOtp');
const closeToastBtn = document.getElementById('closeToastBtn');
const otpBoxes = Array.from({ length: 6 }, (_, i) => document.getElementById(`otp-${i + 1}`));

// Translation DOM Elements & Catalog
const headerTitle = document.getElementById('headerTitle');
const headerStatus = document.getElementById('headerStatus');
const welcomeMessage = document.getElementById('welcomeMessage');
const langLabel = document.getElementById('langLabel');
const aiLabel = document.getElementById('aiLabel');

const UI_TRANSLATIONS = {
    'en': {
        'welcome': 'Hi! I am your KYR Legal Assistant.<br>Ask me about your rights (e.g., Arrest, FIR, or even Ragging in college!).',
        'title': 'Legal Assistant',
        'status': 'Online • KYR AI',
        'placeholder': 'Type a message...',
        'langLabel': 'Language:',
        'aiLabel': 'AI Priority Mode:',
        'clearChat': '<i class="fa-solid fa-trash"></i> Clear Chat',
        'logout': '<i class="fa-solid fa-right-from-bracket"></i> Logout'
    },
    'hi': {
        'welcome': 'नमस्ते! मैं आपका KYR कानूनी सहायक हूँ।<br>मुझसे अपने अधिकारों के बारे में पूछें (जैसे, गिरफ्तारी, प्राथमिकी (FIR), या कॉलेज में रैगिंग!)।',
        'title': 'कानूनी सहायक',
        'status': 'ऑनलाइन • KYR AI',
        'placeholder': 'संदेश लिखें...',
        'langLabel': 'भाषा:',
        'aiLabel': 'एआई प्राथमिकता मोड:',
        'clearChat': '<i class="fa-solid fa-trash"></i> चैट साफ़ करें',
        'logout': '<i class="fa-solid fa-right-from-bracket"></i> लॉगआउट'
    },
    'ta': {
        'welcome': 'வணக்கம்! நான் உங்கள் KYR சட்ட உதவியாளர்.<br>உங்கள் உரிமைகள் பற்றி என்னிடம் கேளுங்கள் (எ.கா., கைது, முதல் தகவல் அறிக்கை (FIR), அல்லது கல்லூரியில் ரேகிங்!).',
        'title': 'சட்ட உதவியாளர்',
        'status': 'ஆன்லைன் • KYR AI',
        'placeholder': 'செய்தியை தட்டச்சு செய்க...',
        'langLabel': 'மொழி:',
        'aiLabel': 'AI முன்னுரிமை முறை:',
        'clearChat': '<i class="fa-solid fa-trash"></i> அரட்டையை அழி',
        'logout': '<i class="fa-solid fa-right-from-bracket"></i> வெளியேறு'
    }
};

function updateLanguage(lang) {
    const t = UI_TRANSLATIONS[lang] || UI_TRANSLATIONS['en'];
    if (headerTitle) headerTitle.innerText = t.title;
    if (headerStatus) headerStatus.innerText = t.status;
    if (welcomeMessage) welcomeMessage.innerHTML = t.welcome;
    if (langLabel) langLabel.innerText = t.langLabel;
    if (aiLabel) aiLabel.innerText = t.aiLabel;
    if (chatInput) chatInput.placeholder = t.placeholder;
    if (clearChatBtn) clearChatBtn.innerHTML = t.clearChat;
    if (logoutBtn) logoutBtn.innerHTML = t.logout;
}

let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let audioUnlocked = false;

// Auth State
let currentIdentifier = '';
let sessionToken = localStorage.getItem('kyr_session_token') || '';

// Manage authentication views
function checkAuth() {
    sessionToken = localStorage.getItem('kyr_session_token') || '';
    updateLanguage(langSelect.value);
    if (sessionToken) {
        loginScreen.classList.add('hidden');
        mainHeader.classList.remove('hidden');
        chatbox.classList.remove('hidden');
        mainFooter.classList.remove('hidden');
        scrollToBottom();
    } else {
        loginScreen.classList.remove('hidden');
        mainHeader.classList.add('hidden');
        chatbox.classList.add('hidden');
        mainFooter.classList.add('hidden');
        
        // Reset login states
        identifierPanel.classList.remove('hidden');
        otpPanel.classList.add('hidden');
        loginError.classList.add('hidden');
        loginIdentifier.value = '';
        otpBoxes.forEach(box => box.value = '');
    }
}

// Check auth on load
window.addEventListener('DOMContentLoaded', checkAuth);

// Unlock audio engine on first user interaction so async TTS works
function unlockAudio() {
    if (!audioUnlocked && window.speechSynthesis) {
        const u = new SpeechSynthesisUtterance('');
        u.volume = 0;
        window.speechSynthesis.speak(u);
        audioUnlocked = true;
    }
}

// API endpoints (relative paths work on server, fall back to localhost for file:// testing)
const API_BASE = window.location.protocol === 'file:' ? 'http://127.0.0.1:8001/api' : '/api';

// Markdown simple parser for bold text (Law citations)
function parseMarkdown(text) {
    let parsed = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    parsed = parsed.replace(/\n/g, '<br>');
    return parsed;
}

// Add message to chat UI
function appendMessage(role, content, meta = {}) {
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${role}`;

    let msgHtml = `<div class="message"><p>${parseMarkdown(content)}</p>`;
    
    if (meta.citation && !meta.citation.includes('Generated by')) {
        msgHtml += `<p style="margin-top:8px; font-size: 13px;"><strong>📜 Law:</strong> ${meta.citation}</p>`;
    }
    if (meta.case_study) {
        msgHtml += `<p style="margin-top:8px; font-size: 13px;"><strong>🧑‍⚖️ Case:</strong> ${meta.case_study}</p>`;
    }
    
    msgHtml += `</div>`;
    
    // Add meta actions for bot
    if (role === 'bot') {
        let actionsHtml = `<div class="msg-actions">`;
        actionsHtml += `<button class="tts-btn" onclick="playTTS(this, '${encodeURIComponent(content)}', '${meta.lang || langSelect.value}')"><i class="fa-solid fa-volume-high"></i></button>`;
        if (meta.source && meta.source.includes('DB')) {
            actionsHtml += `<button class="more-info-btn" onclick="forceAI(this)"><i class="fa-solid fa-wand-magic-sparkles"></i> Get more info</button>`;
        }
        actionsHtml += `</div>`;
        if (meta.metrics) {
            actionsHtml += `<div class="meta-info">${meta.metrics}</div>`;
        }
        msgHtml += actionsHtml;
    }

    wrapper.innerHTML = msgHtml;
    chatbox.appendChild(wrapper);
    scrollToBottom();
    
    // Automatically play TTS if it's a bot message
    if (role === 'bot') {
        const ttsBtn = wrapper.querySelector('.tts-btn');
        if (ttsBtn) {
            // Directly call playTTS rather than simulating a click
            playTTS(ttsBtn, encodeURIComponent(content), meta.lang || langSelect.value);
        }
    }
}

function showTyping() {
    const wrapper = document.createElement('div');
    wrapper.id = 'typingIndicator';
    wrapper.className = 'message-wrapper bot';
    wrapper.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    chatbox.appendChild(wrapper);
    scrollToBottom();
}

function removeTyping() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

function scrollToBottom() {
    chatbox.scrollTop = chatbox.scrollHeight;
}

// Handle sending text message
async function sendMessage(text, forceAI = false) {
    if (!text.trim()) return;

    if (!forceAI) { // Don't append user message again if it's a "force AI" request
        appendMessage('user', text);
    }
    chatInput.value = '';
    showTyping();

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionToken}`
            },
            body: JSON.stringify({
                query: text,
                lang: langSelect.value,
                use_ai_prioritized: aiToggle.checked || forceAI
            })
        });

        if (response.status === 401) {
            localStorage.removeItem('kyr_session_token');
            checkAuth();
            return;
        }

        const data = await response.json();
        removeTyping();
        appendMessage('bot', data.answer_text, data);
        
        // Auto-update UI language if changed by backend
        if (data.lang && data.lang !== langSelect.value) {
            langSelect.value = data.lang;
            updateLanguage(data.lang);
        }

    } catch (err) {
        removeTyping();
        appendMessage('bot', 'Error connecting to server. Please try again.');
        console.error(err);
    }
}

// "Get more info" button logic
window.forceAI = function(btn) {
    // Find the last user message before this bot message
    const wrapper = btn.closest('.message-wrapper');
    let prev = wrapper.previousElementSibling;
    while (prev) {
        if (prev.classList.contains('user')) {
            const text = prev.querySelector('.message p').innerText.replace('🎤 ', '');
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Asking AI...';
            btn.disabled = true;
            sendMessage(text, true);
            break;
        }
        prev = prev.previousElementSibling;
    }
}

// TTS logic (Hybrid Play/Stop toggle)
window.stopTTS = function() {
    if (window.currentAudio) {
        window.currentAudio.pause();
        window.currentAudio = null;
    }
    if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
    }
    if (window.currentTTSBtn) {
        window.currentTTSBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
        window.currentTTSBtn.disabled = false;
        window.currentTTSBtn = null;
    }
};

window.playTTS = async function(btn, content, lang) {
    const text = decodeURIComponent(content);
    
    // If the clicked button is already playing, stop it and return
    if (window.currentTTSBtn === btn) {
        window.stopTTS();
        return;
    }
    
    // If another button is playing, stop it first
    if (window.currentTTSBtn) {
        window.stopTTS();
    }
    
    window.currentTTSBtn = btn;
    const originalHtml = '<i class="fa-solid fa-volume-high"></i>'; // standard play icon
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="color: var(--accent-color);"></i>';
    
    const isTamil = lang.startsWith('ta');
    if (!isTamil) {
        // Native Speech Synthesis (instant)
        btn.innerHTML = '<i class="fa-solid fa-circle-stop" style="color: var(--accent-color);"></i>';
        const utterance = new SpeechSynthesisUtterance(text.replace(/[*#_~`>]/g, ''));
        if (lang.startsWith('hi')) {
            utterance.lang = 'hi-IN';
        } else {
            utterance.lang = 'en-IN';
        }
        
        utterance.onend = () => {
            if (window.currentTTSBtn === btn) {
                btn.innerHTML = originalHtml;
                window.currentTTSBtn = null;
            }
        };
        utterance.onerror = () => {
            if (window.currentTTSBtn === btn) {
                btn.innerHTML = originalHtml;
                window.currentTTSBtn = null;
            }
        };
        
        window.speechSynthesis.speak(utterance);
        return;
    }
    
    // Tamil gTTS from Backend
    try {
        const response = await fetch(`${API_BASE}/tts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionToken}`
            },
            body: JSON.stringify({ text, lang })
        });
        
        if (!response.ok) throw new Error('gTTS backend failed');
        
        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        
        // Safety check: if user clicked stop while we were fetching, don't play
        if (window.currentTTSBtn !== btn) return;
        
        const audio = new Audio(audioUrl);
        window.currentAudio = audio;
        
        btn.innerHTML = '<i class="fa-solid fa-circle-stop" style="color: var(--accent-color);"></i>';
        btn.disabled = false;
        
        audio.onended = () => {
            if (window.currentTTSBtn === btn) {
                btn.innerHTML = originalHtml;
                window.currentTTSBtn = null;
            }
        };
        audio.onerror = () => {
            if (window.currentTTSBtn === btn) {
                btn.innerHTML = originalHtml;
                window.currentTTSBtn = null;
            }
        };
        
        await audio.play();
    } catch (err) {
        console.warn("gTTS failed, falling back to native Tamil SpeechSynthesis:", err);
        
        if (window.currentTTSBtn !== btn) return;
        
        btn.innerHTML = '<i class="fa-solid fa-circle-stop" style="color: var(--accent-color);"></i>';
        btn.disabled = false;
        const utterance = new SpeechSynthesisUtterance(text.replace(/[*#_~`>]/g, ''));
        utterance.lang = 'ta-IN';
        
        utterance.onend = () => {
            if (window.currentTTSBtn === btn) {
                btn.innerHTML = originalHtml;
                window.currentTTSBtn = null;
            }
        };
        utterance.onerror = () => {
            if (window.currentTTSBtn === btn) {
                btn.innerHTML = originalHtml;
                window.currentTTSBtn = null;
            }
        };
        
        window.speechSynthesis.speak(utterance);
    }
}

// Event Listeners
sendBtn.addEventListener('click', () => {
    unlockAudio();
    sendMessage(chatInput.value);
});
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        unlockAudio();
        sendMessage(chatInput.value);
    }
});

// Language Selection Change
langSelect.addEventListener('change', () => {
    updateLanguage(langSelect.value);
});

// Settings Toggle
settingsBtn.addEventListener('click', () => {
    settingsPanel.classList.toggle('hidden');
});
clearChatBtn.addEventListener('click', () => {
    window.stopTTS();
    chatbox.innerHTML = '';
    settingsPanel.classList.add('hidden');
});

// Voice Input Logic (MediaRecorder)
micBtn.addEventListener('click', async () => {
    unlockAudio();
    if (isRecording) {
        // Stop recording
        mediaRecorder.stop();
        micBtn.classList.remove('recording');
        isRecording = false;
    } else {
        // Start recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = e => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const webmBlob = new Blob(audioChunks, { type: 'audio/webm' });
                stream.getTracks().forEach(track => track.stop());
                
                showTyping();
                
                try {
                    // Convert WebM to WAV so backend soundfile/speech_recognition can read it
                    const wavBlob = await encodeAudioToWav(webmBlob);
                    
                    const formData = new FormData();
                    formData.append('audio', wavBlob, 'recording.wav');
                    formData.append('lang', langSelect.value);

                    const response = await fetch(`${API_BASE}/transcribe`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${sessionToken}`
                        },
                        body: formData
                    });

                    if (response.status === 401) {
                        localStorage.removeItem('kyr_session_token');
                        checkAuth();
                        return;
                    }

                    const data = await response.json();
                    removeTyping();
                    
                    if (data.text) {
                        appendMessage('user', `🎤 ${data.text}`);
                        if (data.lang && data.lang !== langSelect.value) {
                            langSelect.value = data.lang;
                            updateLanguage(data.lang);
                        }
                        // Now send the transcribed text to chat
                        sendMessage(data.text);
                    } else {
                        appendMessage('system', `Error: ${data.error || 'Could not transcribe'}`);
                    }
                } catch (err) {
                    removeTyping();
                    appendMessage('system', 'Error processing audio or connecting to transcription service.');
                    console.error(err);
                }
            };

            mediaRecorder.start();
            micBtn.classList.add('recording');
            isRecording = true;
        } catch (err) {
            console.error("Microphone access denied", err);
            alert("Microphone access is required for voice input.");
        }
    }
});

// Helper function to encode AudioBuffer to WAV format
async function encodeAudioToWav(audioBlob) {
    const arrayBuffer = await audioBlob.arrayBuffer();
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    
    const numOfChan = audioBuffer.numberOfChannels,
        length = audioBuffer.length * numOfChan * 2 + 44,
        buffer = new ArrayBuffer(length),
        view = new DataView(buffer),
        channels = [],
        sampleRate = audioBuffer.sampleRate;
    let offset = 0,
        pos = 0;
        
    setUint32(0x46464952);                         // "RIFF"
    setUint32(length - 8);                         // file length - 8
    setUint32(0x45564157);                         // "WAVE"
    setUint32(0x20746d66);                         // "fmt " chunk
    setUint32(16);                                 // length = 16
    setUint16(1);                                  // PCM (uncompressed)
    setUint16(numOfChan);
    setUint32(sampleRate);
    setUint32(sampleRate * 2 * numOfChan);         // avg. bytes/sec
    setUint16(numOfChan * 2);                      // block-align
    setUint16(16);                                 // 16-bit
    setUint32(0x61746164);                         // "data" - chunk
    setUint32(length - pos - 4);                   // chunk length

    for(let i = 0; i < audioBuffer.numberOfChannels; i++)
        channels.push(audioBuffer.getChannelData(i));
        
    while(pos < length) {
        for(let i = 0; i < numOfChan; i++) {
            let sample = Math.max(-1, Math.min(1, channels[i][offset])); 
            sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767)|0; 
            view.setInt16(pos, sample, true);          
            pos += 2;
        }
        offset++;                                     
    }
    
    return new Blob([buffer], {type: "audio/wav"});

    function setUint16(data) {
        view.setUint16(pos, data, true);
        pos += 2;
    }
    function setUint32(data) {
        view.setUint32(pos, data, true);
        pos += 4;
    }
}

// --- OTP / Authentication Logic ---

// OTP Input Grid Navigation
otpBoxes.forEach((box, index) => {
    box.addEventListener('input', (e) => {
        const val = e.target.value;
        if (val.length > 1) {
            e.target.value = val.charAt(val.length - 1);
        }
        if (e.target.value.length === 1 && index < 5) {
            otpBoxes[index + 1].focus();
        }
    });

    box.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && !e.target.value && index > 0) {
            otpBoxes[index - 1].focus();
        }
        if (e.key === 'Enter') {
            verifyOtpBtn.click();
        }
    });
});

// Resend OTP functionality
resendOtpBtn.addEventListener('click', () => {
    if (resendOtpBtn.classList.contains('disabled')) return;
    
    // Simulate disable for 30s
    resendOtpBtn.classList.add('disabled');
    let timer = 30;
    resendOtpBtn.innerText = `Resend in ${timer}s`;
    
    const interval = setInterval(() => {
        timer--;
        if (timer <= 0) {
            clearInterval(interval);
            resendOtpBtn.classList.remove('disabled');
            resendOtpBtn.innerText = 'Resend OTP';
        } else {
            resendOtpBtn.innerText = `Resend in ${timer}s`;
        }
    }, 1000);

    // Call send OTP
    requestOTP(currentIdentifier);
});

// Function to trigger OTP request
async function requestOTP(identifier) {
    loginError.classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/auth/send-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier })
        });
        
        const data = await response.ok ? await response.json() : null;
        
        if (!data || !response.ok) {
            const errData = data || await response.json();
            showLoginError(errData.detail || "Failed to send OTP. Please try again.");
            return;
        }

        // OTP sent successfully!
        currentIdentifier = identifier;
        
        // Show panel transitions
        identifierPanel.classList.add('hidden');
        otpPanel.classList.remove('hidden');
        
        const isEmail = identifier.includes('@');
        console.log("🔍 Checking identifier:", identifier, "| isEmail:", isEmail);
        if (isEmail) {
            document.getElementById('loginCardSubtitle').innerText = `Enter code sent to email: ${identifier}`;
            hideMockToast();
        } else {
            document.getElementById('loginCardSubtitle').innerText = `Enter code sent to WhatsApp: ${identifier}`;
            // Trigger WhatsApp status notification toast for phone numbers (does not leak OTP)
            showMockToast();
        }
        
        // Focus first box
        setTimeout(() => otpBoxes[0].focus(), 100);
        
    } catch (err) {
        showLoginError("Error connecting to server. Is it running?");
        console.error(err);
    }
}

// Show error banner
function showLoginError(msg) {
    errorMessage.innerText = msg;
    loginError.classList.remove('hidden');
}

// Show Toast (Generic status message, does not reveal the OTP)
let toastTimeout;
function showMockToast() {
    clearTimeout(toastTimeout);
    if (mockToastOtp) mockToastOtp.innerText = "";
    const bodyText = mockToast.querySelector('.mock-toast-body');
    if (bodyText) {
        bodyText.innerHTML = "A verification code has been sent to your WhatsApp number.";
    }
    mockToast.classList.remove('hidden');
    
    // Slide down toast, then close after 8s
    toastTimeout = setTimeout(() => {
        hideMockToast();
    }, 8000);
}

function hideMockToast() {
    mockToast.classList.add('hidden');
}

closeToastBtn.addEventListener('click', hideMockToast);

// Send OTP Button click
sendOtpBtn.addEventListener('click', () => {
    const val = loginIdentifier.value.trim();
    if (!val) {
        showLoginError("Please enter an email or phone number.");
        return;
    }
    requestOTP(val);
});

// Support Enter key on email/phone input
loginIdentifier.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendOtpBtn.click();
    }
});

// Verify OTP Button click
verifyOtpBtn.addEventListener('click', async () => {
    loginError.classList.add('hidden');
    
    const otp = otpBoxes.map(box => box.value.trim()).join('');
    if (otp.length < 6) {
        showLoginError("Please enter a full 6-digit OTP code.");
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/auth/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                identifier: currentIdentifier,
                otp: otp
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showLoginError(data.detail || "Incorrect OTP. Please try again.");
            // Highlight boxes
            otpBoxes.forEach(box => {
                box.style.borderColor = 'var(--danger)';
                setTimeout(() => box.style.borderColor = '', 1000);
            });
            return;
        }
        
        // Token received!
        localStorage.setItem('kyr_session_token', data.token);
        
        // Hide toast immediately
        hideMockToast();
        
        // Check auth to show chat
        checkAuth();
        
    } catch (err) {
        showLoginError("Verification failed due to connection error.");
        console.error(err);
    }
});

// Logout Button click
logoutBtn.addEventListener('click', () => {
    window.stopTTS();
    localStorage.removeItem('kyr_session_token');
    settingsPanel.classList.add('hidden');
    checkAuth();
});

