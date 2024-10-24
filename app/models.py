from app import db
from datetime import datetime
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    is_admin = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Hash password dan simpan ke password_hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Cek password yang diinput dengan hash yang tersimpan"""
        return check_password_hash(self.password_hash, password)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(150), nullable=False)
    deskripsi = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('videos', lazy=True))

    def __repr__(self):
        return f'<Video {self.judul}>'

class Streams(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(150), nullable=False)
    deskripsi = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('streams', lazy=True))

    def __repr__(self):
        return f'<Streams {self.judul}>'

def seed():
    # Check if users table is empty
    if User.query.count() == 0:
        # Create some users
        user1 = User(username='admin', email='admin@email.com', is_admin=True)
        user1.set_password('adminpassword')

        user2 = User(username='user1', email='user1@email.com', is_admin=False)
        user2.set_password('user1password')

        user3 = User(username='user2', email='user2@email.com', is_admin=False)
        user3.set_password('user2password')

        # Add the users to the session
        db.session.add_all([user1, user2, user3])
        db.session.commit()

        print('Database seeded with users!')
    else:
        print('Users table is not empty. Skipping seed.')
