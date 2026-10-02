"""Data models for the shopping cart management system."""

from dataclasses import dataclass, field
from hashlib import pbkdf2_hmac
import hmac
import secrets
from typing import Dict


@dataclass
class Product:
    """A product available for purchase."""

    id: str
    name: str
    category: str
    price: float
    stock: int

    def __post_init__(self) -> None:
        """Reject invalid product values early."""
        self.price = float(self.price)
        self.stock = int(self.stock)
        if self.price < 0 or self.stock < 0:
            raise ValueError("Price and stock cannot be negative.")


@dataclass
class CartItem:
    """A product and quantity held in a cart."""

    product: Product
    quantity: int

    @property
    def subtotal(self) -> float:
        """Return the item's price before discounts and tax."""
        return self.product.price * self.quantity


@dataclass
class Cart:
    """A user's in-memory shopping cart."""

    _items: Dict[str, CartItem] = field(default_factory=dict, repr=False)
    coupon_code: str = ""

    @property
    def items(self) -> Dict[str, CartItem]:
        """Expose cart items for read-only iteration by the application."""
        return dict(self._items)

    def get_item(self, product_id: str) -> CartItem | None:
        """Find an item by product ID."""
        return self._items.get(product_id)

    def set_quantity(self, product: Product, quantity: int) -> None:
        """Add or replace an item's quantity; zero removes it."""
        if quantity < 0:
            raise ValueError("Quantity cannot be negative.")
        if quantity == 0:
            self._items.pop(product.id, None)
        else:
            self._items[product.id] = CartItem(product, quantity)

    def remove(self, product_id: str) -> None:
        """Remove an item from the cart."""
        if product_id not in self._items:
            raise KeyError("That product is not in the cart.")
        del self._items[product_id]

    def clear(self) -> None:
        """Empty the cart and clear its coupon."""
        self._items.clear()
        self.coupon_code = ""


@dataclass(frozen=True)
class User:
    """A registered user with a salted password hash."""

    username: str
    password_hash: str
    role: str = "customer"

    @staticmethod
    def hash_password(password: str, salt: bytes | None = None) -> str:
        """Create a PBKDF2-SHA256 hash with an embedded random salt."""
        actual_salt = salt or secrets.token_bytes(16)
        digest = pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt, 200_000)
        return f"{actual_salt.hex()}${digest.hex()}"

    def verify_password(self, password: str) -> bool:
        """Compare a password against its stored salted hash."""
        try:
            salt_hex, expected_hex = self.password_hash.split("$", maxsplit=1)
            actual = self.hash_password(password, bytes.fromhex(salt_hex)).split("$")[-1]
            return hmac.compare_digest(actual, expected_hex)
        except (ValueError, TypeError):
            return False