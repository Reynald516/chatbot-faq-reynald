import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load API Key dari .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Konfigurasi Gemini
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-pro")

# Uji tanya jawab
prompt = "Apa itu chatbot AI dan bagaimana cara kerjanya?"
response = model.generate_content(prompt)

print("Jawaban dari Gemini:")
print(response.text)
