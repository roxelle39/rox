from flask import Flask, render_template, request, redirect, url_for, session
import joblib
import numpy as np
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret123'

# Load the model
model = joblib.load('diabetes_model.pkl')

# Temporary credentials
USERNAME = 'admin'
PASSWORD = '0000'

# Initialize the database
def init_db():
    conn = sqlite3.connect('database.db')
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
    conn.commit()
    conn.close()

# Login page
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('predict'))
        else:
            return render_template('login.html', error="Incorrect credentials.")
    return render_template('login.html')

# Prediction page
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

            # Save to the database
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute('''INSERT INTO patients 
                (Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age, Prediction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (*data.values(),))
            conn.commit()

            patient_id = c.lastrowid
            c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
            patient_data = c.fetchone()

            conn.close()
        except Exception as e:
            print("Error:", e)

    return render_template('form.html', prediction=prediction, patient=patient_data)

# Patients list
@app.route('/patients')
def patients_list():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, Age, Glucose, Prediction FROM patients")
    patients = c.fetchall()
    conn.close()

    return render_template('patients_list.html', patients=patients)

# Patient details
@app.route('/patient/<int:patient_id>')
def patient_info(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient = c.fetchone()
    conn.close()

    return render_template('patient_info.html', patient=patient)

# Delete a patient
@app.route('/delete/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('patients_list'))

# Logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return "Signup page coming soon..."

@app.route('/forgot_password')
def forgot_password():
    return "Forgot password page under construction."

if __name__ == '__main__':
    init_db()
    app.run(debug=True)



