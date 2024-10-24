from flask import render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from app import app, db
from app.models import User
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from app.forms import *
import pandas as pd
import io

key = None

def encrypt_session_value(value):
    global key
    # make key url-safe
    key = Fernet.generate_key() if key is None else key
    
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_session_value(value):
    global key
    key = key if key is not None else Fernet.generate_key()
    f = Fernet(key)
    return f.decrypt(value.encode()).decode()

def get_session_user_id():
    session_key = session.keys()
    
    for key_ in session_key:
        try:
            valid_key = key_
            user_id = decrypt_session_value(session[key_])
        except:
            continue 
        if decrypt_session_value(key_) == app.secret_key:
            return user_id
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if get_session_user_id() is None:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def login_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_session_user_id()
        if user_id is None:
            return redirect(url_for('login'))
        user = User.query.get(user_id)
        if not user.is_admin:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

class BlankUser:
    def __init__(self):
        self.is_admin = False
        self.username = ''
        self.email = ''



# inject data to template
@app.context_processor
def inject_data():
    # is user logged in
    user = None
    if key:
        try:
            user_id = get_session_user_id()
            if user_id:
                user = User.query.get(user_id)
            else:
                user = BlankUser()
        except:
            pass
    return dict(user=user, is_admin=user.is_admin if user else False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    user = {'username': '', 'email': ''}
    is_admin_exists = User.query.filter_by(is_admin=True).first()
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            user = {'username': username, 'email': email}
            if username == '':
                flash('Username tidak boleh kosong', 'error')
                return redirect(url_for('register'))
            

            if password == '':
                flash('Password tidak boleh kosong', 'error')
                return redirect(url_for('register'))
            
            if confirm_password == '':
                flash('Konfirmasi password tidak boleh kosong', 'error')
                return redirect(url_for('register'))

            
            # check if username already exists
            if User.query.filter_by(username=username).first():
                flash('Username sudah ada', 'error')
            # check if email already exists
            if User.query.filter_by(email=email).first():
                flash('Email sudah ada', 'error')
            
            if password != confirm_password:
                flash('Password dan konfirmasi password tidak sama', 'error')
                return redirect(url_for('register'))
            
            # if flash message is not empty, redirect to register page
            if '_flashes' in session:
                return redirect(url_for('register',is_admin_exists=is_admin_exists, users=user))
            try:
                # cek apakah checkbox is_admin diinput
                is_admin = request.form['is_admin'] == 'y'
                print(is_admin)
                
            except KeyError:
                
                is_admin = False
            
            
            # Membuat objek user dan set password
            user_ = User(username=username, email=email, is_admin=is_admin)
            user_.set_password(password)
            
            # Menyimpan user ke database
            db.session.add(user_)
            db.session.commit()
            
            return redirect(url_for('index'))
        except Exception as e:
            
            flash(f'Terjadi kesalahan {e}', 'error')
            return redirect(url_for('register'))
    return render_template('register.html', is_admin_exists=is_admin_exists, users=user, form=form)


# login
# dictionary to store login attempts
login_attempts = {}

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    wait_time = 5
    if get_session_user_id() is not None:
        return redirect(url_for('index'))
    if request.method == 'POST':
        if '@' in request.form['username_email']:
            email = request.form['username_email']
            user = User.query.filter_by(email=email).first()
        else:
            username = request.form['username_email']
            user = User.query.filter_by(username=username).first()
        
        password = request.form['password']
        
        if password == '':
            flash('Password tidak boleh kosong', 'error')
            return redirect(url_for('login'))
        
        # Cek apakah user ada dan password benar
        if user is None or not user.check_password(password):
            # Jika user tidak ada atau password salah
            # increment login attempts for the user
            if user and user.username:
                if user.username not in login_attempts:
                    login_attempts[user.username] = {'attempts': 1, 'time': datetime.now()}
                else:
                    login_attempts[user.username]['time'] = datetime.now()
                    login_attempts[user.username]['attempts'] += 1
                elapsed_time = datetime.now() - login_attempts[user.username]['time']
                if login_attempts[user.username]['attempts'] >= 3 and elapsed_time < timedelta(seconds=wait_time):
                    latest_attempt = login_attempts[user.username]['time']
                    wait_until = latest_attempt + timedelta(seconds=wait_time)
                    flash(f'Terlalu banyak percobaan login. Silakan coba lagi pada {wait_until} WIB', 'error')
                    return redirect(url_for('login'))
                attemp_left = 3 - login_attempts[user.username]['attempts']
                flash(f'Username atau password salah. {attemp_left} percobaan lagi', 'error')
            else:
                flash(f'Username atau password salah', 'error')
            
            return redirect(url_for('login'))
        else:
            if user.username in login_attempts:
                elapsed_time = datetime.now() - login_attempts[user.username]['time']
                if elapsed_time > timedelta(seconds=wait_time):
                    del login_attempts[user.username]
                else:
                    latest_attempt = login_attempts[user.username]['time']
                    wait_until = latest_attempt + timedelta(seconds=wait_time)
                    flash(f'Terlalu banyak percobaan login. Silakan coba lagi pada {wait_until} WIB', 'error')
                    return redirect(url_for('login'))
            # Jika user dan password benar
            # Simpan user ke session
            # encrypt user_id key and value
            # if remember me is checked, set session timeout to 1 day
            encrypted_ = encrypt_session_value(app.secret_key)
            session[encrypted_] = encrypt_session_value(str(user.id))
            
            # reset login attempts for the user
            if user and user.username in login_attempts:
                del login_attempts[user.username]
            
            return redirect(url_for('index'))
    
    return render_template('login.html', form=form)

# logout
@app.route('/logout')
def logout():
    # Hapus user dari session
    session.clear()
    return redirect(url_for('index'))

