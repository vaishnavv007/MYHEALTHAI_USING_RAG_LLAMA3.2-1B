import os
import base64
import json
import requests
import uuid
import shutil
import textwrap
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from pymongo import MongoClient, DESCENDING, ASCENDING
from werkzeug.security import generate_password_hash, check_password_hash
from config import MONGO_URI, SECRET_KEY, ADMIN_ACCESS_PASSWORD
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from chat_engine import ask_bot
import atexit
import textwrap
import base64
import requests
from pypdf import PdfReader
from docx import Document

from PIL import Image
import io
import subprocess





app = Flask(__name__)
app.secret_key = SECRET_KEY

client = MongoClient(MONGO_URI)
db = client['health_portal']
users_col = db['users']
admins_col = db['admins']
bmi_col = db['bmi']
doctors_col = db['doctors']

medical_col = db['medical_reports'] 




UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
@atexit.register
def cleanup_temp_folder():
    shutil.rmtree(UPLOAD_FOLDER, ignore_errors=True)


def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content
    except Exception as e:
        print("❌ Error reading PDF:", e)
    return text.strip()

def chat_with_ollama(prompt_text, model="llama3.2:1b"):
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt_text,
            text=True,
            capture_output=True,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Ollama Error: {result.stderr}"
    except FileNotFoundError:
        return "Ollama not found. Install from https://ollama.com/"
    






@app.route('/')
def home():
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = {
            'name': request.form['name'],
            'age': request.form['age'],
            'gender': request.form['gender'],
            'username': request.form['username'],
            'password': generate_password_hash(request.form['password'])
        }
        if users_col.find_one({'username': data['username']}):
            return "User already exists"
        users_col.insert_one(data)
        return redirect('/login')
    return render_template('signup.html')

@app.route('/admin_signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        access = request.form['access_code']
        if access != ADMIN_ACCESS_PASSWORD:
            return "Access Denied"
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if admins_col.find_one({'username': username}):
            return "Admin exists"
        admins_col.insert_one({'username': username, 'password': password})
        return redirect('/login')
    return render_template('admin_signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        password = request.form['password']

        if role == 'user':
            user = users_col.find_one({'username': username})
            if user and check_password_hash(user['password'], password):
                session['username'] = username
                session['role'] = 'user'
                return redirect('/user')
        elif role == 'admin':
            admin = admins_col.find_one({'username': username})
            if admin and check_password_hash(admin['password'], password):
                session['username'] = username
                session['role'] = 'admin'
                return redirect('/admin')
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
@app.route('/admin', methods=['GET'])
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    doctors = list(doctors_col.find())
    return render_template('admin_dashboard.html', username=session['username'], doctors=doctors)

# Add Doctor
@app.route('/add_doctor', methods=['POST'])
def add_doctor():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    data = {
        'name': request.form['name'],
        'gender': request.form['gender'],
        'category': request.form['category'],
        'qualification': request.form['qualification'],
        'hospital': request.form['hospital'],
        'state': request.form['state'],
        'district': request.form['district'],
        'location': request.form['location'],
        'rating': float(request.form['rating']),
        'map_link': request.form.get('map_link', ''),
        'phone': request.form['phone']
    }
    doctors_col.insert_one(data)
    return redirect(url_for('admin_dashboard'))

# Edit Doctor
@app.route('/edit_doctor/<id>', methods=['GET', 'POST'])
def edit_doctor(id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    doctor = doctors_col.find_one({'_id': ObjectId(id)})

    if request.method == 'POST':
        updated_data = {
            'name': request.form['name'],
            'gender': request.form['gender'],
            'category': request.form['category'],
            'qualification': request.form['qualification'],
            'hospital': request.form['hospital'],
            'state': request.form['state'],
            'district': request.form['district'],
            'location': request.form['location'],
            'rating': float(request.form['rating']),
            'map_link': request.form.get('map_link', ''),
            'phone': request.form['phone']
        }
        doctors_col.update_one({'_id': ObjectId(id)}, {'$set': updated_data})
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_doctor.html', doctor=doctor)

# Delete Doctor
@app.route('/delete_doctor/<id>')
def delete_doctor(id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    doctors_col.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('admin_dashboard'))

@app.route('/user', methods=['GET', 'POST'])
def user_dashboard():
    if 'username' not in session or session['role'] != 'user':
        return redirect('/login')

    username = session['username']

    # Filters from form
    selected_state = request.args.get('state')
    selected_district = request.args.get('district')
    selected_category = request.args.get('category')

    # Build query based on selected filters
    query = {}
    if selected_state:
        query['state'] = selected_state
    if selected_district:
        query['district'] = selected_district
    if selected_category:
        query['category'] = selected_category

    doctors = list(doctors_col.find(query))
    
    # Get unique filter values
    states = doctors_col.distinct('state')
    districts = doctors_col.distinct('district')
    categories = doctors_col.distinct('category')

    bmi_history = list(bmi_col.find({'username': username}).sort('date', -1))
    latest_bmi = bmi_history[0] if bmi_history else None
    chat_sessions = list(db.chat_sessions.find({'username': username}).sort('section', -1))
    medical_reports = list(db.medical_reports.find({'username': username}))

    return render_template(
        'user_dashboard.html',
        username=username,
        doctors=doctors,
        states=states,
        districts=districts,
        categories=categories,
        selected_state=selected_state,
        selected_district=selected_district,
        selected_category=selected_category,
        bmi_history=bmi_history,
        latest_bmi=latest_bmi,
        chat_sessions=chat_sessions,
        medical_reports=medical_reports
    )


@app.route('/bmi', methods=['POST'])
def calculate_bmi():
    if 'username' not in session or session['role'] != 'user':
        return redirect('/login')

    username = session['username']
    height = float(request.form['height'])
    weight = float(request.form['weight'])
    bmi = round(weight / ((height / 100) ** 2), 2)

    bmi_entry = {
        'username': username,
        'height': height,
        'weight': weight,
        'bmi': bmi,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    bmi_col.insert_one(bmi_entry)

    return redirect('/user')

@app.route('/ask', methods=['POST'])
def ask():
    if 'username' not in session or session['role'] != 'user':
        return "Unauthorized", 401

    username = session['username']
    question = request.form['prompt']
    answer = ask_bot(question)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    message = {
        'question': question,
        'answer': answer,
        'date': timestamp  # 🟢 Include date here
    }

    # Find latest section
    last_section = db.chat_sessions.find_one(
        {'username': username},
        sort=[('section', -1)]
    )

    if last_section and len(last_section['messages']) < 20:
        db.chat_sessions.update_one(
            {'_id': last_section['_id']},
            {'$push': {'messages': message}}
        )
    else:
        db.chat_sessions.insert_one({
            'username': username,
            'section': (last_section['section'] + 1) if last_section else 1,
            'messages': [message]
        })

    return {'question': question, 'answer': answer, 'date': timestamp}


@app.route('/delete_section/<int:section>')
def delete_section(section):
    if 'username' not in session or session['role'] != 'user':
        return redirect('/login')
    db.chat_sessions.delete_one({'username': session['username'], 'section': section})
    return redirect('/user')

@app.route('/delete_qa/<section>/<int:index>')
def delete_qa(section, index):
    if 'username' not in session or session['role'] != 'user':
        return redirect('/login')
    doc = db.chat_sessions.find_one({'username': session['username'], 'section': int(section)})
    if doc:
        messages = doc['messages']
        if 0 <= index < len(messages):
            del messages[index]
            db.chat_sessions.update_one({'_id': doc['_id']}, {'$set': {'messages': messages}})
    return redirect('/user')









@app.route('/add_medical', methods=['POST'])
def add_medical():
    if 'username' not in session or session['role'] != 'user':
        return redirect('/login')

    data = {
        'username': session['username'],
        'disease_or_injury': request.form['disease_or_injury'],
        'date_visited': request.form['date_visited'],
        'hospital_name': request.form['hospital_name'],
        'medicine_name': request.form['medicine_name'],
        'days': request.form['days'],
        'dosage_schedule': request.form['dosage_schedule']
    }
    medical_col.insert_one(data)
    return redirect('/user')

@app.route('/edit_medical/<id>', methods=['GET', 'POST'])
def edit_medical(id):
    if 'username' not in session or session['role'] != 'user':
        return redirect('/login')

    report = medical_col.find_one({'_id': ObjectId(id)})

    if request.method == 'POST':
        updated = {
            'disease_or_injury': request.form['disease_or_injury'],
            'date_visited': request.form['date_visited'],
            'hospital_name': request.form['hospital_name'],
            'medicine_name': request.form['medicine_name'],
            'days': request.form['days'],
            'dosage_schedule': request.form['dosage_schedule']
        }
        medical_col.update_one({'_id': ObjectId(id)}, {'$set': updated})
        return redirect('/user')

    return render_template('edit_medical.html', report=report)

@app.route('/delete_medical/<id>')
def delete_medical(id):
    if 'username' not in session or session['role'] != 'user':
        return redirect('/login')

    medical_col.delete_one({'_id': ObjectId(id)})
    return redirect('/user')








@app.route("/upload_file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"})

    if file and file.filename.lower().endswith(".pdf"):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        return jsonify({"filename": filename})
    else:
        return jsonify({"error": "Only PDF files are allowed"})



# 🟢 It uses ollama and pdf
@app.route("/qwen_chat", methods=["POST"])
def qwen_chat():
    data = request.get_json()
    filename = data.get("filename")
    question = data.get("question")

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"})

    text = extract_text_from_pdf(file_path)
    if not text:
        return jsonify({"answer": "❌ Could not extract text from PDF."})

    prompt = f"{question}\n\nDocument:\n{text[:6000]}"
    response = chat_with_ollama(prompt)
    return jsonify({"answer": response})




if __name__ == '__main__':
    app.run(debug=True)
