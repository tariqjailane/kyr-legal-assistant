import sys
print(f"Python version: {sys.version}")

try:
    import transformers
    print(f"Transformers version: {transformers.__version__}")
except ImportError as e:
    print(f"Transformers not installed: {e}")

try:
    from transformers import BertModel, AutoModel, AutoTokenizer
    print("Successfully imported BertModel, AutoModel, AutoTokenizer")
except Exception as e:
    print(f"Error importing modules from transformers: {e}")

try:
    import sentencepiece
    print(f"SentencePiece version: {sentencepiece.__version__}")
except ImportError:
    print("SentencePiece NOT installed")

try:
    import google.protobuf
    print(f"Protobuf version: {google.protobuf.__version__}")
except ImportError:
    print("Protobuf NOT installed")

print("Attempting to load tokenizer...")
try:
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print("Tokenizer loaded")
except Exception as e:
    print(f"Tokenizer load failed: {e}")

print("Attempting to load model...")
try:
    model = AutoModel.from_pretrained("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print("Model loaded")
except Exception as e:
    print(f"Model load failed: {e}")
