from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, HiddenField, SubmitField, FileField, DateTimeField
from wtforms.validators import DataRequired, Length, Email, EqualTo

# buat form untuk register
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=100)])
    confirm_password = PasswordField('Konfirmasi Password', validators=[DataRequired(), Length(min=8, max=100), EqualTo('password', message='Password harus sesuai')])
    is_admin = BooleanField('Admin')
    submit = SubmitField('Register')

# buat form untuk login
class LoginForm(FlaskForm):
    username_email = StringField('Email/Username', validators=[DataRequired(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=100)])
    submit = SubmitField('Login')

# buat form untuk reset password
class ResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(min=4, max=150)])
    submit = SubmitField('Reset Password')

# buat form untuk videos
class VideoForm(FlaskForm):
    judul = StringField('Judul', validators=[DataRequired(), Length(min=4, max=150)])
    deskripsi = TextAreaField('Deskripsi', default='-', validators=[DataRequired(), Length(min=1, max=500)])
    # file upload field for video
    file = FileField('Video', validators=[], render_kw={"accept": "video/*"})
    submit = SubmitField('Submit')

# buat form untuk streams
'''
class Streams(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(150), nullable=False)
    deskripsi = db.Column(db.Text, nullable=False)
    kode_stream = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('streams', lazy=True))

    def __repr__(self):
        return f'<Streams {self.judul}>'
'''
class StreamForm(FlaskForm):
    judul = StringField('Title', validators=[DataRequired(), Length(min=4, max=150)])
    deskripsi = TextAreaField('Description', default='-', validators=[DataRequired(), Length(min=1, max=500)])
    video_id = SelectField('Video', coerce=int, validators=[DataRequired()])
    kode_stream = StringField('Stream Key')
    start_at = DateTimeField('Start At', format='%Y-%m-%dT%H:%M', render_kw={"type": "datetime-local"})
    end_at = DateTimeField('End At', format='%Y-%m-%dT%H:%M', render_kw={"type": "datetime-local"})
    is_repeat = BooleanField('Repeat?')
    submit = SubmitField('Start Stream')

class SubscriptionForm(FlaskForm):
    subscription_type_id = SelectField('Subscription Type', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Subscribe')

class SubscriptionTypeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=4, max=150)])
    price = StringField('Price', validators=[DataRequired(), Length(min=1, max=10)])
    duration = StringField('Duration', validators=[DataRequired(), Length(min=1, max=10)])
    submit = SubmitField('Add Subscription Type')

class PaymentForm(FlaskForm):   
    subscription_id = HiddenField('Subscription ID', validators=[DataRequired()])
    submit = SubmitField('Pay')

class TopUpForm(FlaskForm):
    nominal = StringField('Nominal', validators=[DataRequired(), Length(min=1, max=10)])
    submit = SubmitField('Top Up')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=100)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=8, max=100), EqualTo('password', message='Passwords must match')])
    is_admin = BooleanField('Admin?')
    submit = SubmitField('Submit')

class EditUserFormAdmin(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(min=4, max=150)])
    is_admin = BooleanField('Admin?')
    submit = SubmitField('Submit')

class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[Length(min=8, max=100)])
    password_confirm = PasswordField('Confirm Password', validators=[EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Submit')