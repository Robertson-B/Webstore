from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from functools import wraps
import sqlite3
import os
from decimal import Decimal
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash



app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret"

DB_PATH = os.path.join(os.path.dirname(__file__), "webstore.db")

# SQLite INTEGER is signed 64-bit: range is -(2**63) .. 2**63-1
# Protect against Python ints larger than the SQLite C type can hold.
MAX_SQLITE_INT = 2**63 - 1

def get_db_connection(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# Ensure categories table and products.category_id exist on startup (best-effort)
try:
    _conn = get_db_connection()
    ensure_categories_table(_conn)
    _conn.close()
except Exception:
    # If DB isn't yet created or another startup issue occurs, skip; migration will run later when needed
    pass


@app.route('/favicon.ico')
def favicon():
    """Serve the generated favicon.ico for clients that request /favicon.ico directly."""
    favicon_dir = os.path.join(app.root_path, 'static', 'img', 'favicon')
    return send_from_directory(favicon_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Simple contact form: accepts submissions but does not store them.
    We flash a thank-you message and redirect back to the same page.
    """
    if request.method == 'POST':
        # read fields but intentionally do not persist
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        subject = request.form.get('subject','').strip()
        message = request.form.get('message','').strip()
        # we could log or send to an external service here; for now just acknowledge
        flash('Thanks for your message — we will get back to you soon.')
        return redirect(url_for('contact'))
    return render_template('contact.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/privacy')
def privacy():
    """Serve the playful privacy policy page."""
    return render_template('privacy.html')


@app.route('/cookies')
def cookies():
    """Serve the cartoonish cookies policy page."""
    return render_template('cookies.html')


@app.route('/returns')
def returns_policy():
    """Serve the theatrical returns & refunds policy page."""
    return render_template('returns.html')


def ensure_seller_applications_table(conn):
    """Ensure the seller_applications table exists and has the expected columns.
    Adds a `status` column if it's missing to support approve/reject flows.
    """ 
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seller_applications (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            business_name TEXT,
            message TEXT,
            logo_url TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    # ensure `status` column exists (older installs may have a table without it)
    cur.execute("PRAGMA table_info(seller_applications)")
    cols = [r[1] for r in cur.fetchall()]
    # ensure `status` column exists (older installs may have a table without it)
    if 'status' not in cols:
        cur.execute("ALTER TABLE seller_applications ADD COLUMN status TEXT DEFAULT 'pending'")
        conn.commit()
    # ensure seller_description column exists
    if 'seller_description' not in cols:
        cur.execute("ALTER TABLE seller_applications ADD COLUMN seller_description TEXT")
        conn.commit()


def ensure_categories_table(conn):
    """Create categories table if missing and add category_id column to products if needed.
    This is a best-effort, non-destructive migration: category_id is nullable.
    """
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            slug TEXT UNIQUE,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    # ensure products table has category_id column (nullable)
    try:
        cur.execute("PRAGMA table_info(products)")
        cols = [r[1] for r in cur.fetchall()]
        if 'category_id' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN category_id INTEGER")
            conn.commit()
    except Exception:
        # if products table doesn't exist yet or other error, skip quietly
        pass

    # create an index to speed lookups
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id)")
        conn.commit()
    except Exception:
        pass


def ensure_cart():
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']

def cart_total_items_and_amount(cart):
    total_items = 0
    total_amount = Decimal("0.00")
    if not cart:
        return total_items, total_amount
    conn = get_db_connection()
    cur = conn.cursor()
    ids = list(cart.keys())
    placeholders = ",".join("?" for _ in ids)
    cur.execute(f"SELECT id, price FROM products WHERE id IN ({placeholders})", ids)
    rows = {str(r["id"]): Decimal(str(r["price"])) for r in cur.fetchall()}
    conn.close()
    for pid, qty in cart.items():
        total_items += qty
        price = rows.get(str(pid), Decimal("0.00"))
        total_amount += price * qty
    return total_items, total_amount

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_user_permissions():
    """Inject a helper into templates: current_user_is_admin -> True/False
    True if the logged-in user has is_admin flag or matches the special admin username.
    """
    uid = session.get('user_id')
    is_admin_flag = False
    is_seller_flag = False
    if uid:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username, is_admin, is_seller FROM users WHERE id = ?", (uid,))
        u = cur.fetchone()
        conn.close()
        if u:
            allowed_admin_username = 'Bean'
            if (u['username'] and u['username'].strip().lower() == allowed_admin_username.strip().lower()) or u['is_admin']:
                is_admin_flag = True
            # expose seller flag to templates so navbar can show a Seller Dashboard link
            try:
                is_seller_flag = bool(u['is_seller'])
            except Exception:
                is_seller_flag = False
    # resolve a sensible contact URL for the footer: prefer seller_contact, then contact endpoint, else a fallback path
    contact_url = '/contact'
    try:
        if 'seller_contact' in app.view_functions:
            contact_url = url_for('seller_contact')
        elif 'contact' in app.view_functions:
            contact_url = url_for('contact')
    except Exception:
        # fallback to a static path if url_for fails for any reason
        contact_url = '/contact'

    return {
        'current_user_is_admin': is_admin_flag,
        'current_user_is_seller': is_seller_flag,
        'current_year': datetime.now().year,
        'contact_url': contact_url,
    }

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # restrict admin area to a single user account (by username)
        uid = session.get('user_id')
        if not uid:
            return redirect(url_for('login', next=request.path))
        conn = get_db_connection()
        cur = conn.cursor()
        # fetch both username and is_admin flag so toggling is_admin grants access
        cur.execute("SELECT username, is_admin FROM users WHERE id = ?", (uid,))
        u = cur.fetchone()
        conn.close()
        # allow either the special username or any user with is_admin truthy
        allowed_admin_username = 'Bean'
        has_name_match = bool(u and u['username'] and u['username'].strip().lower() == allowed_admin_username.strip().lower())
        has_admin_flag = bool(u and u['is_admin'])
        if not (has_name_match or has_admin_flag):
            flash("Admin access required.")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.title, p.description, p.price, p.stock, p.created_at, p.seller_id, p.image_url, u.business_name, u.rating, u.username AS seller_username
        FROM products p 
        LEFT JOIN users u ON p.seller_id = u.id 
        ORDER BY p.created_at DESC LIMIT 6
    """)
    featured = cur.fetchall()
    conn.close()
    return render_template('index.html', featured_products=featured)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/products')
def products():
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'newest')
    category_filter = request.args.get('category', '').strip()
    conn = get_db_connection()
    cur = conn.cursor()
    base = """
     SELECT p.id, p.title, p.description, p.price, p.created_at, 
         p.stock, p.image_url, u.business_name, u.rating, p.seller_id,
         c.name AS category_name, c.slug AS category_slug
        FROM products p 
        LEFT JOIN users u ON p.seller_id = u.id
        LEFT JOIN categories c ON p.category_id = c.id
    """
    params = []
    where = ""
    if search:
        where = " WHERE p.title LIKE ? OR p.description LIKE ?"
        params.extend([f"%{search}%", f"%{search}%"])
    # category filter can be a slug or an id
    if category_filter:
        if where:
            where += " AND (c.slug = ? OR p.category_id = ?)"
        else:
            where = " WHERE (c.slug = ? OR p.category_id = ?)"
        params.append(category_filter)
        try:
            params.append(int(category_filter))
        except Exception:
            params.append(-1)
    if sort == 'price_low':
        order = " ORDER BY p.price ASC"
    elif sort == 'price_high':
        order = " ORDER BY p.price DESC"
    else:
        order = " ORDER BY p.created_at DESC"
    cur.execute(base + where + order, params)
    products = cur.fetchall()
    conn.close()
    return render_template('products.html', products=products, search=search, sort=sort)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
     SELECT p.id, p.title, p.description, p.price, p.stock, p.image_url,
         u.id AS seller_id, u.business_name, u.seller_description, u.rating,
         c.name AS category_name, c.slug AS category_slug
     FROM products p
     LEFT JOIN users u ON p.seller_id = u.id
     LEFT JOIN categories c ON p.category_id = c.id
     WHERE p.id = ?
    """, (product_id,))
    product = cur.fetchone()
    conn.close()
    if product is None:
        flash("Product not found.")
        return redirect(url_for('products'))
    return render_template('product_detail.html', product=product)


@app.route('/cart')
def cart_view():
    cart = ensure_cart()
    items = []
    if cart:
        conn = get_db_connection()
        cur = conn.cursor()
        for pid, qty in cart.items():
            cur.execute("SELECT id, title, price FROM products WHERE id = ?", (pid,))
            product = cur.fetchone()
            if product:
                items.append({
                    'product': product,
                    'quantity': qty,
                    'line_total': float(product['price']) * qty
                })
        conn.close()
    total_items, total_amount = cart_total_items_and_amount(cart)
    return render_template('cart.html', items=items, total_items=total_items, total_amount=total_amount)

@app.route('/cart/add', methods=['POST'])
def cart_add():
    product_id = request.form.get('product_id')
    qty = int(request.form.get('quantity', 1))
    # ensure product exists and respect stock limits
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, stock FROM products WHERE id = ?", (product_id,))
        prod = cur.fetchone()
    finally:
        conn.close()

    if not prod:
        flash("Product not found.")
        return redirect(request.form.get('next') or url_for('products'))

    # stock == None/NULL means unlimited
    stock = prod['stock']
    cart = ensure_cart()
    cart = dict(cart)
    current = cart.get(product_id, 0)
    add_requested = max(1, qty)
    if stock is not None:
        available = stock - current
        if available <= 0:
            wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json
            if wants_json:
                return jsonify({"ok": False, "error": "Out of stock", "total_items": sum(cart.values())})
            flash("Item is out of stock.")
            return redirect(request.form.get('next') or url_for('cart_view'))
        add_amount = min(add_requested, available)
    else:
        add_amount = add_requested

    cart[product_id] = current + add_amount
    session['cart'] = cart
    total_items, total_amount = cart_total_items_and_amount(cart)
    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json
    if wants_json:
        # include how many were actually added and a helpful message
        msg = None
        if add_amount < add_requested:
            msg = f"Only {add_amount} items were added due to limited stock."
        else:
            msg = "Added to cart."
        return jsonify({
            "ok": True,
            "total_items": total_items,
            "total_amount": float(total_amount),
            "added": add_amount,
            "requested": add_requested,
            "message": msg
        })
    # notify if we could not add full requested amount
    if add_amount < add_requested:
        flash(f"Only {add_amount} items were added due to limited stock.")
    else:
        flash("Added to cart.")
    return redirect(request.form.get('next') or url_for('cart_view'))

@app.route('/cart/summary')
def cart_summary():
    cart = ensure_cart()
    total_items, total_amount = cart_total_items_and_amount(cart)
    return jsonify({"total_items": total_items, "total_amount": float(total_amount)})

@app.route('/cart/update', methods=['POST'])
def cart_update():
    cart = ensure_cart()
    cart = dict(cart)
    # For each qty_<id> field, ensure quantity does not exceed stock
    conn = get_db_connection()
    cur = conn.cursor()
    for pid, qty in request.form.items():
        if not pid.startswith("qty_"):
            continue
        prod_id = pid[4:]
        try:
            q = int(qty)
        except ValueError:
            q = 0
        if q <= 0:
            cart.pop(prod_id, None)
            continue

        # check stock for this product
        cur.execute("SELECT stock FROM products WHERE id = ?", (prod_id,))
        r = cur.fetchone()
        if r and r['stock'] is not None:
            stock = r['stock']
            if q > stock:
                q = stock
                flash(f"Quantity for product {prod_id} reduced to available stock ({stock}).")

        cart[prod_id] = q
    conn.close()
    session['cart'] = cart
    flash("Cart updated.")
    return redirect(url_for('cart_view'))

@app.route('/cart/remove/<int:product_id>', methods=['POST'])
def cart_remove(product_id):
    cart = ensure_cart()
    cart = dict(cart)
    cart.pop(str(product_id), None)
    session['cart'] = cart
    flash("Removed item.")
    return redirect(url_for('cart_view'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        if not username or not email or not password:
            flash("Fill all fields.")
            return redirect(url_for('register'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cur.fetchone():
            conn.close()
            flash("Username or email already taken.")
            return redirect(url_for('register'))
        pw_hash = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, email, password_hash, is_seller) VALUES (?, ?, ?, 0)",
                    (username, email, pw_hash))
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        session['user_id'] = user_id
        session['username'] = username
        flash("Registered and logged in.")
        next_url = request.args.get('next') or url_for('index')
        return redirect(next_url)
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash FROM users WHERE username = ? OR email = ?", (username, username))
        user = cur.fetchone()
        conn.close()
        if not user or not check_password_hash(user['password_hash'], password):
            flash("Invalid credentials.")
            return redirect(url_for('login', next=request.args.get('next')))
        session['user_id'] = user['id']
        session['username'] = user['username']
        flash("Logged in.")
        return redirect(request.args.get('next') or url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash("Logged out.")
    return redirect(url_for('index'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = ensure_cart()
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for('products'))

    conn = get_db_connection()
    cur = conn.cursor()

    # build items list for display and compute total (include stock for checks)
    ids = list(cart.keys())
    placeholders = ",".join("?" for _ in ids)
    cur.execute(f"SELECT id, title, price, stock, seller_id FROM products WHERE id IN ({placeholders})", ids)
    rows = {str(r["id"]): r for r in cur.fetchall()}
    items = []
    total = 0.0
    for pid, qty in cart.items():
        r = rows.get(str(pid))
        if not r:
            continue
        line_total = float(r["price"]) * qty
        items.append({"product": r, "quantity": qty, "line_total": line_total})
        total += line_total

    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        address = request.form.get('address','').strip()
        if not name or not email or not address:
            flash("Please fill all fields.")
            return redirect(url_for('checkout'))

        # re-validate stock for all items before creating order
        insufficient = []
        for pid, qty in cart.items():
            prod = rows.get(str(pid))
            if not prod:
                insufficient.append((pid, 0, qty))
                continue
            stock = prod['stock']
            if stock is not None and stock < qty:
                insufficient.append((pid, stock, qty))
        if insufficient:
            # inform user and redirect back to cart so they can adjust
            msgs = []
            for pid, avail, wanted in insufficient:
                if avail == 0:
                    msgs.append(f"Product {pid} is no longer available.")
                else:
                    msgs.append(f"Product {pid} only has {avail} left (you wanted {wanted}).")
            for m in msgs:
                flash(m)
            conn.close()
            return redirect(url_for('cart_view'))

        # create order
        buyer_id = session.get('user_id')
        cur.execute(
            "INSERT INTO orders (buyer_id, buyer_name, buyer_email, shipping_address, total) VALUES (?, ?, ?, ?, ?)",
            (buyer_id, name, email, address, total)
        )
        order_id = cur.lastrowid

        # save address for user (avoid duplicates due to UNIQUE constraint)
        try:
            if buyer_id:
                cur.execute("INSERT OR IGNORE INTO addresses (user_id, label, address_text) VALUES (?, ?, ?)",
                            (buyer_id, None, address))
        except Exception:
            pass

        # insert order items and reduce stock
        for pid, qty in cart.items():
            prod = rows.get(str(pid))
            if not prod:
                continue
            unit_price = float(prod['price'])
            cur.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                        (order_id, int(pid), qty, unit_price))
            # decrement stock if not NULL
            cur.execute("UPDATE products SET stock = stock - ? WHERE id = ? AND stock IS NOT NULL", (qty, int(pid)))
            # increment seller's total_sales if seller_id present
            seller_id = prod.get('seller_id') if isinstance(prod, dict) else prod['seller_id']
            if seller_id:
                cur.execute("UPDATE users SET total_sales = COALESCE(total_sales, 0) + ? WHERE id = ?", (qty, seller_id))
        conn.commit()
        conn.close()
        session.pop('cart', None)

        # redirect to order confirmation page (new)
        flash("Order placed successfully!")
        return redirect(url_for('order_confirmation', order_id=order_id))

    # GET: prefill name/email if available
    cur.execute("SELECT username, email FROM users WHERE id = ?", (session.get('user_id'),))
    u = cur.fetchone()
    conn.close()
    pre_name = u['username'] if u else ''
    pre_email = u['email'] if u else ''
    return render_template('checkout.html', items=items, total_amount=total, pre_name=pre_name, pre_email=pre_email)

# new route: order confirmation
@app.route('/order/<int:order_id>')
def order_confirmation(order_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cur.fetchone()
    if not order:
        conn.close()
        flash("Order not found.")
        return redirect(url_for('index'))

    cur.execute("""
        SELECT oi.quantity, oi.unit_price, p.title
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    """, (order_id,))
    items = cur.fetchall()
    conn.close()
    return render_template('order_confirmation.html', order=order, items=items)

@app.route('/addresses')
def address_suggestions():
    """Return saved addresses for the logged-in user that match ?query=..."""
    if 'user_id' not in session:
        return jsonify([])

    q = request.args.get('query', '').strip()
    conn = get_db_connection()
    cur = conn.cursor()
    if q:
        like = f"%{q}%"
        cur.execute("SELECT id, label, address_text FROM addresses WHERE user_id = ? AND address_text LIKE ? ORDER BY created_at DESC LIMIT 8",
                    (session['user_id'], like))
    else:
        cur.execute("SELECT id, label, address_text FROM addresses WHERE user_id = ? ORDER BY created_at DESC LIMIT 8",
                    (session['user_id'],))
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"id": r["id"], "label": r["label"], "address": r["address_text"]} for r in rows])

@app.route('/seller/<int:seller_id>')
def seller_profile(seller_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, business_name, seller_description, rating, total_sales, logo_url FROM users WHERE id = ?",
        (seller_id,)
    )
    seller = cur.fetchone()

    products = []
    if seller:
        cur.execute(
            "SELECT id, title, description, price, stock, created_at, image_url FROM products WHERE seller_id = ? ORDER BY created_at DESC",
            (seller_id,)
        )
        products = cur.fetchall()

    conn.close()
    return render_template('seller_profile.html', seller=seller, products=products)


@app.route('/seller/<int:seller_id>/contact', methods=['GET', 'POST'])
def seller_contact(seller_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, business_name FROM users WHERE id = ?", (seller_id,))
    seller = cur.fetchone()
    if not seller:
        conn.close()
        flash("Seller not found.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        subject = request.form.get('subject','').strip()
        message = request.form.get('message','').strip()

        if not name or not email or not message:
            flash('Please fill in your name, email and message.')
            conn.close()
            # if AJAX, return JSON error
            wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
            if wants_json:
                conn.close()
                return jsonify({"ok": False, "error": "Please fill in your name, email and message."}), 400
            return render_template('seller_contact.html', seller=seller, form=request.form)

        # store message for review (table created on demand)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS seller_messages (
                id INTEGER PRIMARY KEY,
                seller_id INTEGER,
                sender_name TEXT,
                sender_email TEXT,
                subject TEXT,
                message TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute("INSERT INTO seller_messages (seller_id, sender_name, sender_email, subject, message) VALUES (?, ?, ?, ?, ?)",
                    (seller_id, name, email, subject, message))
        conn.commit()
        conn.close()
        wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if wants_json:
            return jsonify({"ok": True, "message": "Your message was sent to the seller."})
        flash('Your message was sent to the seller.')
        return redirect(url_for('seller_profile', seller_id=seller_id))

    conn.close()
    return render_template('seller_contact.html', seller=seller)


# Seller application flow
@app.route('/apply-seller', methods=['GET', 'POST'])
@login_required
def apply_seller():
    # ensure applications table exists with expected schema
    conn = get_db_connection()
    cur = conn.cursor()
    ensure_seller_applications_table(conn)

    if request.method == 'POST':
        business_name = request.form.get('business_name','').strip() or None
        seller_description = request.form.get('seller_description','').strip() or None
        # no logo_url accepted from applicant form anymore (admins set logos)

        cur.execute("INSERT INTO seller_applications (user_id, business_name, seller_description) VALUES (?, ?, ?)",
                    (session.get('user_id'), business_name, seller_description))
        conn.commit()
        conn.close()
        flash("Application submitted. We'll review it and follow up.")
        return redirect(url_for('index'))

    conn.close()
    return render_template('seller_apply.html')

# Admin dashboard
@app.route('/admin')
@admin_required
def admin_index():
    conn = get_db_connection()
    cur = conn.cursor()
    # ensure applications table exists so the subquery below won't fail
    ensure_seller_applications_table(conn)
    cur.execute("""
        SELECT
          (SELECT COUNT(*) FROM products) AS products_count,
          (SELECT COUNT(*) FROM users) AS users_count,
          (SELECT COUNT(*) FROM orders) AS orders_count,
          (SELECT COUNT(*) FROM seller_applications WHERE status IS NULL OR status = 'pending') AS pending_applications
    """)
    stats = cur.fetchone()
    conn.close()
    return render_template('admin/dashboard.html', stats=stats)


@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, buyer_id, buyer_name, total, created_at FROM orders ORDER BY created_at DESC")
    orders = cur.fetchall()
    conn.close()
    return render_template('admin/orders.html', orders=orders)


@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cur.fetchone()
    if not order:
        conn.close()
        flash("Order not found.")
        return redirect(url_for('admin_orders'))

    cur.execute("SELECT oi.quantity, oi.unit_price, p.title FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?", (order_id,))
    items = cur.fetchall()
    conn.close()
    return render_template('admin/order_detail.html', order=order, items=items)


@app.route('/admin/seller_applications')
@admin_required
def admin_seller_applications():
    conn = get_db_connection()
    cur = conn.cursor()
    ensure_seller_applications_table(conn)
    cur.execute("SELECT sa.id, sa.user_id, sa.business_name, sa.seller_description, sa.logo_url, sa.status, sa.created_at, u.username, u.email FROM seller_applications sa LEFT JOIN users u ON sa.user_id = u.id ORDER BY sa.created_at DESC")
    applications = cur.fetchall()
    conn.close()
    return render_template('admin/seller_applications.html', applications=applications)


@app.route('/admin/seller_applications/<int:app_id>/<action>', methods=['POST'])
@admin_required
def admin_seller_application_action(app_id, action):
    if action not in ('approve', 'reject'):
        flash('Invalid action.')
        return redirect(url_for('admin_seller_applications'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM seller_applications WHERE id = ?', (app_id,))
    app_row = cur.fetchone()
    if not app_row:
        conn.close()
        flash('Application not found.')
        return redirect(url_for('admin_seller_applications'))

    if action == 'approve':
        # mark user as seller and copy details if present
        cur.execute(
            'UPDATE users SET is_seller = 1, business_name = COALESCE(?, business_name), logo_url = COALESCE(?, logo_url), seller_description = COALESCE(?, seller_description) WHERE id = ?',
            (app_row['business_name'], app_row['logo_url'], app_row['seller_description'], app_row['user_id'])
        )
        # remove the application after approval
        cur.execute("DELETE FROM seller_applications WHERE id = ?", (app_id,))
        flash('Application approved and user promoted to seller.')
    else:
        # remove application on rejection
        cur.execute("DELETE FROM seller_applications WHERE id = ?", (app_id,))
        flash('Application rejected.')

    conn.commit()
    conn.close()
    return redirect(url_for('admin_seller_applications'))

# Product management
@app.route('/admin/products')
@admin_required
def admin_products():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT p.id, p.title, p.price, p.stock, u.username AS seller, c.name AS category FROM products p LEFT JOIN users u ON p.seller_id = u.id LEFT JOIN categories c ON p.category_id = c.id ORDER BY p.created_at DESC")
    products = cur.fetchall()
    conn.close()
    return render_template('admin/products.html', products=products)


@app.route('/admin/categories')
@admin_required
def admin_categories():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, slug, description, created_at FROM categories ORDER BY name")
    categories = cur.fetchall()
    conn.close()
    return render_template('admin/categories.html', categories=categories)


def _slugify(name: str) -> str:
    # simple slugifier: lowercase, replace spaces with hyphens, remove basic unsafe chars
    if not name:
        return ''
    s = name.strip().lower()
    s = s.replace(' ', '-')
    # strip characters other than alphanum, hyphen, underscore
    return ''.join(ch for ch in s if ch.isalnum() or ch in ('-', '_'))


@app.route('/admin/categories/new', methods=['GET', 'POST'])
@admin_required
def admin_category_new():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        slug = request.form.get('slug','').strip() or _slugify(name)
        description = request.form.get('description','').strip() or None
        if not name:
            flash('Category name required.')
            return redirect(url_for('admin_category_new'))
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO categories (name, slug, description) VALUES (?, ?, ?)", (name, slug, description))
            conn.commit()
            flash('Category created.')
            return redirect(url_for('admin_categories'))
        except sqlite3.IntegrityError:
            flash('Category name or slug already exists.')
            conn.close()
            return redirect(url_for('admin_category_new'))
    return render_template('admin/category_form.html', category=None)


@app.route('/admin/categories/<int:cat_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_category_edit(cat_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, slug, description FROM categories WHERE id = ?", (cat_id,))
    cat = cur.fetchone()
    if not cat:
        conn.close()
        flash('Category not found.')
        return redirect(url_for('admin_categories'))
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        slug = request.form.get('slug','').strip() or _slugify(name)
        description = request.form.get('description','').strip() or None
        if not name:
            flash('Category name required.')
            conn.close()
            return redirect(url_for('admin_category_edit', cat_id=cat_id))
        try:
            cur.execute("UPDATE categories SET name = ?, slug = ?, description = ? WHERE id = ?", (name, slug, description, cat_id))
            conn.commit()
            flash('Category updated.')
            conn.close()
            return redirect(url_for('admin_categories'))
        except sqlite3.IntegrityError:
            flash('Category name or slug already exists.')
            conn.close()
            return redirect(url_for('admin_category_edit', cat_id=cat_id))
    conn.close()
    return render_template('admin/category_form.html', category=cat)


@app.route('/admin/categories/<int:cat_id>/delete', methods=['POST'])
@admin_required
def admin_category_delete(cat_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # disassociate products from this category
    cur.execute("UPDATE products SET category_id = NULL WHERE category_id = ?", (cat_id,))
    cur.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    flash('Category deleted (products unassigned).')
    return redirect(url_for('admin_categories'))

@app.route('/admin/products/new', methods=['GET', 'POST'])
@admin_required
def admin_product_new():
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        price = request.form.get('price','0').strip()
        stock = request.form.get('stock','0').strip()
        seller_id = request.form.get('seller_id') or None
        category_id = request.form.get('category_id') or None
        if category_id == '':
            category_id = None
        else:
            try:
                category_id = int(category_id)
            except Exception:
                category_id = None
        # optional image filename/URL provided by admin
        image_url = request.form.get('image_url','').strip() or None
        if image_url and not (image_url.startswith('http://') or image_url.startswith('https://') or image_url.startswith('/')):
            # treat bare filenames as files placed under /static/img/
            image_url = f"/static/img/{image_url}"
        # Validate price
        try:
            price_val = float(price)
        except ValueError:
            flash("Invalid price.")
            return redirect(url_for('admin_product_new'))

        # Validate stock: allow blank meaning NULL (unlimited). Otherwise parse int and bounds-check.
        stock_val = None
        stock_raw = stock
        if stock_raw != '':
            try:
                stock_val = int(stock_raw)
            except ValueError:
                flash("Invalid stock value.")
                return redirect(url_for('admin_product_new'))
            if stock_val < 0:
                flash("Stock cannot be negative. Use empty value for unlimited.")
                return redirect(url_for('admin_product_new'))
            if stock_val > MAX_SQLITE_INT:
                flash(f"Stock value too large. Maximum allowed is {MAX_SQLITE_INT}.")
                return redirect(url_for('admin_product_new'))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO products (seller_id, title, description, price, stock, image_url, category_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (seller_id, title, description, price_val, stock_val, image_url, category_id))
        conn.commit()
        conn.close()
        flash("Product created.")
        return redirect(url_for('admin_products'))
    # GET
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users ORDER BY username")
    sellers = cur.fetchall()
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cur.fetchall()
    conn.close()
    return render_template('admin/product_form.html', sellers=sellers, product=None, categories=categories)

@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_product_edit(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cur.fetchone()
    if not product:
        conn.close()
        flash("Product not found.")
        return redirect(url_for('admin_products'))
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        price = request.form.get('price','0').strip()
        stock = request.form.get('stock','0').strip()
        seller_id = request.form.get('seller_id') or None
        category_id = request.form.get('category_id') or None
        if category_id == '':
            category_id = None
        else:
            try:
                category_id = int(category_id)
            except Exception:
                category_id = None
        # Validate price
        try:
            price_val = float(price)
        except ValueError:
            flash("Invalid price.")
            return redirect(url_for('admin_product_edit', product_id=product_id))

        # Validate stock
        stock_val = None
        stock_raw = stock
        if stock_raw != '':
            try:
                stock_val = int(stock_raw)
            except ValueError:
                flash("Invalid stock value.")
                return redirect(url_for('admin_product_edit', product_id=product_id))
            if stock_val < 0:
                flash("Stock cannot be negative. Use empty value for unlimited.")
                return redirect(url_for('admin_product_edit', product_id=product_id))
            if stock_val > MAX_SQLITE_INT:
                flash(f"Stock value too large. Maximum allowed is {MAX_SQLITE_INT}.")
                return redirect(url_for('admin_product_edit', product_id=product_id))
        # optional image filename/URL provided by admin
        image_url = request.form.get('image_url','').strip() or None
        if image_url and not (image_url.startswith('http://') or image_url.startswith('https://') or image_url.startswith('/')):
            image_url = f"/static/img/{image_url}"

        if image_url is not None:
            cur.execute("UPDATE products SET seller_id = ?, title = ?, description = ?, price = ?, stock = ?, image_url = ?, category_id = ? WHERE id = ?",
                (seller_id, title, description, price_val, stock_val, image_url, category_id, product_id))
        else:
            cur.execute("UPDATE products SET seller_id = ?, title = ?, description = ?, price = ?, stock = ?, category_id = ? WHERE id = ?",
                (seller_id, title, description, price_val, stock_val, category_id, product_id))
        conn.commit()
        conn.close()
        flash("Product updated.")
        return redirect(url_for('admin_products'))
    # GET form
    cur.execute("SELECT id, username FROM users ORDER BY username")
    sellers = cur.fetchall()
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cur.fetchall()
    conn.close()
    return render_template('admin/product_form.html', product=product, sellers=sellers, categories=categories)

@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_product_delete(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash("Product deleted.")
    return redirect(url_for('admin_products'))


# Seller-only decorator
def seller_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get('user_id')
        if not uid:
            return redirect(url_for('login', next=request.path))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_seller FROM users WHERE id = ?", (uid,))
        u = cur.fetchone()
        conn.close()
        if not (u and u['is_seller']):
            flash('Seller access required.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# Seller dashboard: list seller's products
@app.route('/seller/dashboard')
@login_required
@seller_required
def seller_dashboard():
    uid = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, business_name, seller_description, logo_url FROM users WHERE id = ?", (uid,))
    seller = cur.fetchone()
    cur.execute("SELECT id, title, price, stock, created_at, image_url FROM products WHERE seller_id = ? ORDER BY created_at DESC", (uid,))
    products = cur.fetchall()
    conn.close()
    return render_template('seller/products.html', seller=seller, products=products)


# Seller: add new product
@app.route('/seller/products/new', methods=['GET', 'POST'])
@login_required
@seller_required
def seller_product_new():
    uid = session.get('user_id')
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        price = request.form.get('price','0').strip()
        stock = request.form.get('stock','0').strip()
    # optional image filename/URL provided by seller
        image_url = request.form.get('image_url','').strip() or None
        if image_url and not (image_url.startswith('http://') or image_url.startswith('https://') or image_url.startswith('/')):
            image_url = f"/static/img/{image_url}"
        # Validate price
        try:
            price_val = float(price)
        except ValueError:
            flash("Invalid price.")
            return redirect(url_for('seller_product_new'))

        # Validate stock: blank means unlimited (NULL)
        stock_val = None
        stock_raw = stock
        if stock_raw != '':
            try:
                stock_val = int(stock_raw)
            except ValueError:
                flash("Invalid stock value.")
                return redirect(url_for('seller_product_new'))
            if stock_val < 0:
                flash("Stock cannot be negative. Use empty value for unlimited.")
                return redirect(url_for('seller_product_new'))
            if stock_val > MAX_SQLITE_INT:
                flash(f"Stock value too large. Maximum allowed is {MAX_SQLITE_INT}.")
                return redirect(url_for('seller_product_new'))
        conn = get_db_connection()
        cur = conn.cursor()
        category_id = request.form.get('category_id') or None
        if category_id == '':
            category_id = None
        else:
            try:
                category_id = int(category_id)
            except Exception:
                category_id = None

        cur.execute("INSERT INTO products (seller_id, title, description, price, stock, image_url, category_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (uid, title, description, price_val, stock_val, image_url, category_id))
        conn.commit()
        conn.close()
        flash("Product created.")
        return redirect(url_for('seller_dashboard'))

    # GET: supply categories to select
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cur.fetchall()
    conn.close()
    return render_template('seller/product_form.html', product=None, categories=categories)


# Seller: edit product
@app.route('/seller/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@seller_required
def seller_product_edit(product_id):
    uid = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cur.fetchone()
    if not product:
        conn.close()
        flash('Product not found.')
        return redirect(url_for('seller_dashboard'))
    if product['seller_id'] != uid:
        conn.close()
        flash('Not authorized to edit this product.')
        return redirect(url_for('seller_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        price = request.form.get('price','0').strip()
        stock = request.form.get('stock','0').strip()
        image_url = request.form.get('image_url','').strip() or None
        if image_url and not (image_url.startswith('http://') or image_url.startswith('https://') or image_url.startswith('/')):
            image_url = f"/static/img/{image_url}"
        # Validate price
        try:
            price_val = float(price)
        except ValueError:
            flash("Invalid price.")
            return redirect(url_for('seller_product_edit', product_id=product_id))

        # Validate stock
        stock_val = None
        stock_raw = stock
        if stock_raw != '':
            try:
                stock_val = int(stock_raw)
            except ValueError:
                flash("Invalid stock value.")
                return redirect(url_for('seller_product_edit', product_id=product_id))
            if stock_val < 0:
                flash("Stock cannot be negative. Use empty value for unlimited.")
                return redirect(url_for('seller_product_edit', product_id=product_id))
            if stock_val > MAX_SQLITE_INT:
                flash(f"Stock value too large. Maximum allowed is {MAX_SQLITE_INT}.")
                return redirect(url_for('seller_product_edit', product_id=product_id))

        category_id = request.form.get('category_id') or None
        if category_id == '':
            category_id = None
        else:
            try:
                category_id = int(category_id)
            except Exception:
                category_id = None

        if image_url is not None:
            cur.execute("UPDATE products SET title = ?, description = ?, price = ?, stock = ?, image_url = ?, category_id = ? WHERE id = ?",
                        (title, description, price_val, stock_val, image_url, category_id, product_id))
        else:
            cur.execute("UPDATE products SET title = ?, description = ?, price = ?, stock = ?, category_id = ? WHERE id = ?",
                        (title, description, price_val, stock_val, category_id, product_id))
        conn.commit()
        conn.close()
        flash('Product updated.')
        return redirect(url_for('seller_dashboard'))

    # GET: include categories for select
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cur.fetchall()
    conn.close()
    return render_template('seller/product_form.html', product=product, categories=categories)


# Seller: delete product
@app.route('/seller/products/<int:product_id>/delete', methods=['POST'])
@login_required
@seller_required
def seller_product_delete(product_id):
    uid = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT seller_id FROM products WHERE id = ?", (product_id,))
    p = cur.fetchone()
    if not p:
        conn.close()
        flash('Product not found.')
        return redirect(url_for('seller_dashboard'))
    if p['seller_id'] != uid:
        conn.close()
        flash('Not authorized to delete this product.')
        return redirect(url_for('seller_dashboard'))
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash('Product deleted.')
    return redirect(url_for('seller_dashboard'))

# User management
@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, is_admin, is_seller, created_at FROM users ORDER BY created_at DESC")
    users = cur.fetchall()
    conn.close()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/toggle_admin', methods=['POST'])
@admin_required
def admin_user_toggle_admin(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
    u = cur.fetchone()
    if not u:
        conn.close()
        flash("User not found.")
        return redirect(url_for('admin_users'))
    new = 0 if u['is_admin'] else 1
    cur.execute("UPDATE users SET is_admin = ? WHERE id = ?", (new, user_id))
    conn.commit()
    conn.close()
    flash("User admin status updated.")
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/toggle_seller', methods=['POST'])
@admin_required
def admin_user_toggle_seller(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_seller FROM users WHERE id = ?", (user_id,))
    u = cur.fetchone()
    if not u:
        conn.close()
        flash("User not found.")
        return redirect(url_for('admin_users'))
    new = 0 if u['is_seller'] else 1
    cur.execute("UPDATE users SET is_seller = ? WHERE id = ?", (new, user_id))
    conn.commit()
    conn.close()
    flash("User seller status updated.")
    # if we just promoted them to seller, send admin to the seller details form to fill info
    if new == 1:
        return redirect(url_for('admin_edit_seller', user_id=user_id))
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/seller', methods=['GET', 'POST'])
@admin_required
def admin_edit_seller(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, business_name, seller_description, rating, total_sales, is_seller, logo_url FROM users WHERE id = ?", (user_id,))
    u = cur.fetchone()
    if not u:
        conn.close()
        flash("User not found.")
        return redirect(url_for('admin_users'))

    if request.method == 'POST':
        business_name = request.form.get('business_name','').strip() or None
        seller_description = request.form.get('seller_description','').strip() or None
        logo_url = request.form.get('logo_url','').strip() or None
        # normalize bare filenames to /static/img/<name>
        if logo_url and not (logo_url.startswith('http://') or logo_url.startswith('https://') or logo_url.startswith('/')):
            logo_url = f"/static/img/{logo_url}"
        try:
            rating = float(request.form.get('rating','0') or 0)
        except ValueError:
            rating = 0.0
        try:
            total_sales = int(request.form.get('total_sales','0') or 0)
        except ValueError:
            total_sales = 0

        # ensure user is marked as seller
        if logo_url is not None:
            cur.execute("UPDATE users SET business_name = ?, seller_description = ?, rating = ?, total_sales = ?, is_seller = 1, logo_url = ? WHERE id = ?",
                        (business_name, seller_description, rating, total_sales, logo_url, user_id))
        else:
            cur.execute("UPDATE users SET business_name = ?, seller_description = ?, rating = ?, total_sales = ?, is_seller = 1 WHERE id = ?",
                        (business_name, seller_description, rating, total_sales, user_id))
        conn.commit()
        conn.close()
        flash("Seller details updated.")
        return redirect(url_for('admin_users'))

    conn.close()
    return render_template('admin/seller_form.html', user=u)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_user_delete(user_id):
    # protect deleting self
    if session.get('user_id') == user_id:
        flash("Cannot delete your own account.")
        return redirect(url_for('admin_users'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted.")
    return redirect(url_for('admin_users'))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

