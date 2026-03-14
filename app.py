from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
import pickle
import numpy as np
import pandas as pd
import re
import os
import cv2
from pyzbar.pyzbar import decode
from datetime import datetime
import json

app = Flask(__name__, 
            template_folder='templates',
            static_folder='frontend',
            static_url_path='/frontend')

app.secret_key = "fraudshield_startup_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fraudshield.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE MODELS ---

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.String(50))
    sender = db.Column(db.String(100))
    receiver = db.Column(db.String(100))
    amount = db.Column(db.Float)
    location = db.Column(db.String(100))
    risk_score = db.Column(db.Float)
    status = db.Column(db.String(50)) # Legitimate, Suspicious, Fraud
    details = db.Column(db.Text)

class SuspiciousUPI(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    upi_id = db.Column(db.String(100), unique=True)
    reason = db.Column(db.String(255))

with app.app_context():
    db.create_all()
    # Seed suspicious list if empty
    if not SuspiciousUPI.query.first():
        seeds = [
            ("loan-support@upi", "Fake Loan Assistance"),
            ("amazon-refund-help@upi", "Phishing Refund Scam"),
            ("badguy@upi", "Known Fraudster"),
            ("scammer@okaxis", "Fraudulent Account")
        ]
        for upi, reason in seeds:
            db.session.add(SuspiciousUPI(upi_id=upi, reason=reason))
        db.session.commit()

# --- AUTHENTICATION ---
USERS = {
    "user1@fraudshield.ai": "123456",
    "user2@fraudshield.ai": "654321",
    "user3@fraudshield.ai": "fraud123"
}

# --- ML MODEL LOAD ---
try:
    model = pickle.load(open("model/fraud_model.pkl", "rb"))
except:
    model = None

# --- FRAUD ENGINE ---

def calculate_risk(amount, receiver, location_anomaly, behavioral_anomaly=0):
    """
    Calculates a comprehensive risk score (0-100)
    """
    score = 0
    
    # 1. Amount Factor (Higher amount = higher risk baseline)
    if amount > 50000: score += 40
    elif amount > 10000: score += 20
    elif amount > 5000: score += 10
    
    # 2. Receiver Factor
    suspicious_match = SuspiciousUPI.query.filter_by(upi_id=receiver.lower()).first()
    if suspicious_match:
        score += 50
        
    # 3. Location Factor
    if location_anomaly:
        score += 30
        
    # 4. Behavioral Anomaly
    score += behavioral_anomaly
    
    # 5. ML Model Integration (if available)
    if model:
        # Simulate features for the model
        cols = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount']
        features_df = pd.DataFrame([[0.0] * 30], columns=cols)
        features_df.at[0, 'Amount'] = amount
        # Add some variation based on factors
        features_df.at[0, 'V4'] = 5.0 if score > 50 else -2.0
        
        prob = model.predict_proba(features_df)[0][1]
        ml_score = float(prob * 100)
        # Average the logic score and ML score
        score = (score + ml_score) / 2

    final_score = min(100, max(0, score))
    
    if final_score >= 70: status = "Fraud"
    elif final_score >= 30: status = "Suspicious"
    else: status = "Legitimate"
    
    return round(final_score, 2), status

# --- ROUTES ---

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email in USERS and USERS[email] == password:
            session['logged_in'] = True
            session['user'] = email
            return redirect(url_for('dashboard'))
        flash("Invalid Credentials", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('landing'))

@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template("dashboard.html", page="dashboard")

@app.route("/live_monitor")
def live_monitor():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template("live_feed.html", page="live_monitor")

@app.route("/sms_analysis")
def sms_analysis():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template("sms_analysis.html", page="sms_analysis")

@app.route("/upi_verification")
def upi_verification():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template("upi_protection.html", page="upi_verification")

@app.route("/qr_scanner")
def qr_scanner():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template("qr_scanner.html", page="qr_scanner")

@app.route("/analytics")
def analytics():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template("analytics.html", page="analytics")

# --- API ENDPOINTS ---

@app.route("/api/process_transaction", methods=["POST"])
def process_tx():
    data = request.json
    amount = float(data.get("amount", 0))
    receiver = data.get("receiver", "Unknown")
    sender = data.get("sender", session.get('user', 'Guest'))
    location_anomaly = data.get("location_anomaly", False)
    behavioral = data.get("behavioral", 0)
    
    risk_score, status = calculate_risk(amount, receiver, location_anomaly, behavioral)
    
    new_tx = Transaction(
        time=datetime.now().strftime("%I:%M %p"),
        sender=sender,
        receiver=receiver,
        amount=amount,
        location=data.get("location", "Unknown"),
        risk_score=risk_score,
        status=status,
        details=json.dumps(data)
    )
    db.session.add(new_tx)
    db.session.commit()
    
    return jsonify({
        "risk_score": risk_score,
        "status": status,
        "time": new_tx.time
    })

@app.route("/api/scan_qr", methods=["POST"])
def scan_qr():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    img_array = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    decoded_objects = decode(img)
    if not decoded_objects:
        return jsonify({"error": "No QR Code found"}), 400
    
    qr_data = decoded_objects[0].data.decode('utf-8')
    # Parse UPI URL: upi://pay?pa=merchant@upi&pn=MerchantName&am=100
    pa_match = re.search(r'pa=([\w\.\-]+@[\w\-]+)', qr_data)
    pn_match = re.search(r'pn=([\w\s%\.\-]+)', qr_data)
    am_match = re.search(r'am=([\d\.]+)', qr_data)
    
    upi_id = pa_match.group(1) if pa_match else "Unknown"
    merchant = pn_match.group(1).replace('%20', ' ') if pn_match else "Unknown"
    amount = float(am_match.group(1)) if am_match else 0.0
    
    return jsonify({
        "upi_id": upi_id,
        "merchant": merchant,
        "amount": amount,
        "raw_data": qr_data
    })

@app.route("/api/get_history")
def get_history():
    history = Transaction.query.order_by(Transaction.id.desc()).limit(20).all()
    return jsonify([{
        "time": tx.time,
        "sender": tx.sender,
        "receiver": tx.receiver,
        "amount": tx.amount,
        "location": tx.location,
        "risk_score": tx.risk_score,
        "status": tx.status
    } for tx in history])

@app.route("/api/report_upi", methods=["POST"])
def report_upi():
    data = request.json
    upi_id = data.get("upi_id")
    if upi_id:
        if not SuspiciousUPI.query.filter_by(upi_id=upi_id).first():
            db.session.add(SuspiciousUPI(upi_id=upi_id, reason="User Reported"))
            db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route("/download_report")
def download_report():
    txs = Transaction.query.order_by(Transaction.id.desc()).limit(50).all()
    if not txs: return "No data", 400

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(190, 20, "FraudShield AI - Executive Fraud Report", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(25, 10, "Time", 1, 0, 'C', 1)
    pdf.cell(50, 10, "Merchant/Receiver", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Amount", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Risk %", 1, 0, 'C', 1)
    pdf.cell(50, 10, "Status", 1, 1, 'C', 1)
    
    pdf.set_font("Arial", '', 9)
    for tx in txs:
        pdf.cell(25, 10, tx.time, 1)
        pdf.cell(50, 10, tx.receiver[:25], 1)
        pdf.cell(30, 10, f"Rs {tx.amount}", 1)
        pdf.cell(30, 10, f"{tx.risk_score}%", 1)
        
        status = tx.status
        if status == "Fraud": pdf.set_text_color(200, 0, 0)
        elif status == "Suspicious": pdf.set_text_color(200, 150, 0)
        else: pdf.set_text_color(0, 150, 0)
        
        pdf.cell(50, 10, status, 1, 1)
        pdf.set_text_color(0, 0, 0)
        
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment', filename='FraudShield_Executive_Report.pdf')
    return response

if __name__ == "__main__":
    app.run(debug=True)