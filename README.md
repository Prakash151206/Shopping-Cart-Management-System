# Shopping Cart Management System

A beginner-friendly Python shopping project with a responsive browser storefront and a menu-driven console version. Both interfaces use the same object-oriented models, stock and pricing rules, password hashing, and JSON-backed catalog and order history.

## Requirements

- Python 3.10 or newer
- Flask 3.1 or newer (`requirements.txt`)

## Run the Website

From the project folder, install the dependency and start the local server:

```text
python -m pip install -r requirements.txt
python web.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Set `SHOP_SECRET_KEY` to a stable random value when running beyond local practice so browser sessions remain valid after a restart.

The first start creates `data/users.json` and `data/orders.json`; the sample catalog is in `data/products.json`. The starter administrator login is `admin` / `admin123`. Change or remove this shared demo account before exposing the app to other users. Customers can create accounts from the site.

## Run the Console Version

```text
python main.py
```

## Features

- Responsive product storefront with category filters, name search, and product photography.
- Thirty starter products across five categories, with six items in each section.
- Customer registration and login with salted PBKDF2-SHA256 password hashes.
- Add, remove, and update cart quantities with stock validation.
- `SAVE10` coupon, 5% GST, item subtotals, and rounded currency totals.
- Checkout receipt, inventory updates, and per-user order history persisted in JSON.
- Administrator catalog management: add, edit, and delete products; view low-stock items.
- Flask test-client coverage for core browser workflows.

## Tests

```text
python -m unittest discover -s tests -v
```

## Sample Website Flow

1. Browse the collection and add two Ceramic Mugs to the bag.
2. Enter `SAVE10` in the promotion field. Two Ceramic Mugs at ₹249 each make a ₹498.00 subtotal; the ₹49.80 discount and ₹22.41 GST bring the total to ₹470.61.
3. Create an account or sign in, review the order, and place it. The receipt shows a new order number and inventory is reduced by two mugs.

The admin account can sign in to `/admin` to maintain the catalog. The console version offers the same main shopping and admin operations through numbered menus.

Sample prices are rounded budget-to-midrange INR estimates for demonstration, not live retailer quotes.

## Future Enhancements

1. Add payment-provider integration, shipping addresses, and order status tracking.
2. Add password reset, stronger account policies, and admin audit logs.
3. Move JSON persistence to a database and deploy behind a production WSGI server."# Shopping-Cart-Management-System" 
