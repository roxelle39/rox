from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import joblib
import numpy as np

app = Flask(__name__)
app.secret_key = 'diabetes_prediction_key'

# Charger le modèle et le scaler
try:
    model = joblib.load('model.pkl')
    scaler = joblib.load('scaler.pkl')
except Exception as e:
    print(f"Erreur lors du chargement : {e}")
    exit(1)

# Initialiser la base de données SQLite
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Table des utilisateurs (médecins)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    # Table des patients
    c.execute('''CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER,
        patient_name TEXT NOT NULL,
        pregnancies REAL,
        glucose REAL,
        bloodpressure REAL,
        skinthickness REAL,
        insulin REAL,
        bmi REAL,
        pedigree REAL,
        age REAL,
        result TEXT,
        probability REAL,
        FOREIGN KEY (doctor_id) REFERENCES users (id)
    )''')
    conn.commit()
    conn.close()

init_db()

# Route pour l'inscription
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash('Compte créé avec succès ! Veuillez vous connecter.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Ce nom d’utilisateur existe déjà.', 'danger')
        finally:
            conn.close()
    return render_template('signup.html')

# Route pour la connexion
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            session['user_id'] = user[0]  # Stocker l'ID du médecin
            session['username'] = user[1]
            flash('Connexion réussie !', 'success')
            return redirect(url_for('predict'))
        else:
            flash('Nom d’utilisateur ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

# Route pour la prédiction
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            patient_name = request.form['patient_name']
            features = [
                float(request.form['pregnancies']),
                float(request.form['glucose']),
                float(request.form['bloodpressure']),
                float(request.form['skinthickness']),
                float(request.form['insulin']),
                float(request.form['bmi']),
                float(request.form['pedigree']),
                float(request.form['age'])
            ]
            if any(x < 0 for x in features):
                flash('Les valeurs ne peuvent pas être négatives.', 'danger')
                return render_template('predict.html')
            features_array = np.array([features])
            features_scaled = scaler.transform(features_array)
            prediction = model.predict(features_scaled)[0]
            probability = model.predict_proba(features_scaled)[0][1]
            result = 'Diabétique' if prediction == 1 else 'Non diabétique'
            
            # Stocker les données du patient
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute('''INSERT INTO patients (doctor_id, patient_name, pregnancies, glucose, bloodpressure, skinthickness, insulin, bmi, pedigree, age, result, probability)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (session['user_id'], patient_name, *features, result, probability * 100))
            conn.commit()
            conn.close()
            
            # Préparer les données pour le tableau
            patient_data = {
                'Nom du patient': patient_name,
                'Grossesses': features[0],
                'Glucose': features[1],
                'Pression artérielle': features[2],
                'Épaisseur du pli cutané': features[3],
                'Insuline': features[4],
                'BMI': features[5],
                'Score génétique': features[6],
                'Âge': features[7],
                'Résultat': result,
                'Probabilité de diabète (%)': f"{probability * 100:.2f}"
            }
            flash('Données enregistrées avec succès !', 'success')
            return render_template('predict.html', patient_data=patient_data)
        except ValueError:
            flash('Veuillez entrer des valeurs numériques valides.', 'danger')
    
    return render_template('predict.html')

# Route pour la liste des patients
@app.route('/patients', methods=['GET'])
def patients():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM patients WHERE doctor_id = ?', (session['user_id'],))
    patients = c.fetchall()
    conn.close()
    
    return render_template('patients.html', patients=patients)

# Route pour modifier un patient
@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        try:
            patient_name = request.form['patient_name']
            features = [
                float(request.form['pregnancies']),
                float(request.form['glucose']),
                float(request.form['bloodpressure']),
                float(request.form['skinthickness']),
                float(request.form['insulin']),
                float(request.form['bmi']),
                float(request.form['pedigree']),
                float(request.form['age'])
            ]
            if any(x < 0 for x in features):
                flash('Les valeurs ne peuvent pas être négatives.', 'danger')
                return redirect(url_for('edit_patient', patient_id=patient_id))
            features_array = np.array([features])
            features_scaled = scaler.transform(features_array)
            prediction = model.predict(features_scaled)[0]
            probability = model.predict_proba(features_scaled)[0][1]
            result = 'Diabétique' if prediction == 1 else 'Non diabétique'
            
            c.execute('''UPDATE patients SET patient_name = ?, pregnancies = ?, glucose = ?, bloodpressure = ?, skinthickness = ?, insulin = ?, bmi = ?, pedigree = ?, age = ?, result = ?, probability = ?
                        WHERE id = ? AND doctor_id = ?''',
                     (patient_name, *features, result, probability * 100, patient_id, session['user_id']))
            conn.commit()
            flash('Données modifiées avec succès !', 'success')
            return redirect(url_for('patients'))
        except ValueError:
            flash('Veuillez entrer des valeurs numériques valides.', 'danger')
    
    c.execute('SELECT * FROM patients WHERE id = ? AND doctor_id = ?', (patient_id, session['user_id']))
    patient = c.fetchone()
    conn.close()
    if not patient:
        flash('Patient non trouvé ou non autorisé.', 'danger')
        return redirect(url_for('patients'))
    
    return render_template('edit_patient.html', patient=patient)

# Route pour supprimer un patient
@app.route('/delete_patient/<int:patient_id>')
def delete_patient(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM patients WHERE id = ? AND doctor_id = ?', (patient_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Patient supprimé avec succès.', 'success')
    return redirect(url_for('patients'))

# Route pour la déconnexion
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Déconnexion réussie.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)