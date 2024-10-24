import os, dotenv

dotenv.load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret_key_for_development'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///cat_cpns.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
