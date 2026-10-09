import hashlib
from abc import ABC, abstractmethod

format_price = lambda value: f"{value:.2f}грн"
hash_password = lambda text: hashlib.sha256(text.encode()).hexdigest()
line_sum = lambda line: line[0].price * line[1]

ADMIN_PASSWORD_HASH = hash_password("050110")
LOW_STOCK_LIMIT = 5


class Product(ABC):
    def __init__(self, product_id, name, price, stock):
        self._id = product_id
        self._name = name
        self._price = price
        self._stock = stock

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def price(self):
        return self._price

    @property
    def stock(self):
        return self._stock

    def has_stock(self, qty):
        return self._stock >= qty

    def reduce_stock(self, qty):
        if not self.has_stock(qty):
            raise ValueError(f"Недостатньо товару «{self._name}» на складі")
        self._stock -= qty

    def increase_stock(self, qty):
        self._stock += qty

    @abstractmethod
    def details(self):
        ...

    def __str__(self):
        return f"[{self._id}] {self._name:<22} {format_price(self._price):>12}  | {self.details()}"


class Food(Product):
    def __init__(self, product_id, name, price, stock, shelf_life_days):
        super().__init__(product_id, name, price, stock)
        self._shelf_life_days = shelf_life_days

    def details(self):
        return f"термін придатності: {self._shelf_life_days} дн."


class Electronics(Product):
    def __init__(self, product_id, name, price, stock, warranty_months):
        super().__init__(product_id, name, price, stock)
        self._warranty_months = warranty_months

    def details(self):
        return f"гарантія: {self._warranty_months} міс."


class Clothing(Product):
    def __init__(self, product_id, name, price, stock, size):
        super().__init__(product_id, name, price, stock)
        self._size = size

    def details(self):
        return f"розмір: {self._size}"


class Catalog:
    def __init__(self, products):
        self._products = {p.id: p for p in products}

    def all(self):
        return sorted(self._products.values(), key=lambda p: p.id)

    def available(self):
        return list(filter(lambda p: p.stock > 0, self.all()))

    def low_stock(self):
        return list(filter(lambda p: p.stock <= LOW_STOCK_LIMIT, self.all()))

    def get(self, product_id):
        return self._products.get(product_id)


class Cart:
    def __init__(self):
        self._items = {}

    def quantity_of(self, product):
        return self._items[product.id][1] if product.id in self._items else 0

    def add(self, product, qty):
        if qty <= 0:
            raise ValueError("Кількість має бути більшою за 0")
        if not product.has_stock(self.quantity_of(product) + qty):
            raise ValueError(f"На складі лише {product.stock} шт. товару «{product.name}»")
        self._items[product.id] = (product, self.quantity_of(product) + qty)

    def remove(self, product_id, qty=None):
        if product_id not in self._items:
            raise ValueError("Такого товару немає в кошику")
        product, current = self._items[product_id]
        if qty is None or qty >= current:
            del self._items[product_id]
        elif qty > 0:
            self._items[product_id] = (product, current - qty)
        else:
            raise ValueError("Кількість має бути більшою за 0")

    def lines(self):
        return sorted(self._items.values(), key=lambda line: line[0].id)

    def is_empty(self):
        return not self._items

    def total(self):
        return sum(map(line_sum, self.lines()))

    def clear(self):
        self._items.clear()


class User(ABC):
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    @abstractmethod
    def menu(self, shop):
        ...


class Customer(User):
    def __init__(self, name):
        super().__init__(name)
        self._cart = Cart()

    @property
    def cart(self):
        return self._cart

    def menu(self, shop):
        return {
            "1": ("Переглянути каталог", lambda: shop.show_catalog()),
            "2": ("Додати товар у кошик", lambda: shop.add_to_cart(self)),
            "3": ("Переглянути кошик", lambda: shop.show_cart(self)),
            "4": ("Видалити товар з кошика", lambda: shop.remove_from_cart(self)),
            "5": ("Купити товари з кошика", lambda: shop.checkout(self)),
        }


class Admin(User):
    def menu(self, shop):
        return {
            "1": ("Переглянути залишки", lambda: shop.show_stock()),
            "2": ("Поповнити залишки", lambda: shop.restock()),
            "3": ("Товари, що закінчуються", lambda: shop.show_low_stock()),
        }


class Shop:
    def __init__(self, catalog):
        self._catalog = catalog

    @staticmethod
    def _read_int(prompt):
        try:
            return int(input(prompt).strip())
        except ValueError:
            raise ValueError("Потрібно ввести ціле число")

    def _read_product(self):
        product = self._catalog.get(self._read_int("ID товару: "))
        if product is None:
            raise ValueError("Товару з таким ID не існує")
        return product

    def show_catalog(self):
        print("\n=== КАТАЛОГ ТОВАРІВ ===")
        items = self._catalog.available()
        if not items:
            print("Каталог порожній")
        for p in items:
            print(p)

    def add_to_cart(self, customer):
        self.show_catalog()
        product = self._read_product()
        customer.cart.add(product, self._read_int("Кількість: "))
        print(f"✔ «{product.name}» додано в кошик")

    def show_cart(self, customer):
        print("\n=== КОШИК ===")
        if customer.cart.is_empty():
            print("Кошик порожній")
            return
        for product, qty in customer.cart.lines():
            print(f"[{product.id}] {product.name:<22} {qty} x {format_price(product.price)}"
                  f" = {format_price(line_sum((product, qty)))}")
        print(f"РАЗОМ: {format_price(customer.cart.total())}")

    def remove_from_cart(self, customer):
        self.show_cart(customer)
        if customer.cart.is_empty():
            return
        product_id = self._read_int("ID товару для видалення: ")
        qty_text = input("Скільки видалити (Enter — повністю): ").strip()
        customer.cart.remove(product_id, int(qty_text) if qty_text else None)
        print("✔ Кошик оновлено")

    def checkout(self, customer):
        if customer.cart.is_empty():
            print("Кошик порожній — нічого купувати")
            return
        self.show_cart(customer)
        if input("Підтвердити покупку? (т/н): ").strip().lower() not in ("т", "y", "так"):
            print("Покупку скасовано")
            return
        lines = customer.cart.lines()
        if not all(map(lambda line: line[0].has_stock(line[1]), lines)):
            raise ValueError("Деяких товарів вже недостатньо на складі")
        for product, qty in lines:
            product.reduce_stock(qty)
        print(f"✔ Дякуємо за покупку, {customer.name}! Сплачено: {format_price(customer.cart.total())}")
        customer.cart.clear()

    def show_stock(self):
        print("\n=== ЗАЛИШКИ НА СКЛАДІ ===")
        for p in self._catalog.all():
            print(f"[{p.id}] {p.name:<22} {p.stock:>4} шт.   {format_price(p.price):>12}")
        total_value = sum(map(lambda p: p.price * p.stock, self._catalog.all()))
        print(f"Загальна вартість залишків: {format_price(total_value)}")

    def show_low_stock(self):
        print(f"\n=== ЗАЛИШОК ≤ {LOW_STOCK_LIMIT} шт. ===")
        items = self._catalog.low_stock()
        if not items:
            print("Усього достатньо")
        for p in items:
            print(f"[{p.id}] {p.name:<22} {p.stock} шт.")

    def restock(self):
        self.show_stock()
        product = self._read_product()
        qty = self._read_int("Скільки додати: ")
        if qty <= 0:
            raise ValueError("Кількість має бути більшою за 0")
        product.increase_stock(qty)
        print(f"✔ Тепер «{product.name}»: {product.stock} шт.")

    def _run_menu(self, user):
        while True:
            actions = user.menu(self)
            print(f"\n--- Меню ({user.name}) ---")
            for key, (title, _) in actions.items():
                print(f"{key}. {title}")
            print("0. Вийти")
            choice = input("Ваш вибір: ").strip()
            if choice == "0":
                return
            if choice not in actions:
                print("Невірний пункт меню")
                continue
            try:
                actions[choice][1]()
            except ValueError as error:
                print(f"✖ Помилка: {error}")

    def _admin_login(self):
        for attempt in range(3, 0, -1):
            if hash_password(input("Пароль адміністратора: ")) == ADMIN_PASSWORD_HASH:
                return True
            print(f"✖ Невірний пароль. Залишилось спроб: {attempt - 1}")
        return False

    def run(self):
        print("Ласкаво просимо до міні-магазину!")
        entries = {
            "1": ("Увійти як покупець", lambda: self._run_menu(Customer(input("Ваше ім'я: ").strip() or "Гість"))),
            "2": ("Увійти як адміністратор", lambda: self._run_menu(Admin("Адміністратор")) if self._admin_login() else None),
        }
        while True:
            print("\n=== ГОЛОВНЕ МЕНЮ ===")
            for key, (title, _) in entries.items():
                print(f"{key}. {title}")
            print("0. Вихід")
            choice = input("Ваш вибір: ").strip()
            if choice == "0":
                print("До побачення!")
                return
            entries.get(choice, ("", lambda: print("Невірний пункт меню")))[1]()


def create_catalog():
    return Catalog([
        Food(1, "Шоколад чорний", 45.50, 20, 180),
        Food(2, "Кава в зернах 250г", 189.99, 8, 365),
        Electronics(3, "Навушники", 799.00, 5, 12),
        Electronics(4, "Powerbank 10000", 650.00, 3, 24),
        Clothing(5, "Футболка біла", 299.90, 12, "M"),
        Clothing(6, "Кепка", 150.00, 2, "універсальний"),
    ])


if __name__ == "__main__":
    Shop(create_catalog()).run()