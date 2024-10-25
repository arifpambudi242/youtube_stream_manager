from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import Config
from .bot import *
# csrf
from flask_wtf.csrf import CSRFProtect
import os

# Inisialisasi Flask
app = Flask(__name__)
app.config.from_object(Config)
# Inisialisasi SQLAlchemy dan Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# seed

# csrf
csrf = CSRFProtect(app)
from app import routes, models
# if static files are not served make dir static
if not os.path.exists('app/static/'):
    os.makedirs('app/static')
# generate index.html for the first time with body text forbidden
if not os.path.exists('app/static/index.html'):
    with open('app/static/index.html', 'w') as f:
        f.write('Forbidden')

# if static/videos are not served make dir static/videos
if not os.path.exists('app/static/videos'):
    os.makedirs('app/static/videos')

if not os.path.exists('app/static/videos/index.html'):
    with open('app/static/videos/index.html', 'w') as f:
        f.write('Forbidden')