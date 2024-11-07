import os
import threading
import time
import re
from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from functools import wraps, lru_cache
from app import *
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from app.forms import *
from app.models import *
key = None

background_thread = None
thread_running = False
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
    with app.app_context():
        session_key = session.keys()
        
        for key_ in session_key:
            try:
                valid_key = key_
                user_id = decrypt_session_value(session[key_])
                if len(user_id) > 100:  # Limit the length of user_id to 100 characters
                    continue
            except:
                continue 
            if decrypt_session_value(key_) == app.secret_key:
                return int(user_id)
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        with app.app_context():    
            if get_session_user_id() is None:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
    return decorated_function    

def login_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        with app.app_context():
            user_id = get_session_user_id()
            if user_id is None:
                return redirect(url_for('login'))
            user = User.query.get(user_id)
            if not user.is_admin:
                return redirect(url_for('index'))
            return f(*args, **kwargs)
    return decorated_function

def subscription_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        with app.app_context():
            user_id = get_session_user_id()
            if user_id is None:
                return redirect(url_for('login'))
            sub = Subscription.query.filter_by(user_id=user_id, is_active=True).first()
            if not sub and not User.query.get(user_id).is_admin:
                message = 'Anda belum berlangganan' if is_indonesian_ip() else 'You are not subscribed'
                flash(message, 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
    return decorated_function

def disabled_function(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        message = 'Fitur ini sedang dinonaktifkan' if is_indonesian_ip() else 'This feature is disabled'
        # Redirect to referrer if available, else to index
        flash(message, 'error')
        return redirect(request.referrer or url_for('index'))
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
    is_indonesia = is_indonesian_ip()
    if key:
        try:
            user_id = get_session_user_id()
            if user_id:
                user = User.query.get(user_id)
                ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                ip = ip.split(',')[0] if ',' in ip else ip
            else:
                user = BlankUser()
        except:
            pass
    return dict(user=user, is_admin=user.is_admin if user else False, is_indonesia=is_indonesia)

@app.route('/')
def index():
    return render_template('index.html')

# GET /favicon.ico
@app.route('/favicon.ico')
def favicon():
    # static/img/logo.ico
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

def is_indonesian_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ip = ip.split(',')[0] if ',' in ip else ip
    
    try:
        ip_info = get_ip_info(ip)
        if ip_info:
            return ip_info['country_code'] == 'ID'
    except:
        return False

# Validate IP
def is_valid_ip(ip):
    ipv4_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
    return re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip)

# Cache the IP info function to minimize external requests
@lru_cache(maxsize=1000)
def get_ip_info(ip):
    response = requests.get(f"https://ipapi.co/{ip}/json/")
    return response.json() if response.status_code == 200 else None


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    user = {'username': '', 'email': ''}
    is_admin_exists = User.query.filter_by(is_admin=True).first()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            user = {'username': username, 'email': email}
            if username == '':
                message = 'Username tidak boleh kosong' if is_indonesian_ip() else 'Username must not be empty'
                flash(message, 'error')
                return redirect(url_for('register'))
            

            if password == '':
                message = 'Password tidak boleh kosong' if is_indonesian_ip() else 'Password must not be empty'
                flash(message, 'error')
                return redirect(url_for('register'))
            
            if confirm_password == '':
                message = 'Konfirmasi password tidak boleh kosong' if is_indonesian_ip() else 'Confirm password must not be empty'
                flash(message, 'error')
                return redirect(url_for('register'))

            
            # check if username already exists
            if User.query.filter_by(username=username).first():
                message = 'Username sudah ada' if is_indonesian_ip() else 'Username already exists'
                flash(message, 'error')
            # check if email already exists
            if User.query.filter_by(email=email).first():
                message = 'Email sudah ada' if is_indonesian_ip() else 'Email already exists'
                flash(message, 'error')
            
            if password != confirm_password:
                message = 'Password dan konfirmasi password tidak sama' if is_indonesian_ip() else 'Password and confirm password must be the same'
                flash(message, 'error')
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
            
            flash(f'Gagal mendaftar {e}', 'error') if is_indonesian_ip() else flash(f'Failed to register {e}', 'error')
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
    if request.method == 'POST' and form.validate_on_submit():
        if '@' in request.form['username_email']:
            email = request.form['username_email']
            user = User.query.filter_by(email=email).first()
        else:
            username = request.form['username_email']
            user = User.query.filter_by(username=username).first()
        
        if user:
            if not user.is_active:
                flash('User Belum aktif', 'error') if is_indonesian_ip() else flash('User is not active', 'error')
                return redirect(url_for('login'))
        else:
            flash('Username atau email tidak ditemukan', 'error') if is_indonesian_ip() else flash('Username or email not found', 'error')
            return redirect(url_for('login'))
        
        password = request.form['password']
        
        if password == '':
            flash('Password tidak boleh kosong', 'error') if is_indonesian_ip() else flash('Password must not be empty', 'error')
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
                    flash(f'Terlalu banyak percobaan login. Silakan coba lagi nanti', 'error') if is_indonesian_ip() else flash(f'Too many login attempts. Please try again later', 'error')
                    return redirect(url_for('login'))
                attemp_left = 3 - login_attempts[user.username]['attempts']
                flash(f'Username atau password salah. {attemp_left} percobaan lagi', 'error') if is_indonesian_ip() else flash(f'Username or password is wrong. {attemp_left} more attempts', 'error')
            else:
                flash(f'Username atau password salah', 'error') if is_indonesian_ip() else flash(f'Username or password is wrong', 'error')
            
            return redirect(url_for('login'))
        else:
            if user.username in login_attempts:
                elapsed_time = datetime.now() - login_attempts[user.username]['time']
                if elapsed_time > timedelta(seconds=wait_time):
                    del login_attempts[user.username]
                else:
                    latest_attempt = login_attempts[user.username]['time']
                    wait_until = latest_attempt + timedelta(seconds=wait_time)
                    flash(f'Terlalu banyak percobaan login. Silakan coba lagi nanti', 'error') if is_indonesian_ip() else flash(f'Too many login attempts. Please try again later', 'error')
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

@app.route('/authorize/')
@login_required
@subscription_required
def authorize():
    user_id = get_session_user_id()
    user = User.query.filter_by(id=user_id, is_active=True).first()
    oauth = Oauth2Credentials.query.filter_by(user_id=user_id).first()
    if user:
        if oauth:
            flash('User sudah diotorisasi', 'error') if is_indonesian_ip() else flash('User already authorized', 'error')
            # redirect to referrer if available, else to index
            return redirect(request.referrer or url_for('index'))
        
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES)

        flow.redirect_uri = url_for('oauth2callback', _external=True)

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true')

        return redirect(authorization_url)
    else:
        flash('User tidak ditemukan', 'error') if is_indonesian_ip() else flash('User not found', 'error')
        return redirect(url_for('index'))

@app.route('/oauth2callback', methods=['GET'])
@login_required
@subscription_required
def oauth2callback():
    state = request.args.get('state')
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = Oauth2Credentials(
        token=flow.credentials.token,
        refresh_token=flow.credentials.refresh_token,
        token_uri=flow.credentials.token_uri,
        client_id=flow.credentials.client_id,
        client_secret=flow.credentials.client_secret,
        scopes=','.join(flow.credentials.scopes),
        user_id=get_session_user_id()
    )
    db.session.add(credentials)
    try:
        db.session.commit()
        flash('Berhasil mengotorisasi', 'success') if is_indonesian_ip() else flash('Successfully authorized', 'success')
    except Exception as e:
        flash(f'Gagal mengotorisasi {e}', 'error') if is_indonesian_ip() else flash(f'Failed to authorize {e}', 'error')
    
    # ubah is_use_api menjadi True
    user = User.query.filter_by(id=get_session_user_id()).first()
    user.is_use_api = True
    db.session.commit()
    # redirect to referrer if available, else to index
    return redirect(request.referrer or url_for('streams'))

# revoke
@app.route('/revoke')
@login_required
@subscription_required
def revoke():
    user_id = get_session_user_id()
    oauth = Oauth2Credentials.query.filter_by(user_id=user_id).first()
    if oauth:
        try:
            response = requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': oauth.token},
                headers={'content-type': 'application/x-www-form-urlencoded'}
            )
            if response.status_code == 200:
                # Jika status_code 200, hapus data oauth dari database
                db.session.delete(oauth)
                db.session.commit()
                
                user = User.query.filter_by(id=user_id).first()
                user.is_use_api = False
                db.session.commit()
                
                # Pesan sukses berdasarkan bahasa pengguna
                message = 'Berhasil me-revoke akses' if is_indonesian_ip() else 'Successfully revoked access'
                return jsonify({'status': 'success', 'message': message}), 200
            else:
                # Jika gagal me-revoke (status_code bukan 200)
                message = 'Gagal me-revoke akses' if is_indonesian_ip() else 'Failed to revoke access'
                return jsonify({'status': 'error', 'message': message}), 400
        except Exception as e:
            # line 
            import traceback
            traceback.print_exc()
            line = traceback.format_exc().splitlines()[-1]

            # Jika terjadi kesalahan pada saat mencoba me-revoke
            message = 'Gagal me-revoke akses error pada baris ' + line if is_indonesian_ip() else 'Failed to revoke access error on line ' + line
            return jsonify({'status': 'error', 'message': message}), 400
    else:
        # Jika tidak ada oauth, update status user tanpa revoke
        user = User.query.filter_by(id=user_id).first()
        user.is_use_api = False
        db.session.commit()
        
        # Pesan sukses untuk user yang sudah direvoke
        message = 'User sudah direvoke' if is_indonesian_ip() else 'User already revoked'
        return jsonify({'status': 'success', 'message': message}), 200

    


# logout
@app.route('/logout')
def logout():
    # Hapus user dari session
    session.clear()
    flash('Berhasil logout', 'success') if is_indonesian_ip() else flash('Successfully logout', 'success')
    return redirect(url_for('index'))


# videos
@app.route('/videos', methods=['GET', 'POST'])
@login_required
@subscription_required
def videos():
    form = VideoForm()
    user = User.query.get(get_session_user_id())
    if user.is_admin:
        videos = Videos.query.all()
    else:
        videos = Videos.query.filter_by(user_id=get_session_user_id()).all()
    if request.method == 'POST':
        judul = request.form['judul']
        deskripsi = request.form['deskripsi']
        file = request.files['file']
        allowed_extensions = ['mp4', 'mkv', 'avi', 'mov', 'flv', 'wmv']
        if judul == '':
            flash('Judul tidak boleh kosong', 'error') if is_indonesian_ip() else flash('Title must not be empty', 'error')
            return redirect(url_for('videos'))
        if deskripsi == '':
            flash('Deskripsi tidak boleh kosong', 'error') if is_indonesian_ip() else flash('Description must not be empty', 'error')
            return redirect(url_for('videos'))
        if file.filename == '':
            flash('File tidak boleh kosong', 'error') if is_indonesian_ip() else flash('File must not be empty', 'error')
            return redirect(url_for('videos'))
        if file.filename.split('.')[-1] not in allowed_extensions:
            flash('File harus berupa video', 'error') if is_indonesian_ip() else flash('File must be a video', 'error')
            return redirect(url_for('videos'))
        # save file to static folder
        ext = file.filename.split('.')[-1]
        filename = file.filename.replace(f'.{ext}', '')
        filename = f'{filename}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{ext}'
        path = f'videos/{filename}'
        file.save(f'app/static/{path}')
        video = Videos(judul=judul, deskripsi=deskripsi, path=path, user_id=get_session_user_id())
        db.session.add(video)
        db.session.commit()
        flash('Video berhasil diupload', 'success') if is_indonesian_ip() else flash('Video successfully uploaded', 'success')
        return redirect(url_for('videos'))
    return render_template('videos.html', form=form, videos=videos)

@app.route('/delete_video/<int:id>', methods=['GET'])
@login_required
def delete_video(id):
    video = Videos.query.get(id)
    user_id = int(get_session_user_id())
    user = User.query.get(user_id)
    if video.user_id == user_id or user.is_admin:
        try:
            db.session.delete(video)
            db.session.commit()
        except:
            flash('Gagal menghapus video kemungkinan karena video sedang digunakan', 'error') if is_indonesian_ip() else flash('Failed to delete video possibly because the video is being used', 'error')
            return redirect(url_for('videos'))
        # delete file from static folder
        path = f'app/static/{video.path}'
        if os.path.exists(path):
            os.remove(path)
        flash('Video berhasil dihapus', 'success') if is_indonesian_ip() else flash('Video successfully deleted', 'success')
    else:
        flash('Anda tidak memiliki akses', 'error') if is_indonesian_ip() else flash('You do not have access', 'error')
    return redirect(url_for('videos'))

# edit video
@app.route('/edit_video/<int:id>', methods=['GET', 'POST'])
@login_required
@subscription_required
# @disabled_function
def edit_video(id):
    video = Videos.query.get(id)
    user = User.query.get(get_session_user_id())
    if video.user_id != int(get_session_user_id()) and not user.is_admin:
        flash('Anda tidak memiliki akses', 'error') if is_indonesian_ip() else flash('You do not have access', 'error')
        return redirect(url_for('videos'))
    form = VideoForm()
    if request.method == 'POST':
        judul = request.form['judul']
        deskripsi = request.form['deskripsi']
        file = request.files['file']
        if judul == '':
            flash('Judul tidak boleh kosong', 'error') if is_indonesian_ip() else flash('Title must not be empty', 'error')
            return redirect(url_for('edit_video', id=id))
        if deskripsi == '':
            flash('Deskripsi tidak boleh kosong', 'error') if is_indonesian_ip() else flash('Description must not be empty', 'error')
            return redirect(url_for('edit_video', id=id))
        if file.filename != '':
            old_path = video.path
            ext = file.filename.split('.')[-1]
            filename = file.filename.replace(f'.{ext}', '')
            filename = f'{filename}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{ext}'
            path = f'videos/{filename}'
            file.save(f'app/static/{path}')

            video.path = path
            # delete old file
            path = f'app/static/{old_path}'
            if os.path.exists(path):
                os.remove(path)
        video.judul = judul
        video.deskripsi = deskripsi
        db.session.commit()
        flash('Video berhasil diupdate', 'success') if is_indonesian_ip() else flash('Video successfully updated', 'success')
        return redirect(url_for('edit_video', id=id))
    return render_template('edit_video.html', form=form, video=video)

# streams
@app.route('/streams', methods=['GET', 'POST'])
@login_required
@subscription_required
def streams():
    is_autorisasi = False
    user_id = get_session_user_id()
    oauth = Oauth2Credentials.query.filter_by(user_id=user_id).first()
    if oauth:
        is_autorisasi = True
    form = StreamForm()
    # if user is admin, show all streams
    user = User.query.get(get_session_user_id())
    if user.is_admin:
        streams = Streams.query.all()
        videos = Videos.query.all()
    else:
        streams = Streams.query.filter_by(user_id=get_session_user_id()).all()
        videos = Videos.query.filter_by(user_id=get_session_user_id()).all()
    
    if request.method == 'POST':
        judul = request.form['judul']
        deskripsi = request.form['deskripsi']
        kode_stream = request.form['kode_stream'] if 'kode_stream' in request.form else ''
        start_at = request.form['start_at']
        end_at = request.form['end_at']
        video_id = request.form['video_id']
        is_repeat = request.form.get('is_repeat') == 'y'
        if judul == '':
            message = 'Judul tidak boleh kosong' if is_indonesian_ip() else 'Title must not be empty'
            return jsonify({'status': 'error', 'message': message}), 400
        if deskripsi == '':
            message = 'Deskripsi tidak boleh kosong' if is_indonesian_ip() else 'Description must not be empty'
            return jsonify({'status': 'error', 'message': message}), 400
        if kode_stream == '':
            if not is_autorisasi:
                message = "Kode stream tidak boleh kosong" if is_indonesian_ip() else "Stream code must not be empty"
                return jsonify({'status': 'error', 'message': message}), 400
            else:
                kode_stream = bind_broadcast_and_livestream(judul, deskripsi)

        if Videos.query.get(request.form['video_id']).user_id != int(get_session_user_id()):
            message = 'Anda tidak memiliki akses' if is_indonesian_ip() else 'You do not have access'
        if start_at == '':
            # langsung mulai tanpa delay
            start_at = None
        else:
            # from convert from this format '2024-10-25T13:18' to like time()
            start_at = datetime.strptime(start_at, '%Y-%m-%dT%H:%M')
        if end_at == '':
            end_at = None
        else:
            end_at = datetime.strptime(end_at, '%Y-%m-%dT%H:%M')
        
        if end_at and start_at and end_at < start_at:
            message = 'End at tidak boleh kurang dari start at' if is_indonesian_ip() else 'End at must not be less than start at'
            return jsonify({'status': 'error', 'message': message}), 400
            
        stream = Streams(judul=judul, deskripsi=deskripsi, kode_stream=kode_stream, start_at=start_at, end_at=end_at, is_repeat=is_repeat, user_id=get_session_user_id(), video_id=video_id, pid=None, is_active=False)
        db.session.add(stream)
        db.session.commit()
        
        # flash('Stream berhasil dibuat', 'success') if is_indonesian_ip() else flash('Stream successfully created', 'success')
        message = 'Stream berhasil dibuat' if is_indonesian_ip() else 'Stream successfully created'
        return jsonify({'status': 'success', 'message': message}), 200
    return render_template('streams.html', form=form, streams=streams, videos=videos, is_autorisasi=is_autorisasi)

def bind_broadcast_and_livestream(title, description):
    credentials = Oauth2Credentials.query.filter_by(user_id=get_session_user_id()).first()
    if not credentials:
        return redirect('authorize')
    
    credentials = google.oauth2.credentials.Credentials(
        token=credentials.token,
        refresh_token=credentials.refresh_token,
        token_uri=credentials.token_uri,
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        scopes=SCOPES
    )
    credentials.refresh(google.auth.transport.requests.Request())

    youtube = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    
    # get list latest broadcast
    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'Accept': 'application/json'
    }
    params = {
        'part': 'snippet,contentDetails,status',
        'broadcastStatus': 'all',
        'broadcastType': 'all'
    }
    response = requests.get('https://www.googleapis.com/youtube/v3/liveBroadcasts', headers=headers, params=params).json()
    if response['items']:
        # get latest broadcast
        broadcast_id = response['items'][0]['id']

    # update broadcast
    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        "id": broadcast_id,
        "snippet": {
            "title": title,
            "description": description
        }
    }
    response = requests.put(
        'https://www.googleapis.com/youtube/v3/liveBroadcasts',
        headers=headers,
        json=data
    )
    response = response.json()
    # get stream id
    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'Accept': 'application/json'
    }
    params = {
        'part': 'snippet,contentDetails,status',
        'id': broadcast_id
    }
    response = requests.get('https://www.googleapis.com/youtube/v3/liveBroadcasts', headers=headers, params=params).json()
    stream_id = response['items'][0]['contentDetails']['boundStreamId']
    # update stream
    headers = {
    'Authorization': f'Bearer {credentials.token}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
    }

    params = {
        'part': 'id,snippet,cdn,status',
        'body': {}
    }

    body = {
        "id": stream_id,
        "snippet": {
            "title": title,
            "description": description
        }
    }

    params['body'] = body

    

    response = requests.put(
        'https://www.googleapis.com/youtube/v3/liveStreams',
        headers=headers,
        json=params
    )
    # return stream kode
    print(f'reponse {response.json()}')
    # print(f"response\n\n{response['cdn']['ingestionInfo']['streamName']}\n\n")
    return response['cdn']['ingestionInfo']['streamName']
    
    

# start stream
@app.route('/start_stream/<int:id>', methods=['GET'])
@login_required
@subscription_required
def start_stream(id):
    stream = Streams.query.get(id)
    user = User.query.get(get_session_user_id())
    if stream:
        if stream.user_id == user.id or user.is_admin:
            video = Videos.query.get(stream.video_id)
            if video:
                stream = Streams.query.get(id)
                stream_key = stream.kode_stream
                pid = start_stream_youtube(video.path, stream_key, repeat=stream.is_repeat)
                stream.pid = pid
                stream.start_at = datetime.now()
                stream.end_at = None if stream.end_at is None else stream.end_at + timedelta(seconds=3600)
                stream.is_active = True
                db.session.commit()
                message = 'Stream berhasil dimulai' if is_indonesian_ip() else 'Stream successfully started'
                return jsonify({'status': 'success', 'message': message, 'pid': pid}), 200
            else:
                message = 'Video tidak ditemukan' if is_indonesian_ip() else 'Video not found'
                return jsonify({'status': 'error', 'message': message}), 404
        else:
            message = 'Anda tidak memiliki akses' if is_indonesian_ip() else 'You do not have access'
            return jsonify({'status': 'error', 'message': message}), 403
    else:
        message = 'Stream tidak ditemukan' if is_indonesian_ip() else 'Stream not found'
        return jsonify({'status': 'error', 'message': message}), 404
                        

@app.route('/delete_stream/<int:id>', methods=['GET'])
@login_required
def delete_stream(id):
    stream = Streams.query.get(id)
    user = User.query.get(get_session_user_id())
    if stream.user_id == int(get_session_user_id() or user.is_admin):
        if stream.pid:
            message = 'Stream sedang berjalan' if is_indonesian_ip() else 'Stream is running'
            return jsonify({'status': 'error', 'message': message}), 400
        db.session.delete(stream)
        db.session.commit()
        message = 'Stream berhasil dihapus' if is_indonesian_ip() else 'Stream successfully deleted'
        return jsonify({'status': 'success', 'message': message}), 200
    else:
        message = 'Anda tidak memiliki akses' if is_indonesian_ip() else 'You do not have access'
        return jsonify({'status': 'error', 'message': message}), 403
    


# edit stream
@app.route('/edit_stream/<int:id>', methods=['GET', 'POST'])
@login_required
@subscription_required
# @disabled_function
def edit_stream(id):
    stream = Streams.query.get(id)
    user = User.query.get(get_session_user_id())
    if not user:
        message = 'User tidak ditemukan' if is_indonesian_ip() else 'User not found'
        flash(message, 'error')
        return redirect(url_for('streams'))
    if not user.is_admin:
        if stream.user_id != user.id:
            message = 'Anda tidak memiliki akses' if is_indonesian_ip() else 'You do not have access'
            flash(message, 'error')
    form = StreamForm()
    if user.is_admin:
        videos = Videos.query.all()
    else:
        videos = Videos.query.filter_by(user_id=get_session_user_id()).all()
    if request.method == 'POST':
        judul = request.form['judul']
        deskripsi = request.form['deskripsi']
        kode_stream = request.form['kode_stream']
        start_at = request.form['start_at'] if not stream.is_active else stream.start_at
        end_at = request.form['end_at']
        video_id = request.form['video_id']
        is_repeat = request.form.get('is_repeat') == 'y'
        if judul == '':
            message = 'Judul tidak boleh kosong' if is_indonesian_ip() else 'Title must not be empty'
            flash(message, 'error')
            return redirect(url_for('edit_stream', id=id))
        if deskripsi == '':
            message = 'Deskripsi tidak boleh kosong' if is_indonesian_ip() else 'Description must not be empty'
            flash(message, 'error')
            return redirect(url_for('edit_stream', id=id))
        if kode_stream == '':
            message = 'Kode stream tidak boleh kosong' if is_indonesian_ip() else 'Stream code must not be empty'
            flash(message, 'error')
            return redirect(url_for('edit_stream', id=id))
        if not stream.is_active:
            if start_at == '':
                # langsung mulai tanpa delay
                start_at = None
            else:
                # from convert from this format '2024-10-25T13:18' to like time()
                start_at = datetime.strptime(start_at, '%Y-%m-%dT%H:%M')
        if end_at == '':
            end_at = None
        else:
            end_at = datetime.strptime(end_at, '%Y-%m-%dT%H:%M')
        
        if end_at and start_at and end_at < start_at:
            message = 'End at tidak boleh kurang dari start at' if is_indonesian_ip() else 'End at must not be less than start at'
            flash(message, 'error')
            return redirect(url_for('edit_stream', id=id))
        stream.judul = judul
        stream.deskripsi = deskripsi
        stream.kode_stream = kode_stream
        stream.start_at = start_at if not stream.is_active else stream.start_at
        stream.end_at = end_at
        stream.is_repeat = is_repeat
        stream.video_id = video_id
        db.session.commit()
        message = 'Stream berhasil diupdate' if is_indonesian_ip() else 'Stream successfully updated'
        flash(message, 'success')
        return redirect(url_for('edit_stream', id=id))
    return render_template('edit_stream.html', form=form, stream=stream, videos=videos)



@app.route('/stop_stream/<int:id>', methods=['GET'])
@login_required
def stop_stream(id):
    stream = Streams.query.get(id)
    if stream:
        user = User.query.get(get_session_user_id())
        if stream.user_id == int(get_session_user_id()) or user.is_admin:
            if stream.pid:
                stop_stream_by_pid(stream.pid)
                stream.pid = None
                stream.is_active = False
                db.session.commit()
                message = 'Stream berhasil dihentikan' if is_indonesian_ip() else 'Stream successfully stopped'
                return jsonify({'status': 'success', 'message': message}), 200
            else:
                message = 'Stream tidak sedang berjalan' if is_indonesian_ip() else 'Stream is not running'
                return jsonify({'status': 'error', 'message': message}), 400
        else:
            message = 'Anda tidak memiliki akses' if is_indonesian_ip() else 'You do not have access'
            return jsonify({'status': 'error', 'message': message}), 403
    else:
        message = 'Stream tidak ditemukan' if is_indonesian_ip() else 'Stream not found'
        return jsonify({'status': 'error', 'message': message}), 404


@socketio.on('update_streams')
def update_streams(data):
    streams = Streams.query.all()
    streams = [{'id': stream.id, 'judul': stream.judul, 'deskripsi': stream.deskripsi, 'kode_stream': stream.kode_stream, 'start_at': stream.start_at, 'end_at': stream.end_at, 'is_repeat': stream.is_repeat, 'user_id': stream.user_id, 'video_id': stream.video_id, 'pid': stream.pid, 'duration': stream.duration, 'is_active': stream.is_active} for stream in streams]
    emit('update_streams', {'streams': streams})

def serialize_stream(stream):
    return {
        'id': stream.id,
        'judul': stream.judul,
        'deskripsi': stream.deskripsi,
        'kode_stream': stream.kode_stream,
        'start_at': stream.start_at.isoformat() if stream.start_at else None,
        'end_at': stream.end_at.isoformat() if stream.end_at else None,
        'is_repeat': stream.is_repeat,
        'user_id': stream.user_id,
        'video_id': stream.video_id,
        'pid': stream.pid,
        'duration': str(stream.duration),
        'is_active': stream.is_active
    }


# background_task_socketio function
def background_task_socketio():
    current_duration_change = {}
    current_streams_active_change = {}
    while True:
        time.sleep(1)  # Interval pengecekan
        with app.app_context():
            streams = Streams.query.all()
            for stream in streams:
                if f'{stream.id}' not in current_duration_change:
                    current_duration_change[f'{stream.id}'] = stream.duration
                else:
                    if current_duration_change[f'{stream.id}'] != stream.duration:
                        current_duration_change[f'{stream.id}'] = stream.duration
                        socketio.emit('update_duration', serialize_stream(stream))
                if f'{stream.id}' not in current_streams_active_change:
                    current_streams_active_change[f'{stream.id}'] = stream.is_active
                    socketio.emit('update_streams', serialize_stream(stream))
                else:
                    if current_streams_active_change[f'{stream.id}'] != stream.is_active:
                        current_streams_active_change[f'{stream.id}'] = stream.is_active
                        socketio.emit('update_streams', serialize_stream(stream))  # Emit data jika ada perubahan
                    to_be_deleted = []
                    for key in current_streams_active_change.keys():
                        stream_ = Streams.query.get(int(key))
                        if not stream_:
                            to_be_deleted.append(key)
                            socketio.emit('update_streams', {'user_id': stream.user_id})
                            continue
                    for key in to_be_deleted:
                        del current_streams_active_change[key]
                    # jika tidak ditemukan stream.id pada


# Memulai tugas latar belakang ketika klien terhubung
@socketio.on('connect')
def on_connect():
    global background_thread, thread_running
    if background_thread is None:
        thread_running = True
        background_thread = threading.Thread(target=background_task_socketio)
        background_thread.daemon = True
        background_thread.start()

# Menghentikan tugas latar belakang saat klien disconnect
@socketio.on('disconnect')
def on_disconnect():
    global thread_running
    stop_background_task()

def stop_background_task():
    global thread_running, background_thread
    if thread_running:
        thread_running = False
        background_thread.join()  # Tunggu hingga thread selesai
        background_thread = None

@app.route('/subscriptions', methods=['GET', 'POST'])
@login_required
def subscriptions():
    form = SubscriptionForm()
    user = User.query.get(get_session_user_id())
    if user.is_admin:
        # get all order by updated_at and is_active
        subscriptions = Subscription.query.order_by(Subscription.start_at.desc(), Subscription.is_active.desc()).all()
    else:
        subscriptions = Subscription.query.filter_by(user_id=user.id, is_active=True).all()
    subscription_types = SubscriptionType.query.all()
    if request.method == 'POST':
        if user.is_admin:
            message = 'Admin tidak bisa berlangganan' if is_indonesian_ip() else 'Admin cannot subscribe'
            flash(message, 'error')
            return redirect(url_for('subscriptions'))
        subscription_type_id = request.form['subscription_type_id']
        subscription = Subscription(user_id=get_session_user_id(), subscription_type_id=subscription_type_id, is_active=False)
        db.session.add(subscription)
        db.session.commit()
        message = 'Berhasil berlangganan' if is_indonesian_ip() else 'Successfully subscribe'
        flash(message, 'success')
        return redirect(url_for('subscriptions'))
    return render_template('subscriptions.html', form=form, subscription_types=subscription_types, subscriptions=subscriptions)

@app.route('/delete_subscription/<int:id>', methods=['GET'])
@login_admin_required
def delete_subscription(id):
    subscription = Subscription.query.get(id)
    if subscription:
        if subscription.is_active:
            message = 'Tidak bisa menghapus subscription yang aktif' if is_indonesian_ip() else 'Cannot delete active subscription'
            return jsonify({'status': 'error', 'message': message}), 400
        db.session.delete(subscription)
        db.session.commit()
        message = 'Berhasil menghapus subscription' if is_indonesian_ip() else 'Successfully delete subscription'
        return jsonify({'status': 'success', 'message': message}), 200
    else:
        message = 'Subscription tidak ditemukan' if is_indonesian_ip() else 'Subscription not found'
        return jsonify({'status': 'error', 'message': message}), 404

@app.route('/activate_subscription/<int:id>', methods=['GET'])
@login_admin_required
def activate_subscription(id):
    subscription = Subscription.query.filter_by(id=id).first()
    if subscription:
        subscription.is_active = True
        subscription.start_at = datetime.now()  # Mengatur waktu sekarang sebagai start_at
        
        # Memastikan duration adalah angka yang valid
        duration_days = subscription.subscription_type.duration
        if not isinstance(duration_days, int):
            duration_days = 30
        subscription.end_at = subscription.start_at + timedelta(days=duration_days)
        subscription.duration = timedelta(days=duration_days)
        db.session.commit()
        message = 'Berhasil mengaktifkan subscription' if is_indonesian_ip() else 'Successfully activate subscription'
        return jsonify({'status': 'success', 'message': message, 'end_at': subscription.end_at.isoformat()}), 200
    else:
        message = 'Subscription tidak ditemukan' if is_indonesian_ip() else 'Subscription not found'
        return jsonify({'status': 'error', 'message': message}), 404


@app.route('/deactivate_subscription/<int:id>', methods=['GET'])
@login_admin_required
def deactivate_subscription(id):
    subscription = Subscription.query.filter_by(id=id).first()
    if subscription:
        subscription.is_active = False
        subscription.end_at = datetime.now()
        db.session.commit()
        message = 'Berhasil menonaktifkan subscription' if is_indonesian_ip() else 'Successfully deactivate subscription'
        return jsonify({'status': 'success', 'message': message}), 200
    else:
        message = 'Subscription tidak ditemukan' if is_indonesian_ip() else 'Subscription not found'
        return jsonify({'status': 'error', 'message': message}), 404

@app.route('/users', methods=['GET', 'POST'])
@login_admin_required
def users():
    form = UserForm()
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            if username == '':
                message = 'Username tidak boleh kosong' if is_indonesian_ip() else 'Username must not be empty'
                return jsonify({'status': 'error', 'message': message}), 400
            if email == '':
                message = 'Email tidak boleh kosong' if is_indonesian_ip() else 'Email must not be empty'
                return jsonify({'status': 'error', 'message': message}), 400
            if password == '':
                message = 'Password tidak boleh kosong' if is_indonesian_ip() else 'Password must not be empty'
                return jsonify({'status': 'error', 'message': message}), 400
            if confirm_password == '':
                message = 'Konfirmasi password tidak boleh kosong' if is_indonesian_ip() else 'Password confirmation must not be empty'
                return jsonify({'status': 'error', 'message': message}), 400
            if password != confirm_password:
                message = 'Password dan konfirmasi password tidak sama' if is_indonesian_ip() else 'Password and password confirmation are not the same'
                return jsonify({'status': 'error', 'message': message}), 400
            is_admin = request.form.get('is_admin') == 'y'
            # search username or email in database
            user = User.query.filter_by(username=username).first()
            if user:
                message = 'Username sudah ada' if is_indonesian_ip() else 'Username already exists'
                return jsonify({'status': 'error', 'message': message}), 400
            
            user = User.query.filter_by(email=email).first()
            if user:
                message = 'Email sudah ada' if is_indonesian_ip() else 'Email already exists'
                return jsonify({'status': 'error', 'message': message}), 400
            user = User(username=username, email=email, is_admin=is_admin)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            message = 'Berhasil menambahkan user' if is_indonesian_ip() else 'Successfully add user'
            return jsonify({'status': 'success', 'message': message}), 200

        except Exception as e:
            message = f'Gagal menambahkan user {e}' if is_indonesian_ip() else f'Failed to add user {e}'
            return jsonify({'status': 'error', 'message': message}), 400
    users = User.query.all()
    return render_template('users.html', users=users, form=form)

@app.route('/delete_user/<int:id>', methods=['GET'])
@login_admin_required
def delete_user(id):
    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()
        message = 'Berhasil menghapus user' if is_indonesian_ip() else 'Successfully delete user'
        return jsonify({'status': 'success', 'message': message}), 200
    else:
        message = 'User tidak ditemukan' if is_indonesian_ip() else 'User not found'
        return jsonify({'status': 'error', 'message': message}), 404

@app.route('/edit_user/<int:id>', methods=['GET', 'POST'])
@login_admin_required
def edit_user(id):
    user = User.query.get(id)
    form = UserForm()
    if request.method == 'POST' and form.validate_on_submit():
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if username == '':
            message = 'Username tidak boleh kosong' if is_indonesian_ip() else 'Username must not be empty'
            flash(message, 'error')
            return redirect(url_for('edit_user', id=id))
        if email == '':
            message = 'Email tidak boleh kosong' if is_indonesian_ip() else 'Email must not be empty'
            flash(message, 'error')
            return redirect(url_for('edit_user', id=id))
        if password and password != '':
            if password != confirm_password:
                message = 'Password dan konfirmasi password tidak sama' if is_indonesian_ip() else 'Password and password confirmation are not the same'
                flash(message, 'error')
                return redirect(url_for('edit_user', id=id))
        is_admin = request.form.get('is_admin') == 'y'
        user.username = username
        user.email = email
        user.is_admin = is_admin
        if password:
            user.set_password(password)
        db.session.commit()
        return redirect(url_for('users'))
    return render_template('edit_user.html', form=form, user_=user)

@app.route('/activate_user/<int:id>', methods=['GET'])
@login_admin_required
def activate_user(id):
    user = User.query.get(id)
    if user:
        user.is_active = True
        db.session.commit()
        message = 'Berhasil mengaktifkan user' if is_indonesian_ip() else 'Successfully activate user'
        return jsonify({'status': 'success', 'message': message}), 200

    else:
        message = 'User tidak ditemukan' if is_indonesian_ip() else 'User not found'
        return jsonify({'status': 'error', 'message': message}), 404

@app.route('/deactivate_user/<int:id>', methods=['GET'])
@login_admin_required
def deactivate_user(id):
    if id == get_session_user_id():
        message = 'Tidak bisa menonaktifkan user sendiri' if is_indonesian_ip() else 'Cannot deactivate yourself'
        return jsonify({'status': 'error', 'message': message}), 403
    user = User.query.filter_by(id=id).first()
    if user:
        user.is_active = False
        db.session.commit()
        message = 'Berhasil menonaktifkan user' if is_indonesian_ip() else 'Successfully deactivate user'
        return jsonify({'status': 'success', 'message': message}), 200
    else:
        message = 'User tidak ditemukan' if is_indonesian_ip() else 'User not found'
        return jsonify({'status': 'error', 'message': message}), 404

#  revoke_admin
@app.route('/revoke_admin/<int:id>', methods=['GET'])
@login_admin_required
def revoke_admin(id):
    if id == get_session_user_id():
        message = 'Tidak bisa mencabut hak admin sendiri' if is_indonesian_ip() else 'Cannot revoke yourself as admin'
        return jsonify({'status': 'error', 'message': message}), 403
    user = User.query.filter_by(id=id).first()
    if user:
        user.is_admin = False
        db.session.commit()
        message = 'Berhasil mencabut hak admin user' if is_indonesian_ip() else 'Successfully revoke user as admin'
        return jsonify({'status': 'success', 'message': message}), 200
    else:
        message = 'User tidak ditemukan' if is_indonesian_ip() else 'User not found'
        return jsonify({'status': 'error', 'message': message}), 404

# grant_admin
@app.route('/grant_admin/<int:id>', methods=['GET'])
@login_admin_required
def grant_admin(id):
    user = User.query.filter_by(id=id).first()
    if user:
        user.is_admin = True
        db.session.commit()
        message = 'Berhasil memberikan hak admin user' if is_indonesian_ip() else 'Successfully grant user as admin'
        return jsonify({'status': 'success', 'message': message}), 200
    else:
        message = 'User tidak ditemukan' if is_indonesian_ip() else 'User not found'
        return jsonify({'status': 'error', 'message': message}), 404

# reset_password
@app.route('/reset_password/<int:id>', methods=['GET'])
@login_required
def reset_password(id):
    logged_in_user = User.query.filter_by(id=get_session_user_id()).first()
    user = User.query.filter_by(id=id).first()
    if user:
        if user.id != get_session_user_id() and not logged_in_user.is_admin:
            message = 'Anda tidak memiliki akses' if is_indonesian_ip() else 'You do not have access'
            return jsonify({'status': 'error', 'message': message}), 403
        user.set_password('password')
        db.session.commit()
        message = 'Berhasil mereset password user' if is_indonesian_ip() else 'Successfully reset user password'
        return jsonify({'status': 'success', 'message': message}), 200
    else:
        message = 'User tidak ditemukan' if is_indonesian_ip() else 'User not found'
        return jsonify({'status': 'error', 'message': message}), 404
        

# settings
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = EditUserForm()
    user = User.query.get(get_session_user_id())
    if request.method == 'POST' and form.validate_on_submit():
        username = request.form['username']
        email = request.form['email']
        current_password = request.form['current_password']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if username == '':
            message = 'Username tidak boleh kosong' if is_indonesian_ip() else 'Username must not be empty'
            flash(message, 'error')
            return redirect(url_for('settings'))
        if email == '':
            message = 'Email tidak boleh kosong' if is_indonesian_ip() else 'Email must not be empty'
            flash(message, 'error')
            return redirect(url_for('settings'))
        # if current_password is not empty, then user want to change password
        if current_password and current_password != '':
            if not user.check_password(current_password):
                message = 'Password lama salah' if is_indonesian_ip() else 'Old password is wrong'
                flash(message, 'error')
                return redirect(url_for('settings'))
            
        if password and password != '':
            if password != confirm_password:
                message = 'Password dan konfirmasi password tidak sama' if is_indonesian_ip() else 'Password and password confirmation are not the same'
                flash(message, 'error')
                return redirect(url_for('settings'))
        user.username = username
        user.email = email
        if password:
            user.set_password(password)
        try:
            db.session.commit()
            message = 'Berhasil mengupdate user' if is_indonesian_ip() else 'Successfully update user'
            flash(message, 'success')
            return redirect(url_for('settings'))
        except Exception as e:
            message = f'Gagal mengupdate user {e}' if is_indonesian_ip() else f'Failed to update user {e}'
            flash(message, 'error')
            return redirect(url_for('settings'))
    return render_template('settings.html', form=form)

@app.route('/video/<int:id>', methods=['GET'])
@login_required
def video(id):
    video = Videos.query.filter_by(id=id).first()
    if not video:
        message = 'Video tidak ditemukan' if is_indonesian_ip() else 'Video not found'
        return jsonify({'status': 'error', 'message': message}), 404
    else:
        user = User.query.filter_by(id=video.user_id).first()
        if video.user_id != user.id and not user.is_admin:
            message = 'Anda tidak memiliki akses' if is_indonesian_ip() else 'You do not have access'
            return jsonify({'status': 'error', 'message': message}), 403
        else:
            # return jsonify({'status': 'success', 'video': {'id': video.id, 'judul': video.judul, 'deskripsi': video.deskripsi, 'path': video.path}}), 200
            message = 'Berhasil mendapatkan video' if is_indonesian_ip() else 'Successfully get video'
            return jsonify({'status': 'success', 'message': message, 'video': {'id': video.id, 'judul': video.judul, 'deskripsi': video.deskripsi, 'path': video.path}}), 200