from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = '9ee34f31414d79cb9b5c0bf86e821da7'


DATABASE = 'mydatabase.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        disaster_type TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        latitude REAL,
        longitude REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    ''')
    # Add the created_at column if it does not already exist
    try:
        db.execute('ALTER TABLE reports ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except sqlite3.OperationalError:
        # Column already exists, no action needed
        pass

    db.commit()

# Call the init_db function to initialize the database
init_db()

# Function to generate a random OTP
def generate_otp():
    return str(random.randint(100000, 999999))

# Function to send OTP email
def send_otp(recipient, otp):
    sender_email = "auth.me.official@outlook.com" 
    sender_password = "#aB@8098"
    smtp_server = "smtp-mail.outlook.com"
    smtp_port = 587

    subject = "Your OTP Verification Code"
    body = f"Your OTP code is: {otp}"

    msg = MIMEText(body)
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
        print("OTP sent successfully!")
    except Exception as e:
        print(f"Failed to send OTP. Error: {str(e)}")


@app.route('/submit_report', methods=['POST'])
def submit_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    disaster_type = request.form['disaster_type']
    description = request.form['description']
    location = request.form['location']
    user_id = session['user_id']

    db = get_db()
    db.execute('INSERT INTO reports (user_id, disaster_type, description, location) VALUES (?, ?, ?, ?)',
               (user_id, disaster_type, description, location))
    db.commit()
    print('Success')

    flash('Report submitted successfully!')
    return redirect(url_for('user_dashboard'))

@app.route('/logout', endpoint='logout')
def logout():
    # Logic for logging out the user
    return redirect(url_for('login'))


@app.route('/user/view_reports')
def view_reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db()
    
    # Fetch reports submitted by the logged-in user
    reports = db.execute('SELECT disaster_type, description, location, created_at FROM reports WHERE user_id = ?',
                         (user_id,)).fetchall()
    
    # Render the template with the reports
    return render_template('templates_user/view_reports.html', reports=reports)

# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user:
            # User exists, verify password
            if user['password'] == password:  # Consider using hashed passwords
                session['user_id'] = user['id']
                if role == 'user':
                    return redirect(url_for('user_dashboard'))
                elif role == 'admin':
                    return redirect(url_for('admin_dashboard'))
            else:
                flash('Login Unsuccessful. Please check your email and password.')
        else:
            # User doesn't exist, send OTP and redirect to verification
            otp = generate_otp()
            send_otp(email, otp)
            session['otp'] = otp
            session['otp_email'] = email
            return redirect(url_for('verify'))

    return render_template('login.html')

# OTP verification route
@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        if entered_otp == session.get('otp'):
            # OTP is correct, save user to database
            email = session.get('otp_email')
            password = request.form['password']  # User should enter password during OTP verification

            db = get_db()
            db.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
            db.commit()

            session['user_id'] = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()['id']
            flash('Account created successfully. You are now logged in.')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid OTP. Please try again.')
            return redirect(url_for('verify'))

    return render_template('verify.html')

# User dashboard route (after successful login)
@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    email = session.get('otp_email')
    # Assuming 'user_email' is stored in the session
    user_email = session.get('otp_email', 'Not Available')  # Provide a default value if email is not available
    print(user_email)
    return render_template('templates_user/dashboard.html', username=user_email)


# Admin and user routes (unchanged)
# @app.route('/admin/dashboard')
# def admin_dashboard():
#     return render_template('templates_admin/dashboard.html')

@app.route('/admin/map')
def admin_map():
    return render_template('templates_admin/map.html')

@app.route('/admin/report_manage')
def report_manage():
    db = get_db()
    reports = db.execute('SELECT * FROM reports').fetchall()
    return render_template('templates_admin/report_manage.html', reports=reports)


@app.route('/admin/report_manage/delete/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    db = get_db()
    db.execute('DELETE FROM reports WHERE id = ?', (report_id,))
    db.commit()
    return redirect(url_for('report_manage'))

# @app.route('/admin/report_manage/resolve/<int:report_id>', methods=['POST'])
# def resolve_report(report_id):
#     db = get_db()
#     db.execute('UPDATE reports SET status = "Resolved" WHERE id = ?', (report_id,))
#     db.commit()
#     return redirect(url_for('report_manage'))

@app.route('/admin/report_manage/resolve/<int:report_id>', methods=['POST'])
def resolve_report(report_id):
    db = get_db()
    db.execute('UPDATE reports SET status = "Resolved" WHERE id = ?', (report_id,))
    db.commit()
    return redirect(url_for('report_manage'))


@app.route('/admin/communication')
def communication():
    return render_template('templates_admin/communication.html')

@app.route('/user/map')
def user_map():
    return render_template('templates_user/map.html')

@app.route('/user/report')
def user_report():
    return render_template('templates_user/report.html')

@app.route('/user/support')
def user_support():
    return render_template('templates_user/support.html')




def get_dashboard_data():
    # Connect to SQLite database
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()

    # Get total reports
    cursor.execute('SELECT COUNT(*) FROM reports')
    total_reports = cursor.fetchone()[0]

    # Get active incidents
    cursor.execute('SELECT COUNT(*) FROM reports WHERE status = "Pending"')  # Assuming 'Pending' is used for active
    active_incidents = cursor.fetchone()[0]

    # Get resolved reports
    cursor.execute('SELECT COUNT(*) FROM reports WHERE status = "Resolved"')
    reports_resolved = cursor.fetchone()[0]

    # Get users reporting
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM reports')
    reporting_users = cursor.fetchone()[0]

    # Get recent reports
    cursor.execute('SELECT id, user_id, disaster_type, location, status, created_at FROM reports ORDER BY created_at DESC LIMIT 10')
    recent_reports = cursor.fetchall()

    conn.close()

    return {
        'total_reports': total_reports,
        'active_incidents': active_incidents,
        'reports_resolved': reports_resolved,
        'reporting_users': reporting_users,
        'recent_reports': recent_reports
    }

@app.route('/admin_dashboard')
def admin_dashboard():
    data = get_dashboard_data()
    return render_template('templates_admin/dashboard.html', **data)




if __name__ == '__main__':
    app.run(debug=True)
