from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import Config
# csrf
from flask_wtf.csrf import CSRFProtect

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

