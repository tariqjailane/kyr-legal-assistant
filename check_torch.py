try:
    import torch
    print(f"Torch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
except ImportError as e:
    print(f"Torch import failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
