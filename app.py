import os
import csv
import json
import gradio as gr
import google.generativeai as genai

# Ambil API Key dari ENV (bukan .env)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("❌ API key tidak ditemukan! Pastikan sudah diset di Hugging Face 'Repository secrets' dengan nama 'GEMINI_API_KEY'.")

# Konfigurasi Gemini
genai.configure(api_key=api_key)
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# Fungsi: Cari jawaban dari data.json
def cari_jawaban(pertanyaan_user):
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return "❌ Gagal membaca data.json: " + str(e)

    pertanyaan_user = pertanyaan_user.lower()
    for item in data.get("faq", []):
        if item["question"].lower() in pertanyaan_user:
            return item["answer"]
    return "Maaf, saya belum menemukan jawaban yang sesuai. Silakan tanyakan dengan kata lain."

# Fungsi: Minta jawaban dari Gemini
def generate_response(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Terjadi kesalahan dari Gemini: {e}"

# Fungsi: Simpan data ke leads.csv
def simpan_lead(nama, email, pertanyaan):
    try:
        with open("leads.csv", "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([nama, email, pertanyaan])
    except:
        pass  # Jika gagal, diabaikan supaya tidak ganggu chatbot

# Fungsi utama untuk Gradio
def chatbot_full(nama, email, pertanyaan):
    simpan_lead(nama, email, pertanyaan)
    jawaban = cari_jawaban(pertanyaan)
    if "Maaf" in jawaban:
        jawaban = generate_response(pertanyaan)
    return jawaban

# Launch Gradio
with gr.Blocks() as demo:
    gr.Markdown("## 💬 Leadgen Chatbot")
    with gr.Row():
        nama = gr.Textbox(label="Nama")
        email = gr.Textbox(label="Email")
    pertanyaan = gr.Textbox(label="Pertanyaan")
    jawaban = gr.Textbox(label="Jawaban")
    btn = gr.Button("Submit")
    btn.click(fn=chatbot_full, inputs=[nama, email, pertanyaan], outputs=jawaban)

demo.launch()
