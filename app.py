from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'soulmate_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///soulmate.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile = db.relationship('Profile', backref='user', uselist=False)
    sent_messages = db.relationship('Message', backref='sender', foreign_keys='Message.sender_id')
    received_messages = db.relationship('Message', backref='recipient', foreign_keys='Message.recipient_id')

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    height = db.Column(db.Float)
    religion = db.Column(db.String(50))
    caste = db.Column(db.String(50))
    education = db.Column(db.String(100))
    profession = db.Column(db.String(100))
    location = db.Column(db.String(100))
    about = db.Column(db.Text)
    profile_pic = db.Column(db.String(200))
    interests = db.Column(db.Text)
    partner_preferences = db.Column(db.Text)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!')
            return redirect(url_for('register'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered!')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('login'))
        
        session['user_id'] = user.id
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    unread_messages = Message.query.filter_by(recipient_id=user.id, is_read=False).count()
    
    return render_template('dashboard.html', user=user, unread_messages=unread_messages)

@app.route('/create_profile', methods=['GET', 'POST'])
def create_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if user.profile:
        return redirect(url_for('edit_profile'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        gender = request.form.get('gender')
        dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d')
        height = float(request.form.get('height'))
        religion = request.form.get('religion')
        caste = request.form.get('caste')
        education = request.form.get('education')
        profession = request.form.get('profession')
        location = request.form.get('location')
        about = request.form.get('about')
        interests = request.form.get('interests')
        partner_preferences = request.form.get('partner_preferences')
        
        # Handle profile picture upload
        profile_pic = None
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                profile_pic = filename
        
        new_profile = Profile(
            user_id=user.id,
            full_name=full_name,
            gender=gender,
            dob=dob,
            height=height,
            religion=religion,
            caste=caste,
            education=education,
            profession=profession,
            location=location,
            about=about,
            profile_pic=profile_pic,
            interests=interests,
            partner_preferences=partner_preferences
        )
        
        db.session.add(new_profile)
        db.session.commit()
        
        flash('Profile created successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('create_profile.html')

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    profile = user.profile
    
    if not profile:
        return redirect(url_for('create_profile'))
    
    if request.method == 'POST':
        profile.full_name = request.form.get('full_name')
        profile.gender = request.form.get('gender')
        profile.dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d')
        profile.height = float(request.form.get('height'))
        profile.religion = request.form.get('religion')
        profile.caste = request.form.get('caste')
        profile.education = request.form.get('education')
        profile.profession = request.form.get('profession')
        profile.location = request.form.get('location')
        profile.about = request.form.get('about')
        profile.interests = request.form.get('interests')
        profile.partner_preferences = request.form.get('partner_preferences')
        
        # Handle profile picture upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                profile.profile_pic = filename
        
        db.session.commit()
        
        flash('Profile updated successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_profile.html', profile=profile)

@app.route('/search', methods=['GET', 'POST'])
def search():
    now = datetime.now().date()
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    profiles = []
    
    if request.method == 'POST':
        gender = request.form.get('gender')
        min_age = int(request.form.get('min_age', 18))
        max_age = int(request.form.get('max_age', 60))
        religion = request.form.get('religion')
        
        # Calculate date range for age filter
        max_date = datetime.now().replace(year=datetime.now().year - min_age)
        min_date = datetime.now().replace(year=datetime.now().year - max_age)
        
        query = Profile.query.filter(Profile.user_id != session['user_id'])
        
        if gender:
            query = query.filter_by(gender=gender)
        
        if religion:
            query = query.filter_by(religion=religion)
        
        query = query.filter(Profile.dob.between(min_date, max_date))
        
        profiles = query.all()
        
    return render_template('search.html', profiles=profiles,now=now)

@app.route('/profile/<int:user_id>')
def view_profile(user_id):
    now = datetime.now().date()
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    profile = Profile.query.filter_by(user_id=user_id).first_or_404()
    
    return render_template('view_profile.html', profile=profile,now=now)

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    received = Message.query.filter_by(recipient_id=user_id).order_by(Message.timestamp.desc()).all()
    sent = Message.query.filter_by(sender_id=user_id).order_by(Message.timestamp.desc()).all()
    
    # Mark messages as read
    for message in received:
        if not message.is_read:
            message.is_read = True
    
    db.session.commit()
    
    return render_template('messages.html', received=received, sent=sent)

@app.route('/send_message/<int:recipient_id>', methods=['GET', 'POST'])
def send_message(recipient_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    recipient = User.query.get_or_404(recipient_id)
    
    if request.method == 'POST':
        content = request.form.get('content')
        
        new_message = Message(
            sender_id=session['user_id'],
            recipient_id=recipient_id,
            content=content
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        flash('Message sent successfully!')
        return redirect(url_for('view_profile', user_id=recipient_id))
    
    return render_template('send_message.html', recipient=recipient)

@app.route('/success_stories')
def success_stories():
    return render_template('success_stories.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        db.create_all()
    app.run(debug=True)