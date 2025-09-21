import sqlite3
import random
import os
import io
import string
import secrets
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, send_from_directory, jsonify, send_file
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
import qrcode

app = Flask(__name__)
app.secret_key = "averysecretkey"
DATABASE = "app.db"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'alishapanday69@gmail.com'
app.config['MAIL_PASSWORD'] = 'qxvxiifxzujrrymb'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mail = Mail(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, commit=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    if commit:
        get_db().commit()
    return (rv[0] if rv else None) if one else rv

def generate_verification_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL, 
            password TEXT NOT NULL,
            coins INTEGER DEFAULT 0,
            profile_picture TEXT DEFAULT 'https://i.pravatar.cc/150',
            cover_image TEXT DEFAULT 'https://picsum.photos/600/200'
        );
        CREATE TABLE IF NOT EXISTS spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            story TEXT NOT NULL,
            image TEXT,
            uploader_id INTEGER,
            verification_code TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            FOREIGN KEY (uploader_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS bucket_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            spot_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(spot_id) REFERENCES spots(id),
            UNIQUE(user_id, spot_id)
        );
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            spot_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(spot_id) REFERENCES spots(id),
            UNIQUE(user_id, spot_id)
        );
        CREATE TABLE IF NOT EXISTS claimed_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            spot_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(spot_id) REFERENCES spots(id),
            UNIQUE(user_id, spot_id)
        );
        """)
        
        if not query_db("SELECT * FROM users"):
            query_db("""INSERT INTO users (username, email, password, profile_picture, cover_image) VALUES (?, ?, ?, ?, ?)""", ['Admin', 'admin@example.com', 'password', 'https://i.pravatar.cc/150?u=admin', 'https://picsum.photos/seed/picsum/600/200'], commit=True)

        if not query_db("SELECT * FROM spots"):
            admin_user = query_db("SELECT * FROM users WHERE username = ?", ['Admin'], one=True)
            sample_spots = [
                ("The Whispering Well", "Bhagalpur", "A legendary well in the old city quarter.", "uploads/sample_well.jpg", admin_user['id'], generate_verification_code(), 25.2424, 86.9850),
                ("Vikramshila Ruins", "Bhagalpur", "The remains of an ancient university.", "uploads/sample_ruins.jpg", admin_user['id'], generate_verification_code(), 25.3138, 87.2882)
            ]
            for spot in sample_spots:
                query_db("INSERT INTO spots (name, city, story, image, uploader_id, verification_code, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", spot, commit=True)

def get_current_user():
    if "user_id" not in session:
        return None
    return query_db("SELECT * FROM users WHERE id=?", [session["user_id"]], one=True)

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        user_by_username = query_db("SELECT * FROM users WHERE username=?", [username], one=True)
        if user_by_username:
            flash("Username already taken!")
            return redirect(url_for("register"))
        user_by_email = query_db("SELECT * FROM users WHERE email=?", [email], one=True)
        if user_by_email:
            flash("Email already registered!")
            return redirect(url_for("register"))
        otp = ''.join(random.choices(string.digits, k=6))
        session['registration_data'] = {'username': username, 'email': email, 'password': password}
        session['otp'] = otp
        msg = Message('Your Ghoomania App OTP', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f'Your verification OTP is: {otp}'
        mail.send(msg)
        flash("An OTP has been sent to your email. Please verify.")
        return redirect(url_for("verify_otp"))
    return render_template("register.html")

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if 'registration_data' not in session or 'otp' not in session:
        flash("Registration session expired. Please register again.")
        return redirect(url_for("register"))
    if request.method == "POST":
        user_otp = request.form['otp']
        if user_otp == session['otp']:
            user_data = session['registration_data']
            query_db("INSERT INTO users (username, email, password, coins) VALUES (?, ?, ?, ?)",
                     [user_data['username'], user_data['email'], user_data['password'], 0], commit=True)
            session.pop('registration_data', None)
            session.pop('otp', None)
            flash("Registration successful! Please login.")
            return redirect(url_for("login"))
        else:
            flash("Invalid OTP. Please try again.")
            return redirect(url_for("verify_otp"))
    return render_template("verify_otp.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = query_db("SELECT * FROM users WHERE username=? AND password=?", [username, password], one=True)
        if user:
            session["user_id"] = user["id"]
            flash("Login successful!")
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials. Please try again.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user:
        flash("Please login to access the dashboard.")
        return redirect(url_for("login"))
    
    feed_query = """
    SELECT
        s.id, s.name, s.city, s.story, s.image, s.verification_code,
        u.username as uploader_name,
        u.profile_picture as uploader_pfp,
        (SELECT COUNT(*) FROM recommendations WHERE spot_id = s.id) as rec_count,
        (SELECT COUNT(*) FROM recommendations WHERE spot_id = s.id) * 5 as potential_coins,
        (SELECT COUNT(*) FROM recommendations WHERE spot_id = s.id AND user_id = ?) as user_recommended,
        (SELECT COUNT(*) FROM bucket_list WHERE spot_id = s.id AND user_id = ?) as user_bucketed
    FROM spots s
    JOIN users u ON s.uploader_id = u.id
    ORDER BY rec_count DESC, s.id DESC
    """
    all_spots = query_db(feed_query, [user['id'], user['id']])
    
    top_spots_query = """
    SELECT s.id, s.name, s.image, COUNT(r.spot_id) as rec_count
    FROM spots s
    JOIN recommendations r ON s.id = r.spot_id
    GROUP BY s.id
    ORDER BY rec_count DESC
    LIMIT 10
    """
    top_spots = query_db(top_spots_query)

    return render_template("dashboard.html", user=user, spots=all_spots, top_spots=top_spots)

@app.route("/add_spot", methods=["GET", "POST"])
def add_spot():
    if request.method == 'POST':
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Not logged in'}), 401

        name = request.form.get('name')
        city = request.form.get('city')
        story = request.form.get('story')
        latitude_str = request.form.get('latitude')
        longitude_str = request.form.get('longitude')
        uploader_id = user['id']
        image_path = None
        verification_code = generate_verification_code()

        try:
            latitude = float(latitude_str)
            longitude = float(longitude_str)
        except (ValueError, TypeError):
            flash("Invalid coordinates. Please enter a valid number for latitude and longitude.", "danger")
            return redirect(url_for('dashboard'))

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        query_db("INSERT INTO spots (name, city, story, image, uploader_id, verification_code, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [name, city, story, image_path, uploader_id, verification_code, latitude, longitude], commit=True)
        
        flash("New hidden spot added successfully!")
        return redirect(url_for("dashboard"))
    
    return redirect(url_for("dashboard"))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)

@app.route('/spot/<int:spot_id>/qr_code')
def generate_qr_code(spot_id):
    verify_url = url_for('verify_scan', spot_id=spot_id, _external=True)
    qr_img = qrcode.make(verify_url)
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, 'PNG')
    img_buffer.seek(0)
    return send_file(img_buffer, mimetype='image/png')

@app.route('/verify_scan/<int:spot_id>', methods=['GET', 'POST'])
def verify_scan(spot_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login', next=url_for('verify_scan', spot_id=spot_id)))
    
    spot = query_db("SELECT * FROM spots WHERE id = ?", [spot_id], one=True)
    if not spot:
        flash("This spot does not exist.", "danger")
        return redirect(url_for('dashboard'))

    already_claimed = query_db("SELECT * FROM claimed_rewards WHERE user_id = ? AND spot_id = ?", [user['id'], spot_id], one=True)
    if already_claimed:
        flash("You have already claimed the reward for this spot.", "warning")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        submitted_code = request.form.get('code', '').strip().upper()
        try:
            user_lat = float(request.form.get('latitude'))
            user_lon = float(request.form.get('longitude'))
        except (TypeError, ValueError):
            flash("Could not get your location. Please enable location services and try again.", "danger")
            return redirect(url_for('verify_scan', spot_id=spot_id))

        spot_lat = float(spot['latitude'])
        spot_lon = float(spot['longitude'])
        distance = calculate_distance(user_lat, user_lon, spot_lat, spot_lon)
        
        if distance > 5:
            flash(f"You must be within 5km of the spot to claim this reward.", "danger")
            return redirect(url_for('verify_scan', spot_id=spot_id))

        correct_code = spot['verification_code'].upper()
        if submitted_code == correct_code:
            rec_count_result = query_db("SELECT COUNT(*) as count FROM recommendations WHERE spot_id = ?", [spot_id], one=True)
            rec_count = rec_count_result['count'] if rec_count_result else 0
            coins_to_award = 5 * rec_count
            
            new_coins = user['coins'] + coins_to_award
            query_db("UPDATE users SET coins = ? WHERE id = ?", [new_coins, user['id']], commit=True)
            query_db("INSERT INTO claimed_rewards (user_id, spot_id) VALUES (?, ?)", [user['id'], spot_id], commit=True)
            
            flash(f"Correct! You earned {coins_to_award} coins for finding {spot['name']}! 🎉", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Incorrect code. Please try again.", "danger")
            return redirect(url_for('verify_scan', spot_id=spot_id))

    return render_template('verify_scan.html', spot=spot)

@app.route('/recommend/<int:spot_id>', methods=['POST'])
def recommend_spot(spot_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'You must be logged in to recommend.'}), 401
    
    existing = query_db("SELECT * FROM recommendations WHERE user_id = ? AND spot_id = ?", [user['id'], spot_id], one=True)
    
    if existing:
        query_db("DELETE FROM recommendations WHERE user_id = ? AND spot_id = ?", [user['id'], spot_id], commit=True)
        recommended = False
    else:
        query_db("INSERT INTO recommendations (user_id, spot_id) VALUES (?, ?)", [user['id'], spot_id], commit=True)
        recommended = True
        
    count = query_db("SELECT COUNT(*) as count FROM recommendations WHERE spot_id = ?", [spot_id], one=True)['count']
    return jsonify({'recommended': recommended, 'count': count})

@app.route('/bucket/<int:spot_id>', methods=['POST'])
def bucket_spot(spot_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'You must be logged in.'}), 401
        
    existing = query_db("SELECT * FROM bucket_list WHERE user_id = ? AND spot_id = ?", [user['id'], spot_id], one=True)
    
    if existing:
        query_db("DELETE FROM bucket_list WHERE user_id = ? AND spot_id = ?", [user['id'], spot_id], commit=True)
        bucketed = False
    else:
        query_db("INSERT INTO bucket_list (user_id, spot_id) VALUES (?, ?)", [user['id'], spot_id], commit=True)
        bucketed = True
        
    return jsonify({'bucketed': bucketed})

@app.route('/my_bucket_list')
def my_bucket_list():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    query = """
    SELECT s.* FROM spots s
    JOIN bucket_list b ON s.id = b.spot_id
    WHERE b.user_id = ?
    """
    bucketed_spots = query_db(query, [user['id']])
    return render_template('bucket_list.html', spots=bucketed_spots, user=user)

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    with app.app_context():
        init_db()
    app.run(debug=True)