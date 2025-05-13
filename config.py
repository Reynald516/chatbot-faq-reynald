import os
from dotenv import load_dotenv

# Memuat variabel dari file .env ke dalam environment
load_dotenv()

# Mengambil nilai API key dari environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
