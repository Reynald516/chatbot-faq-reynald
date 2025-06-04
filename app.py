import os
import csv
import json
import random
import spacy
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from spacy.cli import download
from rapidfuzz import fuzz, process
from flask import Flask, request, jsonify

# Inisialisasi Flask app
app = Flask(__name__)

# Load .env dan API key
load_dotenv()

# Ambil API Key dari ENV (bukan .env)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("❌ API key tidak ditemukan! Pastikan sudah diset di Hugging Face 'Repository secrets' dengan nama 'GEMINI_API_KEY'.")

# Konfigurasi Gemini
genai.configure(api_key=api_key)
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# Load NLP spaCy model
try:
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")
except (OSError, IOError):
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

#LOAD DATA
# Data FAQ yang bisa dijawab chatbot
with open("data.json", "r", encoding="utf-8") as f:
    data_main = json.load(f)

with open("intents.json", "r", encoding="utf-8") as f:
    default_intents_file = json.load(f)


# Fungsi untuk load FAQ dari file JSON
def load_faq_data():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "data.json")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["faq"]
    except Exception as e:
        raise RuntimeError(f"❌ Gagal memuat FAQ: {e}")

faq_data = load_faq_data()

# Fungsi load intents
def load_intents_by_toko(nama_toko=None):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_path = os.path.join(base_dir, "intents.json")

        # Load default intents (ini yang sama kayak load_intents_data)
        default_intents = []
        if os.path.exists(default_path):
            with open(default_path, "r", encoding="utf-8") as f:
                default_intents = json.load(f)["intents"]
                print(f"✅ Loaded default intents: {len(default_intents)}")
        else:
            print(f"⚠ File {default_path} tidak ditemukan.")

        # Load toko intents (opsional)
        toko_intents = []
        if nama_toko:
            toko_path = os.path.join(base_dir, "data", f"{nama_toko}.json")
            if os.path.exists(toko_path):
                with open(toko_path, "r", encoding="utf-8") as f:
                    toko_intents = json.load(f)["intents"]
                    print(f"✅ Loaded {nama_toko} intents: {len(toko_intents)}")
            else:
                print(f"⚠ File {toko_path} tidak ditemukan.")

        # Gabungkan default intents + toko intents
        semua_intents = default_intents + toko_intents
        print(f"📦 Total intents loaded: {len(semua_intents)}")
        return {"intents": semua_intents}

    except Exception as e:
        print(f"❌ Gagal memuat intents: {e}")
        return {"intents": []}

intents = load_intents_by_toko()

# INTENT & JAWABAN
# Untuk merespon input
def get_response(user_input, toko="reynald_fashion"):
    user_input_lower = user_input.lower()
    intents = load_intents_by_toko(toko)
    
    # 1. Cek intent dari intents utama + reynald_fashion
    for intent in intents["intents"]:
        for pattern in intent["patterns"]:
            if pattern.lower() in user_input_lower:
                return random.choice(intent["responses"])

                
    # 2. Cek data.json
    for key in data_main:
        if key.lower() in user_input_lower:
            return data_main[key]


    # 3. Cek niat memesan → Simpan leads
    if "pesan" in user_input_lower or "order" in user_input_lower or "beli" in user_input_lower:
        return "Boleh minta nomor WhatsApp Anda agar tim kami bisa bantu lebih lanjut?"

    # 4. Fallback + Simpan ke unknown_questions.csv
    save_unknown_question(user_input)
    return "Maaf, saya belum memahami pertanyaan Anda. Pertanyaan ini akan kami simpan untuk pengembangan ke depannya."

# Cek pattren dengan fuzzy seacrh
def prediksi_intent(pesan, intents_data):
    pesan = pesan.lower()
    best_score = 0
    best_intent = None

    for intent in intents_data["intents"]:
        for pattern in intent["patterns"]:
            pattern_lower = pattern.lower()
            score = fuzz.token_sort_ratio(pesan, pattern_lower)  # dari fuzzywuzzy
            
            if score > best_score:
                best_score = score
                best_intent = intent["tag"]

    if best_score >= 60:
        return best_intent
    return None

# Fungsi untuk mencari jawaban terdekat dari pertanyaan
def cari_jawaban_terdekat(message, faq_data):
    semua_pertanyaan = []
    mapping_pertanyaan_ke_jawaban = {}

    for item in faq_data:
        for q in item["question"]:
            semua_pertanyaan.append(q)
            mapping_pertanyaan_ke_jawaban[q] = item["answer"]

    hasil = process.extractOne(message, semua_pertanyaan, scorer=fuzz.token_sort_ratio)
    if hasil and hasil[1] >= 60:
        pertanyaan_mirip = hasil[0]
        return mapping_pertanyaan_ke_jawaban[pertanyaan_mirip]

    return None
# LEADS
# Simpan pertanyaan+email+nama+entitas baru ke leads.csv
def simpan_leads(nama, email, contact, pertanyaan, entitas_terdeteksi):
    if pertanyaan_sudah_ada(pertanyaan):
        print("✅ Pertanyaan sudah ada di leads, tidak disimpan ulang.")
        return # skip penyimpanan

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entitas_str = ", ".join([f"{text}({label})"for text, label in entitas_terdeteksi])
        
    with open("leads.csv", mode="a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([nama, contact, email, pertanyaan, timestamp, entitas_str])
        print("✅ Pertanyaan baru disimpan ke leads.")

# Cek apakah pertanyaan sudah ada di leads.csv
def pertanyaan_sudah_ada(pertanyaan):
    try:
        with open("leads.csv", mode="r", encoding="utf-8")as file:
            reader = csv.DictReader(file)
            for now in reader:
                if now["pertanyaan"].strip().lower() == pertanyaan.strip().lower():
                    return True
        return False
    except FileNotFoundError:
        return False

# pakai SpaCy untuk Deteksi entitas penting dari pesan misalnya nama, produk, tempat, dll.
def deteksi_entitas(pesan):
    doc = nlp(pesan)
    entitas = [(ent.text, ent.label_) for ent in doc.ents]
    return entitas

# FALLBACK & UNKNOWN
# menyimpan pertanyaan yang tidak dikenali ke leads.csv
def save_unknown_question(question):
    with open("unknown_questions.csv", mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), question])

# Fallback messages yang lebih manusiawi dan elegan
fallback_messages = [
    "Terima kasih sudah menghubungi Reynald Intelligence! Pertanyaan Anda sangat penting bagi kami. Kami akan segera membantu Anda dengan lebih detail. Sementara itu, apakah ada hal lain yang ingin Anda tanyakan?",
    "Kami senang Anda menghubungi Reynald Intelligence. Sepertinya kami perlu beberapa saat untuk menemukan jawaban yang tepat. Apakah Anda ingin admin kami membantu lebih lanjut?",
    "Maaf, kami belum memiliki jawaban yang tepat. Tapi kami sangat menghargai pertanyaan Anda dan akan segera menghubungi Anda kembali.",
    "Pertanyaan Anda sungguh menarik! Saat ini admin kami sedang memeriksa jawaban terbaik untuk Anda. Sabar sebentar ya 😊"
]
     
# MODEL
# Fungsi: Minta jawaban dari Gemini
def generate_response(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Terjadi kesalahan dari Gemini: {e}"
    

# Fungsi utama chatbot
def respond(message, history, system_message, max_tokens, temperature, top_p, nama, email, toko, fallback_message="Apakah Anda ingin dibantu admin kami secara langsung? 😊 "):
    entitas_terdeteksi = deteksi_entitas(message)
    print("🔍 Entitas terdeteksi:", entitas_terdeteksi)
    
    # Cek apakah pertanyaan mirip dengan FAQ
    jawaban = cari_jawaban_terdekat(message, faq_data)

     # Cek intents data dinamis pilihan toko
    intents_data = load_intents_by_toko(toko)
    print(f"🧠 Intents loaded: {len(intents_data['intents'])}")
    
    # Cek intent user
    intent_didapat = prediksi_intent(message, intents_data)
    print(f"🎯 Intent dikenali: {intent_didapat}")

    if intent_didapat and intents_data["intents"]:
        for intent in intents_data["intents"]:
            if intent["tag"] == intent_didapat:
                response_intent = intent["responses"][0]  # Ambil salah satu response
                yield response_intent
                return


    if jawaban:
        yield jawaban
        return
    else:
        try:
            simpan_leads(nama, email, contact="", pertanyaan=message, entitas_terdeteksi=entitas_terdeteksi)
            
        except Exception as e:
            print("Terjadi error saat menyimpan leads:", e)
            save_unknown_question(message)

        # Tambahkan entitas ke system_message
        if entitas_terdeteksi:
            entitas_str = ", ".join([f"{text}({label})" for text, label in entitas_terdeteksi])
            system_message += f"\nCatatan: User menyebut entitas berikut: {entitas_str}."

        # Siapkan pesan ke model
        messages = [{"role": "system", "content": system_message}]
        for user_msg, bot_msg in history:
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            if bot_msg:
                messages.append({"role": "assistant", "content": bot_msg})
        messages.append({"role": "user", "content": message})

       
        prompt_final = "\n".join([msg["content"] for msg in messages])
        response_text = generate_response(prompt_final)
        yield response_text

        if response_text.startswith("Terjadi kesalahan dari Gemini:"):
            response_text = random.choice(fallback_messages)

        yield response_text
        return
 
 # === ✅ WEBHOOK ENDPOINT ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        pesan = data.get("message", "")
        pengirim = data.get("from", "anon")
        print(f"📩 Pesan dari {pengirim}: {pesan}")

        response_gen = respond(
            message=pesan,
            history=[],
            system_message="Kamu adalah asisten toko profesional.",
            max_tokens=512,
            temperature=0.7,
            top_p=0.95,
            nama=pengirim,
            email="anon@example.com",
            toko="reynald_fashion"
        )
        
        jawaban = next(response_gen)
        return jsonify({"reply": jawaban})

    except Exception as e:
        print("❌ ERROR di webhook:", e)
        return jsonify({"error": str(e)}), 500

# === ✅ JALANKAN APP ===
if __name__ == "_main_":
    app.run(host='0.0.0.0', port=7860)