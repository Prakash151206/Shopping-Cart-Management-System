"""Business rules for product catalogs, carts, coupons, and checkout."""

from datetime import datetime
import uuid
from typing import Any

from models import Cart, Product, User
from storage import JSONStorage


class CartManager:
    """Coordinate shopping cart operations and persistent records."""

    GST_RATE = 0.05
    COUPONS = {"SAVE10": 0.10}

    def __init__(self, storage: JSONStorage) -> None:
        self.storage = storage
        self.products = storage.load_products()

    def find_product(self, product_id: str) -> Product:
        """Return a product by ID or raise a helpful error."""
        for product in self.products:
            if product.id == product_id:
                return product
        raise KeyError("Product ID was not found.")

    def add_product(self, product: Product) -> None:
        """Add a new product, requiring a unique ID."""
        if any(existing.id == product.id for existing in self.products):
            raise ValueError("A product with that ID already exists.")
        self.products.append(product)
        self.storage.save_products(self.products)

    def edit_product(self, product_id: str, **changes: Any) -> Product:
        """Update the editable fields of a product."""
        product = self.find_product(product_id)
        for field_name in ("name", "category", "price", "stock"):
            if field_name in changes:
                setattr(product, field_name, changes[field_name])
        product.__post_init__()
        self.storage.save_products(self.products)
        return product

    def delete_product(self, product_id: str) -> None:
        """Delete a product from the catalog."""
        self.find_product(product_id)
        self.products = [product for product in self.products if product.id != product_id]
        self.storage.save_products(self.products)

    def add_to_cart(self, cart: Cart, product_id: str, quantity: int) -> None:
        """Add a quantity after validating it against available stock."""
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        product = self.find_product(product_id)
        current = cart.get_item(product_id)
        new_quantity = quantity + (current.quantity if current else 0)
        if new_quantity > product.stock:
            raise ValueError(f"Only {product.stock} unit(s) are in stock.")
        cart.set_quantity(product, new_quantity)

    def remove_from_cart(self, cart: Cart, product_id: str) -> None:
        """Remove a product from the cart."""
        cart.remove(product_id)

    def update_quantity(self, cart: Cart, product_id: str, quantity: int) -> None:
        """Set a cart quantity, removing the line when quantity is zero."""
        item = cart.get_item(product_id)
        if item is None:
            raise KeyError("That product is not in the cart.")
        if quantity < 0:
            raise ValueError("Quantity cannot be negative.")
        if quantity > item.product.stock:
            raise ValueError(f"Only {item.product.stock} unit(s) are in stock.")
        cart.set_quantity(item.product, quantity)

    def apply_coupon(self, cart: Cart, code: str) -> float:
        """Apply a supported coupon and return its discount rate."""
        normalized = code.strip().upper()
        if normalized not in self.COUPONS:
            raise ValueError("Invalid coupon code.")
        cart.coupon_code = normalized
        return self.COUPONS[normalized]

    def totals(self, cart: Cart) -> dict[str, float]:
        """Calculate subtotal, discount, GST, and grand total."""
        subtotal = round(sum(item.subtotal for item in cart.items.values()), 2)
        discount_rate = self.COUPONS.get(cart.coupon_code, 0.0)
        discount = round(subtotal * discount_rate, 2)
        taxable_amount = subtotal - discount
        tax = round(taxable_amount * self.GST_RATE, 2)
        return {
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "total": round(taxable_amount + tax, 2),
        }

    def checkout(self, cart: Cart, user: User) -> dict[str, Any]:
        """Create an order, reduce stock, and clear the cart."""
        if not cart.items:
            raise ValueError("Your cart is empty.")
        for item in cart.items.values():
            product = self.find_product(item.product.id)
            if item.quantity > product.stock:
                raise ValueError(f"Not enough stock for {product.name}.")

        totals = self.totals(cart)
        order: dict[str, Any] = {
            "order_id": uuid.uuid4().hex[:8].upper(),
            "username": user.username,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "coupon_code": cart.coupon_code,
            "items": [
                {
                    "product_id": item.product.id,
                    "name": item.product.name,
                    "price": item.product.price,
                    "quantity": item.quantity,
                    "subtotal": item.subtotal,
                }
                for item in cart.items.values()
            ],
            **totals,
        }
        orders = self.storage.load_orders()
        orders.append(order)
        old_stock = {item.product.id: item.product.stock for item in cart.items.values()}
        try:
            for item in cart.items.values():
                self.find_product(item.product.id).stock -= item.quantity
            self.storage.save_products(self.products)
            self.storage.save_orders(orders)
        except OSError:
            for product_id, stock in old_stock.items():
                self.find_product(product_id).stock = stock
            raise
        cart.clear()
        return order

    def orders_for(self, username: str) -> list[dict[str, Any]]:
        """Return a user's order history, newest order first."""
        return [
            order for order in reversed(self.storage.load_orders())
            if order.get("username") == username
        ]

    def low_stock(self, threshold: int = 5) -> list[Product]:
        """Return products with stock at or below the threshold."""
        return [product for product in self.products if product.stock <= threshold]