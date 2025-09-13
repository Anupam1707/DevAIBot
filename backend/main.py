import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import google.generativeai as genai
from pymongo import MongoClient
import nltk
from transformers import BertTokenizer, BertModel
import torch
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables
load_dotenv()

# Configure Gemini
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")
genai.configure(api_key=gemini_api_key)

# Configure MongoDB
mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    raise ValueError("MONGODB_URI not found in .env file")
client = MongoClient(mongo_uri)
db = client.get_database("chatbot_db")

# Load BERT model and tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

# Initialize Flask app
app = Flask(__name__, static_folder='../static', template_folder='../static')

# NLTK setup
nltk.download('punkt')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    # --- NLP Pipeline ---
    
    # 1. Get user facts from MongoDB
    # This is a simplified example. You'd likely have a user ID to associate facts with.
    user_facts_cursor = db.facts.find({})
    user_facts = [fact['fact'] for fact in user_facts_cursor]
    
    # 2. Use BERT to find relevant facts
    context = ""
    if user_facts:
        # Encode user message and facts
        message_embedding = model(**tokenizer(user_message, return_tensors='pt'))[0].mean(1)
        fact_embeddings = [model(**tokenizer(fact, return_tensors='pt'))[0].mean(1) for fact in user_facts]
        
        # Calculate cosine similarity
        similarities = [cosine_similarity(message_embedding.detach().numpy(), fact_embedding.detach().numpy())[0][0] for fact_embedding in fact_embeddings]
        
        # Get the most relevant fact
        if max(similarities) > 0.7: # Threshold for relevance
            most_relevant_fact = user_facts[similarities.index(max(similarities))]
            context = f"The user has previously mentioned: {most_relevant_fact}"

    # 3. Prepare prompt for Gemini
    prompt = f"User message: \"{user_message}\"\n\n{context}\n\nRespond to the user's message."

    # 4. Generate response with Gemini
    try:
        model_gemini = genai.GenerativeModel('gemini-2.5-flash')
        response = model_gemini.generate_content(prompt)
        bot_response = response.text
    except Exception as e:
        bot_response = f"Error generating response: {e}"

    # 5. Extract and save new facts (simplified)
    # In a real application, you'd have a more sophisticated way to identify new facts.
    if "my name is" in user_message.lower():
        name = user_message.lower().split("my name is")[1].strip()
        db.facts.insert_one({'fact': f"The user's name is {name}."})

    return jsonify({'response': bot_response})

if __name__ == '__main__':
    app.run(debug=True)
