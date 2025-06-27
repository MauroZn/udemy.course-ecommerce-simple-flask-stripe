from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, current_user, LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Email, Length, EqualTo
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
import stripe
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'

stripe.api_key = os.getenv('STRIPE_API_KEY')
YOUR_DOMAIN = 'http://localhost:5000'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///default.db'

app.config['SQLALCHEMY_BINDS'] = {
    'store': 'sqlite:///store.db',
    'users': 'sqlite:///users.db'
}

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)

class Product(db.Model):
    __bind_key__ = 'store'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=True)

class User(UserMixin, db.Model):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(), Length(max=150)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6, max=100)])
    confirm_password = PasswordField('Confirm Password', validators=[
        InputRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(), Length(max=150)])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    products = Product.query.all()
    return render_template("index.html", products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        new_user = User(email=form.email.data, password=form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get("cart", [])
    if product_id not in cart:
        cart.append(product_id)
    session["cart"] = cart
    return redirect(url_for('home'))

@app.route('/remove-from-cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get("cart", [])
    if product_id in cart:
        cart.remove(product_id)
    session["cart"] = cart
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    cart = session.get("cart", [])
    products = Product.query.filter(Product.id.in_(cart)).all()
    total = sum(p.price for p in products)
    return render_template("cart.html", products=products, total=total)

@app.route('/checkout', methods=["GET"])
def checkout():
    cart = session.get("cart", [])
    if not cart:
        return redirect(url_for('home'))

    products = Product.query.filter(Product.id.in_(cart)).all()
    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": product.name},
                "unit_amount": int(product.price * 100),
            },
            "quantity": 1,
        } for product in products
    ]

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=YOUR_DOMAIN + "/success",
        cancel_url=YOUR_DOMAIN + "/cancel",
    )
    return redirect(checkout_session.url, code=303)

@app.route('/success')
def success():
    session["cart"] = []
    return "<h1>Payment successful!</h1><a href='/'>Back to Shop</a>"

@app.route('/cancel')
def cancel():
    return "<h1>Payment canceled.</h1><a href='/cart'>Back to Cart</a>"

if __name__ == "__main__":
    app.run(debug=True)
