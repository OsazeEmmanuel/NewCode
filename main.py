import datetime

from flask import Flask, redirect, request, render_template, flash, url_for
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask_migrate import Migrate



app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///vet.db'
app.config["SECRET_KEY"] = 'Austin200*556'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
migrate = Migrate(app, db)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

class Doctors(db.Model):
    __tablename__ = 'doctors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    file = db.Column(db.String(200), nullable=False)

    __table_args__ = (
        UniqueConstraint('email', name='uq_doctors_email'),
    )


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    # message = db.Column(db.Text(), nullable=False)

    __table_args__ = (
        UniqueConstraint('email', name='uq_users_email'),
    )
def formatted_now():
    now = datetime.now(timezone.utc)
    return now.replace(second=0, microsecond=0)

class UserMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # user = db.Column(db.relationship(User), backref="name")
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime(timezone=True), nullable=False, default=formatted_now)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name_appointment = db.relationship('User', backref='user', lazy=True)

with app.app_context():
    db.create_all()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Routes
@app.route('/doctor-register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form["email"]
        address = request.form["address"]
        password = request.form['password']
        confirm_password = request.form["confirm_password"]
        if password != confirm_password:
            flash("Passwords don't match.")
            return redirect(url_for("doctor_register"))
        hashed_password = generate_password_hash(password, method="scrypt", salt_length=8)
        file = request.files['image']
        if db.session.execute(db.select(Doctors).where(Doctors.email==email)).scalar():
            flash("Account for this email already exist")
            return redirect(url_for("doctor_register"))
        elif file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            doctor = Doctors(name=name, email=email, address=address, password=hashed_password, file=filename)
            db.session.add(doctor)
            db.session.commit()
            return redirect(url_for("doctors"))
    return render_template('doctor-register.html')


@app.route("/user-register", methods=["POST", "GET"])
def user_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form["email"]
        address = request.form["address"]
        password = request.form['password']
        confirm_password = request.form["confirm_password"]
        if password != confirm_password:
            flash("Passwords don't match.")
            return redirect(url_for("user_register"))
        hashed_password = generate_password_hash(password, "scrypt", salt_length=4)
        user = db.session.execute(db.select(User).where(User.email==email)).scalar()
        if user:
            flash("Account for this email already exist")
            return redirect(url_for("user_register"))
        else:
            new_user = User(name=name, email=email, address=address, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("You've successfully registered")
            return redirect(url_for("user_login"))
    return render_template("user-register.html")


@app.route("/user-login", methods=["POST", "GET"])
def user_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = db.session.execute(db.select(User).where(User.email==email)).scalar()
        if not user:
            return "account for this email does not exist"
        elif not check_password_hash(user.password, password):
            return "Password is incorrect"
        else:
            login_user(user)
            return redirect(url_for('doctors'))
    return render_template("user-login.html")


@app.route("/doctor-login", methods=["POST", "GET"])
def doctor_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        doctor = db.session.execute(db.select(Doctors).where(Doctors.email==email)).scalar()
        if not doctor:
            return "Hello Doc, you are not registered as a vet doctor on our platform"
        elif not check_password_hash(doctor.password, password):
            return "Hello Doc, your password is incorrect"
        else:
            login_user(doctor)
            return redirect(url_for('doctors'))
    return render_template("doctor-login.html")

@app.route("/", methods=["POST", "GET"])
@app.route("/home", methods=["POST", "GET"])
def landing_page():
    return render_template("landing.html")


@app.route("/doctors", methods=["POST", "GET"])
def doctors():
    # users = db.session.execute(db.select(Doctors)).scalars()
    page = request.args.get('page', 1, type=int)
    users = Doctors.query.paginate(page=page, per_page=3)
    return render_template("doctors.html", users=users)


@app.route("/doctor-profile/<int:id>", methods=["POST", "GET"])
def doctor_profile(id):
    doctors = db.session.execute(db.select(Doctors).where(Doctors.id == id).scalar())
    return render_template("doctor-profile.html", doctors=doctors)


@app.route("/logout", methods=["POST", "GET"])
def logout():
    logout_user()
    return redirect(url_for("landing_page"))


@app.route("/appointment", methods=["POST", "GET"])
def appointment():
    if request.method == "POST":
        message = request.form["message"]
        user_id = current_user.id
        # date = datetime.datetime.now()
        user_message = UserMessage(message=message, user_id=user_id)
        db.session.add(user_message)
        db.session.commit()
    return render_template("appointment.html")


@app.route("/contact", methods=["POST", "GET"])
def contact():
    return render_template("phonevet.html")


@app.route("/received-messages", methods=["POST", "GET"])
def received_messages():
    messages = db.session.execute(db.select(UserMessage)).scalars()
    users = db.session.execute(db.select(User)).scalars()
    return render_template("received_messages.html", messages=messages, users=users)

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)