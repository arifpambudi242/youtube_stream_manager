from datetime import datetime
from enum import Enum
from app import *
from werkzeug.security import generate_password_hash, check_password_hash


class SubscriptionType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now())
    is_active = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f'<SubscriptionType {self.name}>'

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('subscriptions', lazy=True))
    subscription_type_id = db.Column(db.Integer, db.ForeignKey('subscription_type.id'), nullable=False)
    subscription_type = db.relationship('SubscriptionType', backref=db.backref('subscriptions', lazy=True))
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f'<Subscription {self.id}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    is_admin = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    is_active = db.Column(db.Boolean, default=False)
    def set_password(self, password):
        """Hash password dan simpan ke password_hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Cek password yang diinput dengan hash yang tersimpan"""
        return check_password_hash(self.password_hash, password)


class Videos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(150), nullable=False)
    deskripsi = db.Column(db.Text, nullable=False)
    path = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('videos', lazy=True))

    def __repr__(self):
        return f'<Video {self.judul}>'

class Streams(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(150), nullable=False)
    deskripsi = db.Column(db.Text, nullable=False)
    kode_stream = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now())
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)
    is_repeat = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('streams', lazy=True))
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    video = db.relationship('Videos', backref=db.backref('streams', lazy=True))
    pid = db.Column(db.Integer)
    # duration from time delta
    duration = db.Column(db.Interval)
    is_active = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f'<Streams {self.judul}>'
    
    def is_started(self):
        return self.pid is not None
    @property
    def end_at_str(self):
        return self.end_at.strftime('%Y-%m-%d %H:%M')
    @property
    def start_at_str(self):
        return self.start_at.strftime('%Y-%m-%d %H:%M')

class Oauth2Credentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('oauth2_credentials', lazy=True))
    token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    token_uri = db.Column(db.Text, nullable=False)
    client_id = db.Column(db.Text, nullable=False)
    client_secret = db.Column(db.Text, nullable=False)
    scopes = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now())
    def __repr__(self):
        return f'<Oauth2Credentials {self.user_id}>'
    
    def to_dict(self):
        return {
            'token': self.token,
            'refresh_token': self.refresh_token,
            'token_uri': self.token_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scopes': self.scopes
        }
    
    @staticmethod
    def from_dict(data):
        return Oauth2Credentials(
            token=data['token'],
            refresh_token=data['refresh_token'],
            token_uri=data['token_uri'],
            client_id=data['client_id'],
            client_secret=data['client_secret'],
            scopes=data['scopes']
        )
    
    def update(self, data):
        self.token = data['token']
        self.refresh_token = data['refresh_token']
        self.token_uri = data['token_uri']
        self.client_id = data['client_id']
        self.client_secret = data['client_secret']
        self.scopes = data['scopes']
        self.updated_at = datetime.now()
    
    def to_credentials(self):
        return google.oauth2.credentials.Credentials(
            token=self.token,
            refresh_token=self.refresh_token,
            token_uri=self.token_uri,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes
        )

def seed():
    # Check if users table is empty
    if User.query.count() == 0:
        # Create some users
        user1 = User(username='admin', email='admin@email.com', is_admin=True, is_active=True)
        user1.set_password('adminpassword')

        user2 = User(username='user1', email='user1@email.com', is_admin=False, is_active=True)
        user2.set_password('user1password')

        user3 = User(username='user2', email='user2@email.com', is_admin=False, is_active=True)
        user3.set_password('user2password')

        # Add the users to the session
        db.session.add_all([user1, user2, user3])
        db.session.commit()

        print('Database seeded with users!')
    else:
        print('Users table is not empty. Skipping seed.')

    # Check if subscription_type table is empty
    if SubscriptionType.query.count() == 0:
        # Create some subscription types
        sub1 = SubscriptionType(name='Basic', price=10000, duration=30)
        sub2 = SubscriptionType(name='Premium', price=20000, duration=30)
        sub3 = SubscriptionType(name='Gold', price=30000, duration=30)

        # Add the subscription types to the session
        db.session.add_all([sub1, sub2, sub3])
        db.session.commit()

        print('Database seeded with subscription types!')
    else:
        print('Subscription types table is not empty. Skipping seed.')

    # Check if subscription table is empty
    if Subscription.query.count() == 0:
        # Create some subscriptions
        sub1 = Subscription(user_id=1, subscription_type_id=1, start_at=datetime.now(), is_active=True)
        sub2 = Subscription(user_id=2, subscription_type_id=2, start_at=datetime.now(), is_active=True)
        sub3 = Subscription(user_id=3, subscription_type_id=3, start_at=datetime.now(), is_active=True)

        # Add the subscriptions to the session
        db.session.add_all([sub1, sub2, sub3])
        db.session.commit()

        print('Database seeded with subscriptions!')
    else:
        print('Subscriptions table is not empty. Skipping seed.')