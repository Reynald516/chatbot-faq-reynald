import json
import os
import csv
import random
from difflib import SequenceMatcher
from rapidfuzz import fuzz, process
import gradio as gr
import spacy
import sqlite3
import setup_database
from huggingface_hub import InferenceClient
from datetime import datetime

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except (OSError, IOError):
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

# Buat client HuggingFace dengan model LLaMA 3
client = InferenceClient(model="meta-llama/Meta-Llama-3-8B-Instruct")

# Load intent & data
with open("intents.json", "r", encoding="utf-8") as f:
    intents = json.load(f)

with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def get_response(user_input):
    user_input_lower = user_input.lower()


    # 1. Cek intents.json
    for intent in intents["intents"]:
        for pattern in intent["patterns"]:
            if pattern.lower() in user_input_lower:
                return random.choice(intent["responses"])

    # 2. Cek data.json
    for key in data:
        if key.lower() in user_input_lower:
            return data[key]

    # 3. Cek niat memesan → Simpan leads
    if "pesan" in user_input_lower or "order" in user_input_lower or "beli" in user_input_lower:
        return "Boleh minta nomor WhatsApp Anda agar tim kami bisa bantu lebih lanjut?"

    # 4. Fallback + Simpan ke unknown_questions.csv
    save_unknown_question(user_input)
    return "Maaf, saya belum memahami pertanyaan Anda. Pertanyaan ini akan kami simpan untuk pengembangan ke depannya."

def save_unknown_question(question):
    with open("unknown_questions.csv", "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([question, str(datetime.now())])

def save_leads(name, contact):
    with open("leads.csv", "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([name, contact, str(datetime.datetime.now())])
    return "Terima kasih! Kontak Anda telah kami simpan dan akan segera dihubungi oleh tim kami."

def lihat_data_csv():
    with open("leads.csv", "r", encoding="utf-8")as f:
        print("=== ISI leads.csv ===")
        print(f.read())

print("=====================")

lihat_data_csv()

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

# Fungsi untuk load intents dari file intents.json
def load_intents_data():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "intents.json")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["intents"]
    except Exception as e:
        raise RuntimeError(f"❌ Gagal memuat intents: {e}")

intents_data = load_intents_data()

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

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Fungsi untuk memprediksi intent dari pesan
def prediksi_intent(pesan, intents_data):
    pesan = pesan.lower()
    best_score = 0
    best_intent = None
    for intent in intents_data:
        for pattern in intent["patterns"]:
            score = similar(pesan, pattern)
            if score > best_score:
                best_score = score
                best_intent = intent["tag"]
    if best_score > 0.7:
        return best_intent
    return None

# Simpan pertanyaan baru ke leads.csv
def simpan_leads(nama, email, pertanyaan, entitas):
    if pertanyaan_sudah_ada(pertanyaan):
        print("✅ Pertanyaan sudah ada di leads, tidak disimpan ulang.")
        return # skip penyimpanan

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entitas_str = ", ".join([f"{text}({label})"for text, label in entitas])
        
    with open("leads.csv", mode="a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([nama, email, pertanyaan, timestamp, entitas_str, "belum dijawab"])
        print("✅ Pertanyaan baru disimpan ke leads.")

# Deteksi entitas penting dari pesan
def deteksi_entitas(pesan):
    doc = nlp(pesan)
    entitas = [(ent.text, ent.label_) for ent in doc.ents]
    return entitas

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


def simpan_pertanyaan(pertanyaan):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pertanyaan_baru (pertanyaan) VALUES (?)
    ''', (pertanyaan,))
    conn.commit()
    conn.close()

def load_intents_by_toko(nama_toko):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        defaul_path = os.path.join(base_dir, "intents.json")
        with open(defaul_path, "r", encoding="utf-8")as f:
            defaul_intents = json.load(f)["intents"]

        toko_path = os.path.join(base_dir, "data", f"{nama_toko}.json")
        if os.path.exists(toko_path):
            with open(toko_path, "r", encoding="utf-8") as f:
                toko_intents = json.load(f)["intents"]
        else:
            toko_intents = []
            
        semua_intents = defaul_intents + toko_intents
        return semua_intents
        
    except Exception as e:
        print(f" Gagal memuat intents untuk toko{nama_toko}:{e}")
        return []


# Fallback messages yang lebih manusiawi dan elegan
fallback_messages = [
    "Terima kasih sudah menghubungi Reynald Intelligence! Pertanyaan Anda sangat penting bagi kami. Kami akan segera membantu Anda dengan lebih detail. Sementara itu, apakah ada hal lain yang ingin Anda tanyakan?",
    "Kami senang Anda menghubungi Reynald Fashion. Sepertinya kami perlu beberapa saat untuk menemukan jawaban yang tepat. Apakah Anda ingin admin kami membantu lebih lanjut?",
    "Maaf, kami belum memiliki jawaban yang tepat. Tapi kami sangat menghargai pertanyaan Anda dan akan segera menghubungi Anda kembali.",
    "Pertanyaan Anda sungguh menarik! Saat ini admin kami sedang memeriksa jawaban terbaik untuk Anda. Sabar sebentar ya 😊"
]
    

# Fungsi utama chatbot
def respond(message, history, system_message, max_tokens, temperature, top_p, nama, email, toko, fallback_message="Apakah Anda ingin dibantu admin kami secara langsung? 😊 "):
    entitas_terdeteksi = deteksi_entitas(message)
    print("🔍 Entitas terdeteksi:", entitas_terdeteksi)
    
    # Cek apakah pertanyaan mirip dengan FAQ
    jawaban = cari_jawaban_terdekat(message, faq_data)

     # Cek intents data dinamis pilihan toko
    intents_data = load_intents_by_toko(toko)
    
    # Cek intent user
    intent_didapat = prediksi_intent(message, intents_data)
    if intent_didapat:
        for intent in intents_data:
            if intent["tag"] == intent_didapat:
                response_intent = intent["responses"][0]  # Ambil salah satu response
                yield response_intent
                return


    if jawaban:
        yield jawaban
        return
    else:
        try:
            simpan_leads(nama, email, message, entitas_terdeteksi)

            simpan_pertanyaan(message)

            
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

        # Panggil model LLM dari Hugging Face
        response = ""
        try:
            msg = client.chat_completion(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            print("DEBUG msg:", msg)
            print("DEBUG type:", type(msg))
            
            response_text = msg.choices[0].message.content
            if response_text:
                response = response_text.strip()
                yield response
            else:
                save_unknown_question(message)
                yield fallback_message
                # Lanjutkan kalau formatnya benar
        except Exception as e:
            print(f"❌ Error API: {e}")
            save_unknown_question(message)
            yield "Maaf, terjadi kesalahan. Coba lagi nanti."

        # Tambahkan fallback jika response kosong
        if response is None or not response.strip():
            save_unknown_question(message)
            yield random.choice(fallback_messages)

# Gradio interface
demo = gr.ChatInterface(
    respond,
    additional_inputs=[
        gr.Textbox(label="Nama", value="Reynald"),
        gr.Textbox(label="Email", value="reynaldintelligence@gmail.com"),
        gr.Dropdown(label="Pilih Toko", choices=["reynald_fashion", "toko_sepatu"], value="reynald_fashion"),
        gr.Textbox(
            value="Kamu adalah chatbot butik fashion cewek bernama Reynald Fashion. Gaya bicaramu sopan, ramah, hangat, dan modis seperti beauty advisor di butik high class. Jawabanmu harus membantu, meyakinkan, dan tetap elegan.",
            label="System message"
        ),
        gr.Slider(1, 2048, value=512, step=1, label="Max new tokens"),
        gr.Slider(0.1, 4.0, value=0.7, step=0.1, label="Temperature"),
        gr.Slider(0.1, 1.0, value=0.95, step=0.05, label="Top-p"),
    ],
    title="💬 Reynald Chatbot",
    description="Tanyakan apa pun tentang toko anda dengan bantuan Reynald intelligence. Kami siap membantu Anda dengan pelayanan terbaik.",
)

if __name__ == "__main__":
    demo.launch()
