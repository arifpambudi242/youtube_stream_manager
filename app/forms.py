from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, HiddenField, SubmitField, FileField
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
    deskripsi = TextAreaField('Deskripsi', validators=[DataRequired(), Length(min=4, max=500)])
    # file upload field for video
    file = FileField('Video', validators=[DataRequired()])
    submit = SubmitField('Submit')