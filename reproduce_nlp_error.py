import sys
import os

# Ensure we can import from local directory
sys.path.append(os.getcwd())

from nlp_engine import nlp_engine

print("Attempting to load models...")
try:
    nlp_engine.load_models()
    print("Models loaded successfully!")
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    # Also print full traceback
    import traceback
    traceback.print_exc()
