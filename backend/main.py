import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import google.generativeai as genai
from pymongo import MongoClient
import nltk
from transformers import BertTokenizer, BertModel
import torch
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")
genai.configure(api_key=gemini_api_key)

mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    raise ValueError("MONGODB_URI not found in .env file")
client = MongoClient(mongo_uri)
db = client.get_database("chatbot_db")

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

app = Flask(__name__, static_folder='../static', template_folder='../static')

nltk.download('punkt')

def generate_and_store_fact(user_message, bot_response):
    if "my name is" in user_message.lower():
        return

    try:
        # Create a prompt to generate a summarized fact
        prompt = f"""Summarize the following user interaction into a one-line fact from the user's perspective.
        For example: 'The user expressed interest in dogs.' or 'The user asked for their name.'

        User message: "{user_message}"
        Bot response: "{bot_response}"

        Fact:"""

        # Generate the fact using the generative model
        model_gemini = genai.GenerativeModel('gemini-pro')
        response = model_gemini.generate_content(prompt)
        summarized_fact = response.text.strip()

        # Store the summarized fact in the database
        if summarized_fact:
            db.facts.insert_one({'fact': summarized_fact})
            print(f"Stored fact: {summarized_fact}")

    except Exception as e:
        print(f"Error generating or storing fact: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    print(f"Received user message: {user_message}")
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    if "my name is" in user_message.lower():
        try:
            name = user_message.lower().split("my name is")[1].strip().split()[0]
            db.facts.insert_one({'fact': f"The user's name is {name}."})
        except IndexError:
            pass

    user_facts_cursor = db.facts.find({})
    user_facts = [fact['fact'] for fact in user_facts_cursor]
    
    context = ""
    if user_facts:
        # Get embeddings
        message_embedding = model(**tokenizer(user_message, return_tensors='pt'))[0].mean(1)
        fact_embeddings = [model(**tokenizer(fact, return_tensors='pt'))[0].mean(1) for fact in user_facts]
        
        # Calculate similarities
        similarities = [cosine_similarity(message_embedding.detach().numpy(), fact_embedding.detach().numpy())[0][0] for fact_embedding in fact_embeddings]
        
        # Find the most relevant fact
        if similarities and max(similarities) > 0.7:
            most_relevant_fact = user_facts[similarities.index(max(similarities))]
            context = f"The user has previously mentioned: {most_relevant_fact}"

    prompt = f"User message: \"{user_message}\"\n\n{context}\n\nRespond to the user's message."

    try:
        model_gemini = genai.GenerativeModel('gemini-pro')
        response = model_gemini.generate_content(prompt)
        bot_response = response.text
    except Exception as e:
        bot_response = f"Error generating response: {e}"

    generate_and_store_fact(user_message, bot_response)
    return jsonify({'response': bot_response})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)