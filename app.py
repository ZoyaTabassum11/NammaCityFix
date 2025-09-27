from twilio.rest import Client
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import requests
from werkzeug.utils import secure_filename



def send_sms(phone_number, name, ticket_id):
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        'authorization': '0rE2PANavZsQgdnofKOMxJ4Ct8eXbYqmp1wulHS6iWIzkBULVyWIuA2CrMRU4fVZalOyTXbp1SNzYnFP',  # Replace with your Fast2SMS API key
        'sender_id': 'FSTSMS',
        'message': f'Dear {name}, your complaint has been received. Ticket ID: {ticket_id}',
        'language': 'english',
        'route': 'v3',
        'numbers': phone_number
    }

    headers = {
        'cache-control': "no-cache"
    }

    response = requests.get(url, headers=headers, params=payload)
    print(response.text)

# SendGrid email setup
SENDGRID_API_KEY = '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'  # Replace with your SendGrid API Key
sendgrid_client = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)


app = Flask(__name__)
app.secret_key = 'kriyahackathon'  # Needed for session and flash messages

# Create DB and table if not exists




# Function to send email using Twilio SendGrid
def send_email(ticket_id, user_email):
    from_email = Email("sarahazeez04@gmail.com")  # Replace with your email address
    to_email = To(user_email)
    subject = "Complaint Received"
    content = Content("text/plain", f"Thank you for submitting your complaint! Your ticket ID is {ticket_id}. You can track your complaint with this ID.")
    
    mail = Mail(from_email, to_email, subject, content)
    try:
        response = sendgrid_client.send(mail)
        
        response = sendgrid_client.send(mail)
        print("Email sent!")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.body}")
        print(f"Response Headers: {response.headers}")

    except Exception as e:
        print(f"Error sending email: {e}")

def init_db():
    if not os.path.exists('users.db'):
        with sqlite3.connect('users.db') as conn:
            # Create users table
            conn.execute('''CREATE TABLE users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gov_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                designation TEXT NOT NULL,
                department TEXT NOT NULL,
                password TEXT NOT NULL
            )''')

            # Create complaints table
            conn.execute('''CREATE TABLE complaints (
                ticket_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                category TEXT NOT NULL,
                date DATE NOT NULL,
                description TEXT NOT NULL,
                image_filename TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                address TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                expected_date TEXT, 
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_to TEXT,
                resolved_image TEXT
            )''')

            print("Database initialized with 'users' and 'complaints' tables.")
    else:
        # If database exists, check if the 'status' column exists in 'complaints'
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            # Check if the 'status' column exists
            c.execute("PRAGMA table_info(complaints)")
            columns = [column[1] for column in c.fetchall()]
            if 'status' not in columns:
                # Add 'status' column if it doesn't exist
                c.execute("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'Pending'")
                print("Added 'status' column to 'complaints' table.")
            else:
                print("'status' column already exists in 'complaints' table.")


@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/complain')
def complain():
    return render_template('raisecomplain.html')

@app.route('/auth')
def auth():
    return render_template('auth.html')

@app.route('/jeweb')
def jeweb():
    if 'user_id' not in session or session.get('user_designation') != 'JE':
        return redirect(url_for('login'))

    je_id = session['user_id']  # assuming you store user_id in session on login

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Get complaints assigned to this JE
    c.execute("SELECT * FROM complaints WHERE assigned_to = ? AND status = 'In Progress'", (je_id,))
    pending_complaints = c.fetchall()

    # Get resolved complaints (optional)
    c.execute("SELECT * FROM complaints WHERE assigned_to = ? AND status = 'Resolved'", (je_id,))
    resolved_complaints = c.fetchall()

    conn.close()

    return render_template(
        'jeweb.html',
        pending_complaints=pending_complaints,
        resolved_complaints=resolved_complaints
    )


@app.route('/deptweb')
def deptweb():
    department = session.get('user_department')  # Department of the logged-in authority
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Fetch pending complaints that match the department's category
    c.execute("SELECT * FROM complaints WHERE status = 'Pending' AND category = ?", (department,))
    pending_complaints = c.fetchall()

    # Fetch resolved complaints that match the department's category
    c.execute("SELECT * FROM complaints WHERE status = 'Resolved' AND category = ?", (department,))
    resolved_complaints = c.fetchall()

    # Fetch JE users who belong to the same department as the logged-in user
    c.execute("SELECT * FROM users WHERE designation = 'JE' AND department = ?", (department,))
    je_list = c.fetchall()

    # In Progress complaints
    c.execute("SELECT * FROM complaints WHERE status = 'In Progress' AND category = ?", (department,))
    in_progress_complaints = c.fetchall()


    conn.close()
    
    return render_template('deptweb.html', 
                           pending_complaints=pending_complaints, 
                           resolved_complaints=resolved_complaints, 
                           je_list=je_list,in_progress_complaints=in_progress_complaints)

@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        gov_id = request.form['id']  # This is the govt-issued ID
        name = request.form['name']
        designation = request.form['designation']
        department = request.form['department']
        password = request.form['password']

        with sqlite3.connect('users.db') as conn:
            try:
                # Insert the new user into the database
                conn.execute("INSERT INTO users (gov_id, name, designation, department, password) VALUES (?, ?, ?, ?, ?)",
                             (gov_id, name, designation, department, password))
                conn.commit()

                # Get the user_id of the newly inserted user
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM users WHERE gov_id = ?", (gov_id,))
                user_id = cur.fetchone()[0]  # Fetch the user_id

                # Set session variables
                session['user_id'] = user_id
                session['user_name'] = name
                session['user_designation'] = designation
                session['user_department'] = department
                session['gov_id'] = gov_id

                flash("Signup successful!")

                # Redirect based on the designation
                if designation == 'Head':
                    return redirect(url_for('deptweb'))  # Redirect to Head dashboard
                elif designation == 'JE':
                    return redirect(url_for('jeweb'))  # Redirect to JE dashboard

            except sqlite3.IntegrityError:
                flash("Gov ID already exists. Please use a different one.")
                return redirect(url_for('auth'))

    return render_template('auth.html', action='signup')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        gov_id = request.form['id']
        password = request.form['password']

        with sqlite3.connect('users.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE gov_id=? AND password=?", (gov_id, password))
            user = cur.fetchone()

            if user:
                session['user_id'] = user[0]  # Add this!
                session['user_name'] = user[2]
                session['user_designation'] = user[3]
                session['user_department'] = user[4]
                session['gov_id'] = user[1]

                flash("Logged in successfully.")

                # Redirect based on the designation
                if user[3] == 'Head':
                    return redirect(url_for('deptweb'))  # Redirect to Head dashboard
                elif user[3] == 'JE':
                    return redirect(url_for('jeweb'))  # Redirect to JE dashboard
            else:
                flash("Invalid ID or password.")
                return redirect(url_for('auth'))

    return render_template('auth.html', action='login')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('auth'))

import random
import string

def generate_ticket_id():
    return 'TCKT' + ''.join(random.choices(string.digits, k=6))


@app.route('/subcomplaint', methods=['POST'])
def submit_complaint():
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    category = request.form['category']
    date=request.form['date']
    description=request.form['description']
    latitude = request.form['latitude']
    longitude = request.form['longitude']
    address = request.form['address']

    image = request.files['image']
    image_filename = secure_filename(image.filename)
    image_path = os.path.join('static/uploads', image_filename)
    image.save(image_path)

    ticket_id = generate_ticket_id()
    # Save to database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''INSERT INTO complaints 
                 (ticket_id, name, phone, email, category,date,description, image_filename, latitude, longitude, address) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?,?)''',
              (ticket_id, name, phone, email, category, date,description, image_filename, latitude, longitude, address))
    conn.commit()
    conn.close()

    # send_sms(phone, name, ticket_id)
    send_email(ticket_id, email)  # Send email

    # Redirect to the thank you page with the ticket_id
    return redirect(url_for('thank_you', ticket_id=ticket_id))

@app.route('/thankyou/<ticket_id>')
def thank_you(ticket_id):
    # Fetch the name of the user (optional, you can adjust this part)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT name FROM complaints WHERE ticket_id = ?', (ticket_id,))
    name = c.fetchone()[0]
    conn.close()

    return render_template("thankyou.html", name=name, ticket_id=ticket_id)

@app.route('/track', methods=['GET'])
def track():
    return render_template('track.html')

@app.route('/trackcomplaint', methods=['POST'])
def trackcomplaint():
    ticket_id = request.json.get('ticket_id')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM complaints WHERE ticket_id = ?", (ticket_id,))
    complaint = c.fetchone()
    conn.close()

    if complaint:
        return jsonify({
            "success": True,
            "ticket_id": complaint[0],
            "name": complaint[1],
            "email": complaint[3],
            "phone": complaint[2],
            "category": complaint[4],
            "description": complaint[6],
            "location": complaint[10],
            "status": complaint[11],
            "expected_resolution": complaint[12],
            "image": complaint[7]
        })
    else:
        return jsonify({"success": False, "message": "Invalid Ticket ID"})

@app.route('/assign_complaint/<ticket_id>', methods=['POST'])
def assign_complaint(ticket_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE complaints SET status = 'In Progress' WHERE ticket_id = ?", (ticket_id,))
    assigned_to = request.form['assigned_to']  # or however you fetch the JE name
    c.execute('UPDATE complaints SET assigned_to = ?, status = "In Progress" WHERE ticket_id = ?', (assigned_to, ticket_id))

    conn.commit()
    conn.close()

    flash("Complaint status updated to 'In Progress'")
    return redirect(url_for('deptweb'))

 # Optional if you want to show alerts


from flask import Flask, request, redirect, url_for, session, flash

@app.route('/resolve_complaint/<ticket_id>', methods=['POST'])
def resolve_complaint(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get the uploaded file
    resolved_image = request.files.get('resolved_image')
    if resolved_image:
        filename = secure_filename(resolved_image.filename)
        filepath = os.path.join('static', 'uploads', filename)
        resolved_image.save(filepath)

        # Update the database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE complaints SET status = 'Resolved', resolved_image = ? WHERE ticket_id = ?", (filename, ticket_id))
        conn.commit()
        conn.close()

        # Redirect back to JE dashboard to refresh data
        return redirect(url_for('jeweb'))

    return "Image not uploaded", 400

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
