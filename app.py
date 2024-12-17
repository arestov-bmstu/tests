from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired, Length
from wtforms.ext.sqlalchemy.orm import FileAllowed
from werkzeug.exceptions import abort
from models import db, User, Test, Question, Answer
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()  # Создаем таблицы в базе данных

# Формы для обработки данных
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CreateTestForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    questions = TextAreaField('Questions (one per line)', validators=[DataRequired()])
    submit = SubmitField('Create Test')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None:
            new_user = User(username=form.username.data)
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Account created for {form.username.data}!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists.', 'danger')
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None and user.check_password(form.password.data):
            flash('You have been logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html', form=form)

@app.route('/create-test', methods=['GET', 'POST'])
def create_test():
    form = CreateTestForm()
    if form.validate_on_submit():
        new_test = Test(title=form.title.data)
        db.session.add(new_test)
        db.session.flush()  # Получаем ID нового теста до коммита
        questions = form.questions.data.split('\n')
        for q in questions:
            new_question = Question(text=q.strip(), test=new_test)
            db.session.add(new_question)
        db.session.commit()
        flash('Test has been created!', 'success')
        return redirect(url_for('assign_test'))
    return render_template('create_test.html', form=form)

@app.route('/assign-test/<int:test_id>', methods=['GET', 'POST'])
def assign_test(test_id):
    test = Test.query.get_or_404(test_id)
    users = User.query.all()
    if request.method == 'POST':
        selected_users = request.form.getlist('users')
        for user_id in selected_users:
            user = User.query.get(user_id)
            for question in test.questions:
                answer = Answer(user=user, question=question)
                db.session.add(answer)
        db.session.commit()
        flash('Test assigned to selected users.', 'success')
        return redirect(url_for('index'))
    return render_template('assign_test.html', test=test, users=users)

@app.route('/take-test/<int:answer_id>', methods=['GET', 'POST'])
def take_test(answer_id):
    answer = Answer.query.get_or_404(answer_id)
    if request.method == 'POST':
        answer.answer_text = request.form['answer']
        db.session.commit()
        flash('Your answer has been saved.', 'success')
        return redirect(url_for('index'))
    return render_template('take_test.html', answer=answer)

if __name__ == '__main__':
    app.run(debug=True)


@app.route('/upload-json', methods=['GET', 'POST'])
def upload_json():
    form = UploadJSONForm()
    if form.validate_on_submit():
        file = form.file.data
        data = json.load(file)
        test = Test(title=data['title'], json_data=json.dumps(data))
        db.session.add(test)
        db.session.commit()
        flash('JSON uploaded successfully!', 'success')
        return redirect(url_for('view_tests'))
    return render_template('upload_json.html', form=form)

@app.route('/tests')
def view_tests():
    tests = Test.query.all()
    return render_template('tests.html', tests=tests)

@app.route('/test/<int:test_id>')
def view_test(test_id):
    test = Test.query.get_or_404(test_id)
    data = json.loads(test.json_data)
    return render_template('test.html', test=data)