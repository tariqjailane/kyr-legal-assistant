try:
    print("Attempting to import transformers...")
    import transformers
    print(f"Transformers version: {transformers.__version__}")
    
    print("Attempting to import AutoModel...")
    from transformers import AutoModel, AutoTokenizer
    print("AutoModel imported successfully.")
    
    print("Attempting to load model...")
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    print("Model loaded successfully.")
    
except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()
