title: Reynald Chatbot
emoji: 💬
colorFrom: yellow
colorTo: purple
sdk: gradio
sdk_version: 5.31.0
app_file: app.py
pinned: false
license: mit
Reynald Chatbot 💬
An example chatbot using Gradio, huggingface_hub, and the Hugging Face Inference API.

Description
This project is a chatbot application built using Gradio for the user interface and Hugging Face's Inference API to generate responses based on user inputs. It integrates FAQ data from a data.json file and leads from a leads.csv file to further personalize the chatbot's behavior.

Features
FAQ-based Response: The chatbot first checks if the user's question matches any existing FAQ and provides an answer from data.json.
Hugging Face Integration: If the question is not found in the FAQ, the chatbot uses Hugging Face's Inference API to generate a response.
Interactive Chat Interface: The Gradio interface provides a user-friendly way to interact with the chatbot, adjusting parameters like the response length (max_tokens), creativity (temperature), and more.
Setup Instructions
Clone or download this repository.
Install dependencies:
pip install -r requirements.txt
Reynald Chatbot 💬
An example chatbot using Gradio, huggingface_hub, and the Hugging Face Inference API.

Description
This project is a chatbot application built using Gradio for the user interface and Hugging Face's Inference API to generate responses based on user inputs. It integrates FAQ data from a data.json file and leads from a leads.csv file to further personalize the chatbot's behavior.

Features
FAQ-based Response: The chatbot first checks if the user's question matches any existing FAQ and provides an answer from data.json.
Hugging Face Integration: If the question is not found in the FAQ, the chatbot uses Hugging Face's Inference API to generate a response.
Interactive Chat Interface: The Gradio interface provides a user-friendly way to interact with the chatbot, adjusting parameters like the response length (max_tokens), creativity (temperature), and more.
Setup Instructions
Clone or download this repository.
Install dependencies:
pip install -r requirements.txt
