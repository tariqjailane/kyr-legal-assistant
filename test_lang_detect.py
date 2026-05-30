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

# Test Cases
tests = [
    ("मकान", "hi"),
    ("Rent", "en"),
    ("எப்ஐஆர்", "ta"),
    ("IPC Section 302", "en"),
    ("धारा 302 IPC", "hi"),
    ("12345", None),
    ("நில உரிமையாளர் issue", "ta")
]

for text, expected in tests:
    result = detect_language(text)
    print(f"'{text}' -> {result} (Expected: {expected}) - {'PASS' if result == expected else 'FAIL'}")
