# __init__.py
import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import Config
from .bot import *
from flask_wtf.csrf import CSRFProtect
import os
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler


# Inisialisasi Flask
app = Flask(__name__)
app.config.from_object(Config)

# Inisialisasi SQLAlchemy dan Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Inisialisasi SocketIO
socketio = SocketIO(app, async_mode='eventlet')

# Inisialisasi scheduler untuk background task
scheduler = BackgroundScheduler()

# Inisialisasi CSRF
csrf = CSRFProtect(app)

# Variabel global untuk background task
background_thread = None
thread_running = False

# Impor routes dan models
from app import routes, models

# Setup direktori statis
if not os.path.exists('app/static/'):
    os.makedirs('app/static')
if not os.path.exists('app/static/index.html'):
    with open('app/static/index.html', 'w') as f:
        f.write('Forbidden')
if not os.path.exists('app/static/videos'):
    os.makedirs('app/static/videos')
if not os.path.exists('app/static/videos/index.html'):
    with open('app/static/videos/index.html', 'w') as f:
        f.write('Forbidden')
