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
            if len(user_id) > 100:  # Limit the length of user_id to 100 characters
                continue
        except:
            continue 
        if decrypt_session_value(key_) == app.secret_key:
            return user_id
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


# videos
@app.route('/videos', methods=['GET', 'POST'])
@login_required
def videos():
    form = VideoForm()
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
    if video.user_id == user_id:
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
def edit_video(id):
    video = Videos.query.get(id)
    if video.user_id != int(get_session_user_id()):
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
def streams():
    form = StreamForm()
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
        auto_start = request.form.get('auto_start') == 'y'
        if judul == '':
            flash('Judul tidak boleh kosong', 'error')
            return redirect(url_for('streams'))
        if deskripsi == '':
            flash('Deskripsi tidak boleh kosong', 'error')
            return redirect(url_for('streams'))
        if kode_stream == '':
            flash('Kode stream tidak boleh kosong', 'error')
            return redirect(url_for('streams'))
        if Streams.query.filter_by(kode_stream=kode_stream).first():
            flash('Kode stream sudah ada', 'error')
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
        stream_id = stream.id
        if auto_start:
            # start_stream_youtube
            video = Videos.query.get(video_id)
            if video:
                # start_stream_youtube(video.path, kode_stream, repeat=is_repeat) using thread
                stream = Streams.query.get(stream_id)
                pid = start_stream_youtube(video.path, kode_stream, repeat=is_repeat)
                stream.pid = pid
                db.session.commit()
        
        flash('Stream berhasil dibuat', 'success')
        return redirect(url_for('streams'))
    return render_template('streams.html', form=form, streams=streams, videos=videos)


# stream checker
@app.route('/check_stream/<stream_key>', methods=['GET'])
@login_required
def check_stream(stream_key):
    stream = Streams.query.filter_by(kode_stream=stream_key).first()
    if stream:
        if stream.user_id == int(get_session_user_id()):
            video = Videos.query.get(stream.video_id)
            if video:
                stream_key = stream.kode_stream
                youtube_rtmp_url = f'rtmp://a.rtmp.youtube.com/live2/{stream_key}'
                stream_url = youtube_rtmp_url
                is_active = check_youtube_stream(stream_url)
                if is_active:
                    stream.is_active = True
                    db.session.commit()
                    jsonify({'status': 'success', 'message': 'Stream is active'}), 200
                else:
                    jsonify({'status': 'failed', 'message': 'Stream is not active'}), 404
                    
        else:
            jsonify({'status': 'failed', 'message': 'Anda tidak memiliki akses'}), 403

# start stream
@app.route('/start_stream/<int:id>', methods=['GET'])
@login_required
def start_stream(id):
    stream = Streams.query.get(id)
    if stream:
        if stream.user_id == int(get_session_user_id()):
            video = Videos.query.get(stream.video_id)
            if video:
                stream_key = stream.kode_stream
                youtube_rtmp_url = f'rtmp://a.rtmp.youtube.com/live2/{stream_key}'
                stream_url = youtube_rtmp_url
                is_active = check_youtube_stream(stream_url)
                if is_active:
                    jsonify({'status': 'failed', 'message': 'Stream is already active'}), 400
                else:
                    try:
                        if stream.start_at:
                            start_at = stream.start_at
                            delay = (start_at - datetime.now()).total_seconds()
                            if delay > 0:
                                pid = start_stream_youtube(video.path, stream.kode_stream, delay=delay, repeat=stream.is_repeat)
                                stream.pid = pid
                                db.session.commit()
                            else:
                                pid = start_stream_youtube(video.path, stream.kode_stream, repeat=stream.is_repeat)
                                stream.pid = pid
                                db.session.commit()
                        else:
                            pid = start_stream_youtube(video.path, stream.kode_stream, repeat=stream.is_repeat)
                            stream.pid = pid
                            db.session.commit()
                        jsonify({'status': 'success', 'message': 'Stream started'}), 200
                    except Exception as e:
                        jsonify({'status': 'failed', 'message': f'Failed to start stream: {e}'}), 500
            else:
                jsonify({'status': 'failed', 'message': 'Video not found'}), 404
        else:
            jsonify({'status': 'failed', 'message': 'Anda tidak memiliki akses'}), 403
    else:
        jsonify({'status': 'failed', 'message': 'Stream not found'}), 404
                        

@app.route('/delete_stream/<int:id>', methods=['GET'])
@login_required
def delete_stream(id):
    stream = Streams.query.get(id)
    if stream.user_id == int(get_session_user_id()):
        if stream.pid:
            stop_stream_by_pid(stream.pid)
        db.session.delete(stream)
        db.session.commit()
        flash('Stream berhasil dihapus', 'success')
    else:
        flash('Anda tidak memiliki akses', 'error')
    return redirect(url_for('streams'))

# edit stream
@app.route('/edit_stream/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_stream(id):
    stream = Streams.query.get(id)
    if stream.user_id != int(get_session_user_id()):
        return redirect(url_for('streams'))
    form = StreamForm()
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
        if Streams.query.filter_by(kode_stream=kode_stream).first():
            flash('Kode stream sudah ada', 'error')
            return redirect(url_for('edit_stream', id=id))
        if Videos.query.get(request.form['video_id']).user_id != int(get_session_user_id()):
            flash('Anda tidak memiliki akses', 'error')
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
    return stop_stream(id)