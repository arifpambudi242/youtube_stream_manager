import os
import signal
import subprocess
import threading
import time
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from app import *
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from app.forms import *
from app.models import *
import pandas as pd
import io
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
                flash('Anda belum berlangganan', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
    return decorated_function

def disabled_function(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        flash('Fitur ini sedang dinonaktifkan', 'error')
        # Redirect to referrer if available, else to index
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
    if request.method == 'POST' and form.validate_on_submit():
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
    if request.method == 'POST' and form.validate_on_submit():
        if '@' in request.form['username_email']:
            email = request.form['username_email']
            user = User.query.filter_by(email=email).first()
        else:
            username = request.form['username_email']
            user = User.query.filter_by(username=username).first()
        
        if user:
            if not user.is_active:
                flash('User Belum aktif', 'error')
                return redirect(url_for('login'))
        else:
            flash('Username atau email tidak ditemukan', 'error')
            return redirect(url_for('login'))
        
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
            flash('Judul tidak boleh kosong', 'error')
            return redirect(url_for('videos'))
        if deskripsi == '':
            flash('Deskripsi tidak boleh kosong', 'error')
            return redirect(url_for('videos'))
        if file.filename == '':
            flash('File tidak boleh kosong', 'error')
            return redirect(url_for('videos'))
        if file.filename.split('.')[-1] not in allowed_extensions:
            flash('File harus berupa video', 'error')
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
        flash('Video berhasil diupload', 'success')
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
            flash('Gagal menghapus video kemungkinan karena video sedang digunakan', 'error')
            return redirect(url_for('videos'))
        # delete file from static folder
        path = f'app/static/{video.path}'
        if os.path.exists(path):
            os.remove(path)
        flash('Video berhasil dihapus', 'success')
    else:
        flash('Anda tidak memiliki akses', 'error')
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
        flash('Anda tidak memiliki akses', 'error')
        return redirect(url_for('videos'))
    form = VideoForm()
    if request.method == 'POST':
        judul = request.form['judul']
        deskripsi = request.form['deskripsi']
        file = request.files['file']
        if judul == '':
            flash('Judul tidak boleh kosong', 'error')
            return redirect(url_for('edit_video', id=id))
        if deskripsi == '':
            flash('Deskripsi tidak boleh kosong', 'error')
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
        flash('Video berhasil diupdate', 'success')
        return redirect(url_for('edit_video', id=id))
    return render_template('edit_video.html', form=form, video=video)

# streams
@app.route('/streams', methods=['GET', 'POST'])
@login_required
@subscription_required
def streams():
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
        kode_stream = request.form['kode_stream']
        start_at = request.form['start_at']
        end_at = request.form['end_at']
        video_id = request.form['video_id']
        is_repeat = request.form.get('is_repeat') == 'y'
        if judul == '':
            flash('Judul tidak boleh kosong', 'error')
            return redirect(url_for('streams'))
        if deskripsi == '':
            flash('Deskripsi tidak boleh kosong', 'error')
            return redirect(url_for('streams'))
        if kode_stream == '':
            flash('Kode stream tidak boleh kosong', 'error')
            return redirect(url_for('streams'))
        if Videos.query.get(request.form['video_id']).user_id != int(get_session_user_id()):
            flash('Anda tidak memiliki akses', 'error')
            return redirect(url_for('streams'))
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
            
        stream = Streams(judul=judul, deskripsi=deskripsi, kode_stream=kode_stream, start_at=start_at, end_at=end_at, is_repeat=is_repeat, user_id=get_session_user_id(), video_id=video_id, pid=None, is_active=False)
        db.session.add(stream)
        db.session.commit()
        
        flash('Stream berhasil dibuat', 'success')
        return redirect(url_for('streams'))
    return render_template('streams.html', form=form, streams=streams, videos=videos)


# stream checker

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
                stream.is_active = True
                db.session.commit()
                return jsonify({'status': 'success', 'message': 'Stream berhasil dimulai'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Video tidak ditemukan'}), 404
        else:
            return jsonify({'status': 'error', 'message': 'Anda tidak memiliki akses'}), 403
    else:
        return jsonify({'status': 'error', 'message': 'Stream tidak ditemukan'}), 404
                        

@app.route('/delete_stream/<int:id>', methods=['GET'])
@login_required
def delete_stream(id):
    stream = Streams.query.get(id)
    user = User.query.get(get_session_user_id())
    if stream.user_id == int(get_session_user_id() or user.is_admin):
        if stream.pid:
            stop_stream_by_pid(stream.pid)
        db.session.delete(stream)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Stream berhasil dihapus'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Anda tidak memiliki akses'}), 403
    


# edit stream
@app.route('/edit_stream/<int:id>', methods=['GET', 'POST'])
@login_required
@subscription_required
# @disabled_function
def edit_stream(id):
    stream = Streams.query.get(id)
    user = User.query.get(get_session_user_id())
    if not user.is_admin:
        if stream.user_id != user.id:
            flash('Anda tidak memiliki akses', 'error')
            return redirect(url_for('streams'))
    if stream.is_active:
        flash('Stream sedang berjalan', 'error')
        return redirect(url_for('streams'))
    form = StreamForm()
    if user.is_admin:
        videos = Videos.query.all()
    else:
        videos = Videos.query.filter_by(user_id=get_session_user_id()).all()
    if request.method == 'POST':
        judul = request.form['judul']
        deskripsi = request.form['deskripsi']
        kode_stream = request.form['kode_stream']
        start_at = request.form['start_at']
        end_at = request.form['end_at']
        video_id = request.form['video_id']
        is_repeat = request.form.get('is_repeat') == 'y'
        if judul == '':
            flash('Judul tidak boleh kosong', 'error')
            return redirect(url_for('edit_stream', id=id))
        if deskripsi == '':
            flash('Deskripsi tidak boleh kosong', 'error')
            return redirect(url_for('edit_stream', id=id))
        if kode_stream == '':
            flash('Kode stream tidak boleh kosong', 'error')
            return redirect(url_for('edit_stream', id=id))
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
        stream.judul = judul
        stream.deskripsi = deskripsi
        stream.kode_stream = kode_stream
        stream.start_at = start_at
        stream.end_at = end_at
        stream.is_repeat = is_repeat
        stream.video_id = video_id
        db.session.commit()
        flash('Stream berhasil diupdate', 'success')
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
                return jsonify({'status': 'success', 'message': 'Stream berhasil dihentikan'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Stream tidak sedang berjalan'}), 400
        else:
            return jsonify({'status': 'error', 'message': 'Anda tidak memiliki akses'}), 403
    else:
        return jsonify({'status': 'error', 'message': 'Stream tidak ditemukan'}), 404


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
    print("Client connected, background task started")

# Menghentikan tugas latar belakang saat klien disconnect
@socketio.on('disconnect')
def on_disconnect():
    global thread_running
    stop_background_task()
    print("Client disconnected, background task stopped")

def stop_background_task():
    """Hentikan hanya thread latar belakang tanpa menghentikan server"""
    global thread_running, background_thread
    if thread_running:
        thread_running = False
        background_thread.join()  # Tunggu hingga thread selesai
        background_thread = None
        print("Background task stopped")

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
            flash('Admin tidak bisa berlangganan', 'error')
            return redirect(url_for('subscriptions'))
        subscription_type_id = request.form['subscription_type_id']
        subscription = Subscription(user_id=get_session_user_id(), subscription_type_id=subscription_type_id, is_active=False)
        db.session.add(subscription)
        db.session.commit()
        flash('Berhasil berlangganan', 'success')
        return redirect(url_for('subscriptions'))
    return render_template('subscriptions.html', form=form, subscription_types=subscription_types, subscriptions=subscriptions)

@app.route('/delete_subscription/<int:id>', methods=['GET'])
@login_admin_required
def delete_subscription(id):
    subscription = Subscription.query.get(id)
    if subscription:
        if subscription.is_active:
            flash('Tidak bisa menghapus subscription yang aktif', 'error')
            return redirect(url_for('subscriptions'))
        db.session.delete(subscription)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Berhasil menghapus subscription'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Subscription tidak ditemukan'}), 404

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
        return jsonify({'status': 'success', 'message': 'Berhasil mengaktifkan subscription'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Subscription tidak ditemukan'}), 404


@app.route('/deactivate_subscription/<int:id>', methods=['GET'])
@login_admin_required
def deactivate_subscription(id):
    subscription = Subscription.query.filter_by(id=id).first()
    if subscription:
        subscription.is_active = False
        subscription.end_at = datetime.now()
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Berhasil menonaktifkan subscription'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Subscription tidak ditemukan'}), 404

@app.route('/users', methods=['GET', 'POST'])
@login_admin_required
def users():
    form = UserForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            password_confirm = request.form['password_confirm']
            if username == '':
                flash('Username tidak boleh kosong', 'error')
                return redirect(url_for('users'))
            if email == '':
                flash('Email tidak boleh kosong', 'error')
                return redirect(url_for('users'))
            if password == '':
                flash('Password tidak boleh kosong', 'error')
                return redirect(url_for('users'))
            if password_confirm == '':
                flash('Konfirmasi password tidak boleh kosong', 'error')
                return redirect(url_for('users'))
            if password != password_confirm:
                flash('Password dan konfirmasi password tidak sama', 'error')
                return redirect(url_for('users'))
            is_admin = request.form.get('is_admin') == 'y'
            # search username or email in database
            user = User.query.filter_by(username=username).first()
            if user:
                flash('Username sudah ada', 'error')
                return jsonify({'status': 'error', 'message': 'Username sudah ada'}), 400
            user = User.query.filter_by(email=email).first()
            if user:
                flash('Email sudah ada', 'error')
                return jsonify({'status': 'error', 'message': 'Email sudah ada'}), 400
            user = User(username=username, email=email, is_admin=is_admin)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Berhasil menambahkan user'}), 200
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Gagal menambahkan user {e}'}), 400
    users = User.query.all()
    return render_template('users.html', users=users, form=form)

@app.route('/delete_user/<int:id>', methods=['GET'])
@login_admin_required
def delete_user(id):
    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Berhasil menghapus user'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404

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
            flash('Username tidak boleh kosong', 'error')
            return redirect(url_for('edit_user', id=id))
        if email == '':
            flash('Email tidak boleh kosong', 'error')
            return redirect(url_for('edit_user', id=id))
        if password and password != '':
            if password != confirm_password:
                flash('Password dan konfirmasi password tidak sama', 'error')
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
        return jsonify({'status': 'success', 'message': 'Berhasil mengaktifkan user'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404

@app.route('/deactivate_user/<int:id>', methods=['GET'])
@login_admin_required
def deactivate_user(id):
    if id == get_session_user_id():
        return jsonify({'status': 'error', 'message': 'Tidak bisa menonaktifkan user sendiri'}), 403
    user = User.query.filter_by(id=id).first()
    if user:
        user.is_active = False
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Berhasil menonaktifkan user'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404

#  revoke_admin
@app.route('/revoke_admin/<int:id>', methods=['GET'])
@login_admin_required
def revoke_admin(id):
    if id == get_session_user_id():
        return jsonify({'status': 'error', 'message': 'Tidak bisa mencabut hak admin sendiri'}), 403
    user = User.query.filter_by(id=id).first()
    if user:
        user.is_admin = False
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Berhasil mencabut hak admin user'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404

# grant_admin
@app.route('/grant_admin/<int:id>', methods=['GET'])
@login_admin_required
def grant_admin(id):
    user = User.query.filter_by(id=id).first()
    if user:
        user.is_admin = True
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Berhasil memberikan hak admin user'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404

# reset_password
@app.route('/reset_password/<int:id>', methods=['GET'])
@login_required
def reset_password(id):
    logged_in_user = User.query.filter_by(id=get_session_user_id()).first()
    user = User.query.filter_by(id=id).first()
    if user:
        if user.id != get_session_user_id() and not logged_in_user.is_admin:
            return jsonify({'status': 'error', 'message': 'Anda tidak memiliki akses'}), 403
        user.set_password('password')
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Berhasil mereset password user'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404
        

# settings
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = EditUserForm()
    user = User.query.get(get_session_user_id())
    if request.method == 'POST' and form.validate_on_submit():
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        if username == '':
            flash('Username tidak boleh kosong', 'error')
            return redirect(url_for('settings'))
        if email == '':
            flash('Email tidak boleh kosong', 'error')
            return redirect(url_for('settings'))
        if password and password != '':
            if password != password_confirm:
                flash('Password dan konfirmasi password tidak sama', 'error')
                return redirect(url_for('settings'))
        user.username = username
        user.email = email
        if password:
            user.set_password(password)
        try:
            db.session.commit()
            flash('Berhasil mengupdate user', 'success')
        except Exception as e:
            flash(f'Gagal mengupdate user {e}', 'error')
    return render_template('settings.html', form=form)