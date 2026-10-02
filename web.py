"""Flask website for the Shopping Cart Management System."""

from functools import wraps
import os
import secrets
from typing import Any, Callable

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

from cart_manager import CartManager
from models import Cart, Product, User
from storage import JSONStorage


PRODUCT_IMAGES = {
    "P001": "photo-1531346878377-a5be20888e57",
    "P002": "photo-1583485088034-697b5bc54ccd",
    "P003": "photo-1514228742587-6b1558fcca3d",
    "P004": "photo-1544816155-12df9643f363",
    "P005": "photo-1507473885765-e6ed057f782c",
    "P006": "photo-1527864550417-7fd91fc51a46",
    "P007": "photo-1602143407151-7111542de6e8",
    "P008": "photo-1455390582262-044cdead277a",
    "P009": "photo-1584100936595-c0654b55a2e2",
    "P010": "photo-1558618666-fcd25c85cd64",
    "P011": "photo-1455390582262-044cdead277a",
    "P012": "photo-1531346878377-a5be20888e57",
    "P013": "photo-1513364776144-60967b0f800f",
    "P014": "photo-1600369671236-e74521d4b6ad",
    "P015": "photo-1602143407151-7111542de6e8",
    "P016": "photo-1485955900006-10f4d324d411",
    "P017": "photo-1490312278390-ab64016e0aa9",
    "P018": "photo-1544816155-12df9643f363",
    "P019": "photo-1544816155-12df9643f363",
    "P020": "photo-1534274988757-a28bf1a57c17",
    "P021": "photo-1553062407-98eeb64c6a62",
    "P022": "photo-1586350977771-b3b0abd50c82",
    "P023": "photo-1511707171634-5f897ff02aa9",
    "P024": "photo-1583863788434-e58a36330cf0",
    "P025": "photo-1606220945770-b5b6c2c55bf1",
    "P026": "photo-1603398938378-e54eab446dde",
    "P027": "photo-1523987355523-c7b5b0dd90a7",
    "P028": "photo-1523987355523-c7b5b0dd90a7",
    "P029": "photo-1500530855697-b586d89ba3ee",
    "P030": "photo-1553062407-98eeb64c6a62",
}


def format_inr(value: float) -> str:
    """Format a numeric amount as Indian rupees with Indian digit grouping."""
    amount = f"{abs(value):.2f}"
    whole, fraction = amount.split(".")
    if len(whole) > 3:
        prefix, last_three = whole[:-3], whole[-3:]
        groups = []
        while prefix:
            groups.insert(0, prefix[-2:])
            prefix = prefix[:-2]
        whole = f"{','.join(groups)},{last_three}"
    sign = "-" if value < 0 else ""
    return f"{sign}₹{whole}.{fraction}"


def create_app(storage: JSONStorage | None = None) -> Flask:
    """Create the website application, optionally with isolated storage."""
    app = Flask(__name__)
    app.secret_key = os.environ.get("SHOP_SECRET_KEY", secrets.token_hex(32))
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    data_store = storage or JSONStorage()
    manager = CartManager(data_store)
    app.extensions["shop_storage"] = data_store
    app.extensions["cart_manager"] = manager

    def get_cart() -> Cart:
        """Restore cart lines from the signed session cookie."""
        cart = Cart()
        for product_id, quantity in session.get("cart", {}).items():
            try:
                manager.add_to_cart(cart, product_id, int(quantity))
            except (KeyError, ValueError, TypeError):
                continue
        coupon = session.get("coupon", "")
        if coupon:
            try:
                manager.apply_coupon(cart, coupon)
            except ValueError:
                pass
        return cart

    def save_cart(cart: Cart) -> None:
        """Store only product IDs and quantities in the signed session."""
        session["cart"] = {
            product_id: item.quantity for product_id, item in cart.items.items()
        }
        session["coupon"] = cart.coupon_code

    def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
        """Restrict a view to authenticated users."""
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if g.user is None:
                flash("Please sign in to continue.", "info")
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def admin_required(view: Callable[..., Any]) -> Callable[..., Any]:
        """Restrict a view to an administrator account."""
        @wraps(view)
        @login_required
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if g.user.role != "admin":
                flash("Administrator access is required.", "error")
                return redirect(url_for("index"))
            return view(*args, **kwargs)
        return wrapped

    @app.before_request
    def load_request_state() -> None:
        """Attach the current user and cart to the request context."""
        username = session.get("username")
        g.user = next(
            (user for user in data_store.load_users() if user.username == username), None
        )
        g.cart = get_cart()

    @app.context_processor
    def template_context() -> dict[str, Any]:
        """Expose common layout values to every page."""
        return {
            "current_user": g.get("user"),
            "cart_count": sum(item.quantity for item in g.get("cart", Cart()).items.values()),
            "money": format_inr,
        }

    def image_url(product_id: str) -> str:
        """Build the remote product image URL for a catalog tile."""
        image_id = PRODUCT_IMAGES.get(product_id, "photo-1494438639946-1ebd1d20bf85")
        return f"https://images.unsplash.com/{image_id}?auto=format&fit=crop&w=900&q=82"

    @app.get("/")
    def index() -> str:
        """Render the searchable and filterable product catalog."""
        search = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        products = manager.products
        if search:
            products = [p for p in products if search.casefold() in p.name.casefold()]
        if category:
            products = [p for p in products if p.category.casefold() == category.casefold()]
        categories = sorted({product.category for product in manager.products})
        return render_template(
            "index.html", products=products, categories=categories,
            selected_category=category, search=search, image_url=image_url,
        )

    @app.route("/register", methods=["GET", "POST"])
    def register() -> Any:
        """Register a customer account."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            users = data_store.load_users()
            if not username:
                flash("Enter a username.", "error")
            elif any(user.username.casefold() == username.casefold() for user in users):
                flash("That username is already registered.", "error")
            elif len(password) < 6:
                flash("Use a password with at least six characters.", "error")
            else:
                user = User(username, User.hash_password(password))
                data_store.save_users([*users, user])
                session["username"] = user.username
                flash("Your account is ready. Welcome in.", "success")
                return redirect(url_for("index"))
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    def login() -> Any:
        """Authenticate a customer or administrator."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = next(
                (u for u in data_store.load_users()
                 if u.username.casefold() == username.casefold()), None
            )
            if user and user.verify_password(password):
                session.clear()
                session["username"] = user.username
                flash(f"Welcome back, {user.username}.", "success")
                destination = request.args.get("next", "")
                return redirect(destination if destination.startswith("/") else url_for("index"))
            flash("The username or password was not recognized.", "error")
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    def logout() -> Any:
        """End the current browser session."""
        session.clear()
        flash("You are signed out.", "info")
        return redirect(url_for("index"))

    @app.post("/cart/add/<product_id>")
    def add_to_cart(product_id: str) -> Any:
        """Add a product to the session cart."""
        try:
            quantity = int(request.form.get("quantity", "1"))
            manager.add_to_cart(g.cart, product_id, quantity)
            save_cart(g.cart)
            product = manager.find_product(product_id)
            flash(f"{product.name} added to your bag.", "success")
        except (ValueError, KeyError) as error:
            flash(str(error), "error")
        return redirect(request.referrer or url_for("index"))

    @app.get("/cart")
    def cart_page() -> str:
        """Show cart contents and pricing breakdown."""
        return render_template("cart.html", cart=g.cart, totals=manager.totals(g.cart))

    @app.post("/cart/update/<product_id>")
    def update_cart(product_id: str) -> Any:
        """Change or remove an item quantity in the cart."""
        try:
            quantity = int(request.form.get("quantity", "0"))
            manager.update_quantity(g.cart, product_id, quantity)
            save_cart(g.cart)
            flash("Your bag has been updated.", "success")
        except (ValueError, KeyError) as error:
            flash(str(error), "error")
        return redirect(url_for("cart_page"))

    @app.post("/cart/remove/<product_id>")
    def remove_from_cart(product_id: str) -> Any:
        """Remove a product line from the cart."""
        try:
            manager.remove_from_cart(g.cart, product_id)
            save_cart(g.cart)
            flash("Item removed from your bag.", "info")
        except KeyError as error:
            flash(str(error), "error")
        return redirect(url_for("cart_page"))

    @app.post("/cart/coupon")
    def apply_coupon() -> Any:
        """Apply a supported promotion code."""
        try:
            manager.apply_coupon(g.cart, request.form.get("coupon", ""))
            save_cart(g.cart)
            flash("SAVE10 applied. You saved 10%.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("cart_page"))

    @app.route("/checkout", methods=["GET", "POST"])
    @login_required
    def checkout() -> Any:
        """Review and place the current order."""
        if request.method == "POST":
            try:
                order = manager.checkout(g.cart, g.user)
                session.pop("cart", None)
                session.pop("coupon", None)
                return render_template("receipt.html", order=order)
            except (ValueError, KeyError, OSError) as error:
                flash(str(error), "error")
                return redirect(url_for("cart_page"))
        if not g.cart.items:
            flash("Add something to your bag before checking out.", "info")
            return redirect(url_for("index"))
        return render_template(
            "checkout.html", cart=g.cart, totals=manager.totals(g.cart)
        )

    @app.get("/orders")
    @login_required
    def order_history() -> str:
        """Show the signed-in user's previous orders."""
        return render_template("orders.html", orders=manager.orders_for(g.user.username))

    @app.route("/admin", methods=["GET", "POST"])
    @admin_required
    def admin() -> Any:
        """Manage catalog products and monitor low inventory."""
        if request.method == "POST":
            action = request.form.get("action", "")
            product_id = request.form.get("product_id", "").strip()
            try:
                if action == "add":
                    manager.add_product(Product(
                        product_id,
                        request.form.get("name", "").strip(),
                        request.form.get("category", "").strip(),
                        float(request.form.get("price", "")),
                        int(request.form.get("stock", "")),
                    ))
                    flash("Product added to the catalog.", "success")
                elif action == "edit":
                    manager.edit_product(
                        product_id,
                        name=request.form.get("name", "").strip(),
                        category=request.form.get("category", "").strip(),
                        price=float(request.form.get("price", "")),
                        stock=int(request.form.get("stock", "")),
                    )
                    flash("Product details saved.", "success")
                elif action == "delete":
                    manager.delete_product(product_id)
                    flash("Product removed from the catalog.", "info")
                else:
                    raise ValueError("Choose a valid catalog action.")
            except (ValueError, KeyError, TypeError) as error:
                flash(str(error), "error")
            return redirect(url_for("admin"))
        return render_template("admin.html", products=manager.products, low_stock=manager.low_stock())

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)