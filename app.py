from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diet_system.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    is_dietitian = db.Column(db.Boolean, default=False)

    created_diet_plans = db.relationship(
        'DietPlan',
        foreign_keys='DietPlan.dietitian_id',
        backref='assigned_by_dietitian',
        lazy=True
    )
    assigned_diet_plans = db.relationship(
        'DietPlan',
        foreign_keys='DietPlan.user_id',
        backref='assigned_to_user',
        lazy=True
    )
    food_logs = db.relationship('FoodLog', backref='user', lazy=True)

class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class DietPlan(db.Model):
    __tablename__ = 'diet_plan'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dietitian_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_details = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        is_dietitian = request.form.get('is_dietitian') == 'on'

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password=hashed_password, name=name, is_dietitian=is_dietitian)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found with this email. Please register.')
            return redirect(url_for('login'))

        if not check_password_hash(user.password, password):
            flash('Invalid password. Please try again.')
            return redirect(url_for('login'))

        login_user(user)
        if user.is_dietitian:
            return redirect(url_for('dietitian_dashboard'))
        return redirect(url_for('user_dashboard'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.is_dietitian:
        return redirect(url_for('dietitian_dashboard'))
    food_logs = FoodLog.query.filter_by(user_id=current_user.id).order_by(FoodLog.date.desc()).all()
    diet_plan = DietPlan.query.filter_by(user_id=current_user.id).order_by(DietPlan.created_at.desc()).first()
    return render_template('user_dashboard.html', food_logs=food_logs, diet_plan=diet_plan)

@app.route('/dietitian/dashboard')
@login_required
def dietitian_dashboard():
    if not current_user.is_dietitian:
        return redirect(url_for('user_dashboard'))

    users = User.query.filter_by(is_dietitian=False).all()

    for user in users:
        user.diet_plan = DietPlan.query.filter_by(user_id=user.id).order_by(DietPlan.created_at.desc()).first()

    return render_template('dietitian_dashboard.html', users=users)

@app.route('/add_food_log', methods=['POST'])
@login_required
def add_food_log():
    food_name = request.form.get('food_name')
    calories = request.form.get('calories')
    new_log = FoodLog(user_id=current_user.id, food_name=food_name, calories=calories)
    db.session.add(new_log)
    db.session.commit()
    return redirect(url_for('user_dashboard'))

@app.route('/create_diet_plan', methods=['POST'])
@login_required
def create_diet_plan():
    if not current_user.is_dietitian:
        return redirect(url_for('user_dashboard'))
    user_id = request.form.get('user_id')
    plan_details = request.form.get('plan_details')
    new_plan = DietPlan(user_id=user_id, dietitian_id=current_user.id, plan_details=plan_details)
    db.session.add(new_plan)
    db.session.commit()
    return redirect(url_for('dietitian_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
