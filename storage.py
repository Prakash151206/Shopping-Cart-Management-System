"""JSON-backed storage helpers for products, users, and orders."""

import json
import os
from pathlib import Path
from typing import Any

from models import Product, User


class JSONStorage:
    """Read and write the application's JSON data files."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
        self.products_path = self.data_dir / "products.json"
        self.users_path = self.data_dir / "users.json"
        self.orders_path = self.data_dir / "orders.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.products_path.exists():
            self._write_json(self.products_path, [])
        if not self.users_path.exists():
            self._write_json(self.users_path, [])
        if not self.orders_path.exists():
            self._write_json(self.orders_path, [])
        if not self.load_users():
            self.save_users([User("admin", User.hash_password("admin123"), "admin")])

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        """Load JSON data, returning a default for missing or empty files."""
        try:
            with path.open("r", encoding="utf-8") as data_file:
                return json.load(data_file)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        """Write JSON atomically so interrupted writes do not truncate data."""
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as data_file:
            json.dump(value, data_file, indent=2)
            data_file.write("\n")
        os.replace(temporary_path, path)

    def load_products(self) -> list[Product]:
        """Return all valid products from products.json."""
        records = self._read_json(self.products_path, [])
        return [Product(**record) for record in records]

    def save_products(self, products: list[Product]) -> None:
        """Persist products to products.json."""
        self._write_json(self.products_path, [product.__dict__ for product in products])

    def load_users(self) -> list[User]:
        """Return registered users from users.json."""
        records = self._read_json(self.users_path, [])
        return [User(**record) for record in records]

    def save_users(self, users: list[User]) -> None:
        """Persist users without ever storing plain-text passwords."""
        self._write_json(self.users_path, [user.__dict__ for user in users])

    def load_orders(self) -> list[dict[str, Any]]:
        """Return all recorded orders."""
        return self._read_json(self.orders_path, [])

    def save_orders(self, orders: list[dict[str, Any]]) -> None:
        """Persist order history to orders.json."""
        self._write_json(self.orders_path, orders)