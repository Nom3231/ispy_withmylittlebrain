# All the forms on the site. WTForms checks the fields before we save anything.
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, InputRequired, Length, EqualTo, ValidationError, Email
from app.models import User


def _strip(value):
    # Cut extra spaces so " bob " is saved as "bob"
    if isinstance(value, str):
        return value.strip()
    return value


class RegistrationForm(FlaskForm):
    username = StringField('Username', filters=[_strip], validators=[
        DataRequired(),
        Length(min=3, max=30, message='Username must be between 3 and 30 characters.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        # Stop people picking a name that is already in the database
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('This username is already taken. Please choose another.')


class LoginForm(FlaskForm):
    username = StringField('Username', filters=[_strip], validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class AdminLoginForm(FlaskForm):
    # Same fields as player login, but used on the hidden admin page
    username = StringField('Username', filters=[_strip], validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')


class GuessForm(FlaskForm):
    # InputRequired lets you guess 0. DataRequired treats 0 as empty which is wrong for this game.
    guess = IntegerField('Your Guess', validators=[
        InputRequired(message='Please enter a valid number.')
    ])
    submit = SubmitField('Make Guess')


class FeedbackForm(FlaskForm):
    name = StringField('Your Name', filters=[_strip], validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    email = StringField('Your Email', filters=[_strip], validators=[
        DataRequired(),
        Email(message='Enter a valid email address.'),
        Length(max=120)
    ])
    rating = SelectField('Rating (1-5 Brains)', choices=[
        ('5', '5 - Mind Blowing'),
        ('4', '4 - Very Fun'),
        ('3', '3 - Good Challenge'),
        ('2', '2 - Needs Improvement'),
        ('1', '1 - Not Great')
    ], default='5')
    message = TextAreaField('Feedback & Suggestions', filters=[_strip], validators=[
        DataRequired(),
        Length(min=5, max=2000, message='Message must be between 5 and 2000 characters.')
    ])
    submit = SubmitField('Submit Feedback')


class ContentUpdateForm(FlaskForm):
    # Admin uses this to post news on the home page
    title = StringField('Update Title', filters=[_strip], validators=[DataRequired(), Length(max=150)])
    content = TextAreaField('Content / Announcement', filters=[_strip], validators=[DataRequired()])
    submit = SubmitField('Publish Update')
