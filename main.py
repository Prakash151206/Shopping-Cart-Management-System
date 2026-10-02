"""Console entry point for the Shopping Cart Management System."""

from getpass import getpass
from typing import Callable

from cart_manager import CartManager
from models import Cart, Product, User
from storage import JSONStorage


WIDTH = 76


def line(char: str = "-") -> None:
    """Print a full-width separator."""
    print(char * WIDTH)


def money(value: float) -> str:
    """Format an amount as currency."""
    return f"${value:,.2f}"


def read_int(prompt: str, minimum: int | None = None) -> int:
    """Read an integer, retrying on invalid input."""
    while True:
        try:
            value = int(input(prompt).strip())
            if minimum is not None and value < minimum:
                print(f"Enter a number of at least {minimum}.")
                continue
            return value
        except ValueError:
            print("Please enter a whole number.")


def show_products(manager: CartManager, category: str = "", search: str = "") -> None:
    """Display products, optionally filtering by category or name."""
    products = manager.products
    if category:
        products = [item for item in products if item.category.casefold() == category.casefold()]
    if search:
        products = [item for item in products if search.casefold() in item.name.casefold()]
    line("=")
    print(f"{'ID':<8} {'PRODUCT':<26} {'CATEGORY':<16} {'PRICE':>10} {'STOCK':>7}")
    line()
    for product in products:
        print(
            f"{product.id:<8} {product.name[:25]:<26} {product.category[:15]:<16} "
            f"{money(product.price):>10} {product.stock:>7}"
        )
    if not products:
        print("No products matched your selection.")
    line("=")


def view_cart(cart: Cart, manager: CartManager) -> None:
    """Print cart lines and a full price breakdown."""
    line("=")
    print("YOUR CART")
    line()
    if not cart.items:
        print("Your cart is empty.")
        return
    print(f"{'ID':<8} {'PRODUCT':<28} {'QTY':>5} {'UNIT':>11} {'SUBTOTAL':>12}")
    line()
    for item in cart.items.values():
        print(
            f"{item.product.id:<8} {item.product.name[:27]:<28} {item.quantity:>5} "
            f"{money(item.product.price):>11} {money(item.subtotal):>12}"
        )
    totals = manager.totals(cart)
    print(f"Coupon: {cart.coupon_code or 'None'}")
    print(f"Subtotal: {money(totals['subtotal'])}")
    print(f"Discount: -{money(totals['discount'])}")
    print(f"GST (5%): {money(totals['tax'])}")
    print(f"Grand total: {money(totals['total'])}")
    line("=")


def register(storage: JSONStorage) -> User:
    """Register and persist a new customer account."""
    users = storage.load_users()
    username = input("Choose a username: ").strip()
    if not username or any(user.username.casefold() == username.casefold() for user in users):
        raise ValueError("Username is blank or already taken.")
    password = getpass("Choose a password (minimum 6 characters): ")
    if len(password) < 6:
        raise ValueError("Password must contain at least 6 characters.")
    user = User(username, User.hash_password(password))
    storage.save_users([*users, user])
    return user


def login(storage: JSONStorage) -> User:
    """Authenticate a user without exposing stored password hashes."""
    username = input("Username: ").strip()
    password = getpass("Password: ")
    for user in storage.load_users():
        if user.username.casefold() == username.casefold() and user.verify_password(password):
            return user
    raise ValueError("Incorrect username or password.")


def print_receipt(order: dict) -> None:
    """Print a completed order as a receipt."""
    line("=")
    print(f"RECEIPT  |  Order {order['order_id']}  |  {order['created_at']}")
    print(f"Customer: {order['username']}")
    line()
    for item in order["items"]:
        print(f"{item['name']} x {item['quantity']} @ {money(item['price'])}: {money(item['subtotal'])}")
    print(f"Subtotal: {money(order['subtotal'])}")
    print(f"Discount: -{money(order['discount'])}")
    print(f"GST: {money(order['tax'])}")
    print(f"TOTAL PAID: {money(order['total'])}")
    line("=")


def customer_menu(user: User, manager: CartManager) -> None:
    """Run the signed-in customer's menu."""
    cart = Cart()
    actions: dict[str, Callable[[], None]] = {
        "1": lambda: show_products(manager),
        "2": lambda: show_products(manager, category=input("Category: ").strip()),
        "3": lambda: show_products(manager, search=input("Search name: ").strip()),
        "4": lambda: manager.add_to_cart(
            cart, input("Product ID: ").strip(), read_int("Quantity: ", minimum=1)
        ),
        "5": lambda: manager.remove_from_cart(cart, input("Product ID to remove: ").strip()),
        "6": lambda: manager.update_quantity(
            cart, input("Product ID: ").strip(), read_int("New quantity (0 removes): ", minimum=0)
        ),
        "7": lambda: view_cart(cart, manager),
        "8": lambda: manager.apply_coupon(cart, input("Coupon code: ").strip()),
        "9": lambda: print_receipt(manager.checkout(cart, user)),
        "10": lambda: show_orders(user, manager),
    }
    while True:
        print(f"\nWelcome, {user.username}!")
        print("1 Products  2 Category filter  3 Search  4 Add to cart  5 Remove item")
        print("6 Update quantity  7 View cart  8 Apply coupon  9 Checkout  10 Past orders  0 Logout")
        choice = input("Select: ").strip()
        if choice == "0":
            return
        try:
            if choice not in actions:
                print("Choose a listed option.")
                continue
            actions[choice]()
            if choice == "4":
                print("Product added to cart.")
            elif choice == "8":
                print("Coupon SAVE10 applied: 10% off.")
            elif choice in {"5", "6"}:
                print("Cart updated.")
        except (ValueError, KeyError, OSError) as error:
            print(f"Could not complete that action: {error}")


def show_orders(user: User, manager: CartManager) -> None:
    """Display the signed-in user's previous orders."""
    orders = manager.orders_for(user.username)
    if not orders:
        print("No past orders found.")
        return
    for order in orders:
        print(f"{order['order_id']} | {order['created_at']} | {money(order['total'])}")


def admin_menu(manager: CartManager) -> None:
    """Run the product administration menu."""
    while True:
        print("\nADMIN MENU: 1 Add product  2 Edit product  3 Delete product  4 Low stock  0 Back")
        choice = input("Select: ").strip()
        try:
            if choice == "0":
                return
            if choice == "1":
                product = Product(
                    input("ID: ").strip(), input("Name: ").strip(), input("Category: ").strip(),
                    float(input("Price: ")), read_int("Stock: ", minimum=0),
                )
                manager.add_product(product)
                print("Product added.")
            elif choice == "2":
                product_id = input("Product ID: ").strip()
                product = manager.find_product(product_id)
                name = input(f"Name [{product.name}]: ").strip()
                category = input(f"Category [{product.category}]: ").strip()
                price_text = input(f"Price [{product.price:.2f}]: ").strip()
                stock_text = input(f"Stock [{product.stock}]: ").strip()
                manager.edit_product(
                    product_id,
                    **{key: value for key, value in {
                        "name": name or product.name,
                        "category": category or product.category,
                        "price": float(price_text) if price_text else product.price,
                        "stock": int(stock_text) if stock_text else product.stock,
                    }.items()},
                )
                print("Product updated.")
            elif choice == "3":
                manager.delete_product(input("Product ID to delete: ").strip())
                print("Product deleted.")
            elif choice == "4":
                print("LOW STOCK (5 or fewer)")
                for product in manager.low_stock():
                    print(f"{product.id:<8} {product.name:<28} {product.stock} left")
            else:
                print("Choose a listed option.")
        except (ValueError, KeyError, OSError) as error:
            print(f"Could not complete that action: {error}")


def main() -> None:
    """Start the application and handle the main login menu."""
    storage = JSONStorage()
    manager = CartManager(storage)
    while True:
        line("=")
        print("SHOPPING CART MANAGEMENT SYSTEM")
        print("1 Register  2 Login  3 Browse products  0 Exit")
        choice = input("Select: ").strip()
        if choice == "0":
            print("Goodbye!")
            return
        if choice == "3":
            show_products(manager)
            continue
        try:
            user = register(storage) if choice == "1" else login(storage) if choice == "2" else None
            if user is None:
                print("Choose a listed option.")
            elif user.role == "admin":
                admin_menu(manager)
            else:
                customer_menu(user, manager)
        except (ValueError, OSError) as error:
            print(f"Could not continue: {error}")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")