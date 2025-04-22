from flask import Flask, render_template, request, redirect, url_for, session
import joblib
import numpy as np
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret123'

# Load the model
model = joblib.load('diabetes_model.pkl')

# Initialize the database
def init_db():
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Pregnancies INTEGER,
            Glucose INTEGER,
            BloodPressure INTEGER,
            SkinThickness INTEGER,
            Insulin INTEGER,
            BMI REAL,
            DiabetesPedigreeFunction REAL,
            Age INTEGER,
            Prediction INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )''')
        conn.commit()

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                error = "Username already exists."
                return render_template('signup.html', error=error)
    return render_template('signup.html')

# Login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = c.fetchone()

        if user:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('predict'))
        else:
            return render_template('login.html', error="Incorrect credentials.")
    return render_template('login.html')

# Prediction
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    prediction = None
    patient_data = None

    if request.method == 'POST':
        try:
            data = {
                'Pregnancies': int(request.form['Pregnancies']),
                'Glucose': int(request.form['Glucose']),
                'BloodPressure': int(request.form['BloodPressure']),
                'SkinThickness': int(request.form['SkinThickness']),
                'Insulin': int(request.form['Insulin']),
                'BMI': float(request.form['BMI']),
                'DiabetesPedigreeFunction': float(request.form['DiabetesPedigreeFunction']),
                'Age': int(request.form['Age']),
            }

            features = np.array([[v for v in data.values()]])
            prediction = int(model.predict(features)[0])
            data['Prediction'] = prediction

            with sqlite3.connect('database.db') as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO patients 
                            (Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, 
                            DiabetesPedigreeFunction, Age, Prediction)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (*data.values(),))
                conn.commit()
                patient_id = c.lastrowid
                c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
                patient_data = c.fetchone()

        except Exception as e:
            return f"An error occurred: {e}"

    return render_template('form.html', prediction=prediction, patient=patient_data)

# List patients
@app.route('/patients')
def patients_list():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, Age, Glucose, Prediction FROM patients")
        patients = c.fetchall()

    return render_template('patients_list.html', patients=patients)

# Patient details
@app.route('/patient/<int:patient_id>')
def patient_info(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        patient = c.fetchone()

    return render_template('patient_info.html', patient=patient)

# Modify patient
@app.route('/modify_patient/<int:patient_id>', methods=['GET', 'POST'])
def modify_patient(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()

        if request.method == 'POST':
            updated_data = {
                'Pregnancies': int(request.form['Pregnancies']),
                'Glucose': int(request.form['Glucose']),
                'BloodPressure': int(request.form['BloodPressure']),
                'SkinThickness': int(request.form['SkinThickness']),
                'Insulin': int(request.form['Insulin']),
                'BMI': float(request.form['BMI']),
                'DiabetesPedigreeFunction': float(request.form['DiabetesPedigreeFunction']),
                'Age': int(request.form['Age']),
            }

            c.execute('''UPDATE patients SET Pregnancies=?, Glucose=?, BloodPressure=?, 
                        SkinThickness=?, Insulin=?, BMI=?, DiabetesPedigreeFunction=?, Age=? 
                        WHERE id=?''', (*updated_data.values(), patient_id))
            conn.commit()

            return redirect(url_for('patients_list'))

        c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        patient = c.fetchone()

    return render_template('modify_patient.html', patient=patient)

# Delete patient
@app.route('/delete/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()

    return redirect(url_for('patients_list'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Placeholder for forgot password
@app.route('/forgot_password')
def forgot_password():
    return "Forgot password page under construction."

if __name__ == '__main__':
    init_db()
    app.run(debug=True)







