from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Instantiate SQLAlchemy here and call db.init_app(app) from application startup.
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_seller = db.Column(db.Boolean, default=False)
    business_name = db.Column(db.String(255))
    seller_description = db.Column(db.Text)
    rating = db.Column(db.Float, default=0.0)
    total_sales = db.Column(db.Integer, default=0)
    logo_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    products = db.relationship('Product', back_populates='seller', lazy='dynamic')
    orders = db.relationship('Order', back_populates='buyer', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.username}>"


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.BigInteger)
    image_url = db.Column(db.String(1024))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    rating = db.Column(db.Float, default=0.0)

    seller = db.relationship('User', back_populates='products')
    category = db.relationship('Category', back_populates='products')

    order_items = db.relationship('OrderItem', back_populates='product', lazy='dynamic')

    def __repr__(self):
        return f"<Product {self.title}>"


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    slug = db.Column(db.String(255), unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('Product', back_populates='category', lazy='dynamic')

    def __repr__(self):
        return f"<Category {self.name}>"


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    buyer_name = db.Column(db.String(255))
    buyer_email = db.Column(db.String(255))
    shipping_address = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    total = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship('User', back_populates='orders')
    items = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f"<Order {self.id} (buyer={self.buyer_id})>"


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    order = db.relationship('Order', back_populates='items')
    product = db.relationship('Product', back_populates='order_items')

    def __repr__(self):
        return f"<OrderItem order={self.order_id} product={self.product_id} qty={self.quantity}>"


class Address(db.Model):
    __tablename__ = 'addresses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    label = db.Column(db.String(100))
    address_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

    def __repr__(self):
        return f"<Address {self.id} for user {self.user_id}>"


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(255))
    body = db.Column(db.Text)
    rating = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')
    author = db.relationship('User')

    def __repr__(self):
        return f"<Review {self.id} product={self.product_id} rating={self.rating}>"


class SellerApplication(db.Model):
    __tablename__ = 'seller_applications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    business_name = db.Column(db.String(255))
    seller_description = db.Column(db.Text)
    logo_url = db.Column(db.String(1024))
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

    def __repr__(self):
        return f"<SellerApplication {self.id} user={self.user_id}>"


class SellerMessage(db.Model):
    __tablename__ = 'seller_messages'
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    sender_name = db.Column(db.String(255))
    sender_email = db.Column(db.String(255))
    subject = db.Column(db.String(255))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    seller = db.relationship('User')

    def __repr__(self):
        return f"<SellerMessage {self.id} to seller={self.seller_id}>"
