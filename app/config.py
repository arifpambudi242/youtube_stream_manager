import os, dotenv

dotenv.load_dotenv()

secret_path = os.getenv("SECRET_PATH")
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret_key_for_development'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///db_nya.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.getenv("DEBUG")
