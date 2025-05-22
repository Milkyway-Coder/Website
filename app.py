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

    def get_profile_views_count(self):
        return ProfileView.query.filter_by(viewed_id=self.id).count()
    
    def get_interests_received_count(self):
        return Interest.query.filter_by(recipient_id=self.id).count()
    
    def get_pending_interests_received_count(self):
        return Interest.query.filter_by(recipient_id=self.id, status='pending').count()    

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

class Interest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_interests')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_interests')

class ProfileView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    viewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    viewed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    viewer = db.relationship('User', foreign_keys=[viewer_id], backref='profile_views')
    viewed = db.relationship('User', foreign_keys=[viewed_id], backref='profile_viewers')


class SavedProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    saved_profile_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Define relationships
    saver = db.relationship('User', foreign_keys=[user_id], backref='saved_profiles')
    saved = db.relationship('User', foreign_keys=[saved_profile_id], backref='saved_by')
    
    # Add a unique constraint to prevent duplicate saves
    __table_args__ = (
        db.UniqueConstraint('user_id', 'saved_profile_id', name='unique_saved_profile'),
    )


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
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get profile view count
    profile_views_count = ProfileView.query.filter_by(viewed_id=user_id).count()
    
    # Get interest counts
    interests_received_count = Interest.query.filter_by(recipient_id=user_id).count()
    
    # Get unread message count
    unread_messages = Message.query.filter_by(recipient_id=user_id, is_read=False).count()

    # Get received pending interests count (assuming you have a status field)
    received_pending_interests_count = Interest.query.filter_by(recipient_id=user_id, status='pending').count()

    # Get saved profiles count - Add this line
    saved_profiles_count = SavedProfile.query.filter_by(user_id=user_id).count()
    
    return render_template(
        'dashboard.html', 
        user=user, 
        unread_messages=unread_messages, 
        profile_views_count=profile_views_count,
        interests_received_count=interests_received_count,
        received_pending_interests_count=received_pending_interests_count,
        saved_profiles_count=saved_profiles_count
    )

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
    
    # Retrieve the current user
    current_user_id = session['user_id']
    user = User.query.get(current_user_id)  # Get the current user from the database
    
    # Don't track if viewing own profile
    if current_user_id != user_id:
        # Record profile view
        new_view = ProfileView(
            viewer_id=current_user_id,
            viewed_id=user_id
        )
        db.session.add(new_view)
        db.session.commit()
    
    profile = Profile.query.filter_by(user_id=user_id).first_or_404()
    
    # Check if current user has sent an interest to this profile
    interest_status = None
    if current_user_id != user_id:
        interest = Interest.query.filter_by(
            sender_id=current_user_id, 
            recipient_id=user_id
        ).first()
        if interest:
            interest_status = interest.status

    # Check if profile is already saved by current user
    is_saved = SavedProfile.query.filter_by(
        user_id=current_user_id,
        saved_profile_id=user_id
    ).first() is not None
    
    return render_template('view_profile.html', user=user, profile=profile, now=now, interest_status=interest_status, is_saved=is_saved)

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

@app.route('/express_interest/<int:recipient_id>')
def express_interest(recipient_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Check if interest already exists
    existing_interest = Interest.query.filter_by(
        sender_id=session['user_id'], 
        recipient_id=recipient_id
    ).first()
    
    if existing_interest:
        flash('You have already expressed interest in this profile.')
        return redirect(url_for('view_profile', user_id=recipient_id))
    
    # Create new interest
    new_interest = Interest(
        sender_id=session['user_id'],
        recipient_id=recipient_id
    )
    
    db.session.add(new_interest)
    db.session.commit()
    
    flash('Interest expressed successfully!')
    return redirect(url_for('view_profile', user_id=recipient_id))

@app.route('/browse_matches')
def browse_matches():
    # Logic for browsing matches
    return render_template('search.html')

@app.route('/interests')
def interests():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    received_interests = Interest.query.filter_by(recipient_id=user_id).order_by(Interest.timestamp.desc()).all()
    sent_interests = Interest.query.filter_by(sender_id=user_id).order_by(Interest.timestamp.desc()).all()
    
    return render_template('interests.html', received_interests=received_interests, sent_interests=sent_interests)

@app.route('/respond_interest/<int:interest_id>/<string:response>')
def respond_interest(interest_id, response):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    interest = Interest.query.get_or_404(interest_id)
    
    # Ensure the user is the recipient of the interest
    if interest.recipient_id != session['user_id']:
        flash('Unauthorized action.')
        return redirect(url_for('interests'))
    
    if response == 'accept':
        interest.status = 'accepted'
        flash('Interest accepted!')
    elif response == 'decline':
        interest.status = 'declined'
        flash('Interest declined.')
    elif response == 'change':
        # Show a page to change the response
        return render_template('change_response.html', interest=interest)
    
    db.session.commit()
    return redirect(url_for('interests'))

@app.route('/update_interest_response/<int:interest_id>', methods=['POST'])
def update_interest_response(interest_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    interest = Interest.query.get_or_404(interest_id)
    
    # Ensure the user is the recipient of the interest
    if interest.recipient_id != session['user_id']:
        flash('Unauthorized action.')
        return redirect(url_for('interests'))
    
    # Get the new status from the form
    new_status = request.form.get('status')
    
    # Update the status
    if new_status in ['accepted', 'declined']:
        old_status = interest.status  # Store the old status for flash message
        interest.status = new_status
        
        if old_status == new_status:
            flash(f'No changes made. The interest remains {new_status}.')
        else:
            flash(f'Your response has been updated from {old_status} to {new_status}!')
            
        db.session.commit()
    else:
        flash('Invalid status.')
    
    return redirect(url_for('interests'))


# Add these routes to your Flask app

# Save or unsave a profile
@app.route('/save_profile/<int:profile_id>', methods=['POST'])
def save_profile(profile_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Check if already saved
    existing_save = SavedProfile.query.filter_by(
        user_id=user_id,
        saved_profile_id=profile_id
    ).first()
    
    if existing_save:
        # Unsave the profile
        db.session.delete(existing_save)
        db.session.commit()
        flash('Profile removed from favorites!', 'success')
    else:
        # Save the profile
        new_save = SavedProfile(
            user_id=user_id,
            saved_profile_id=profile_id,
            notes=""
        )
        db.session.add(new_save)
        db.session.commit()
        flash('Profile added to favorites!', 'success')
    
    # Get the URL to return to
    next_page = request.args.get('next') or request.referrer or url_for('dashboard')
    return redirect(next_page)

# View saved profiles
@app.route('/saved_profiles')
def saved_profiles():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    now = datetime.now().date()
    
    # Get saved profiles with their user and profile data
    saved = db.session.query(
        SavedProfile, User, Profile
    ).join(
        User, User.id == SavedProfile.saved_profile_id
    ).join(
        Profile, Profile.user_id == SavedProfile.saved_profile_id
    ).filter(
        SavedProfile.user_id == user_id
    ).order_by(
        SavedProfile.timestamp.desc()
    ).all()
    
    # Check interests status for each saved profile
    saved_data = []
    for saved_record, saved_user, saved_profile in saved:
        # Check if user has sent an interest to this profile
        interest = Interest.query.filter_by(
            sender_id=user_id,
            recipient_id=saved_user.id
        ).first()
        
        interest_status = interest.status if interest else None
        
        saved_data.append({
            'saved_record': saved_record,
            'user': saved_user,
            'profile': saved_profile,
            'interest_status': interest_status
        })
    
    # Get counts for the sidebar
    unread_messages = Message.query.filter_by(recipient_id=user_id, is_read=False).count()
    received_pending_interests_count = Interest.query.filter_by(recipient_id=user_id, status='pending').count()
    
    return render_template(
        'saved_profiles.html',
        user=user,
        saved_data=saved_data,
        now=now,
        unread_messages=unread_messages,
        received_pending_interests_count=received_pending_interests_count
    )

# Update saved profile notes
@app.route('/update_saved_notes/<int:saved_id>', methods=['POST'])
def update_saved_notes(saved_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    saved = SavedProfile.query.get_or_404(saved_id)
    
    # Ensure the user owns this saved profile
    if saved.user_id != user_id:
        flash('Unauthorized action.')
        return redirect(url_for('saved_profiles'))
    
    notes = request.form.get('notes', '')
    saved.notes = notes
    db.session.commit()
    
    flash('Notes updated successfully!', 'success')
    return redirect(url_for('saved_profiles'))


if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        db.create_all()
    app.run(debug=True)