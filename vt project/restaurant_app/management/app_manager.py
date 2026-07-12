"""
management/app_manager.py
High-level application orchestrator for configuration, database, sessions,
and service wiring.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from business_logic.auth import hash_password
from business_logic.service import RestaurantService
from management.config_manager import ConfigManager
from management.db_manager import DBManager
from management.error_handler import handle
from management.event_bus import clear_all, publish, subscribe
from management.session_manager import SessionManager

log = logging.getLogger("restaurant_app.app")


@dataclass
class MCPSettings:
    enabled: bool = False
    email_enabled: bool = False
    sms_enabled: bool = False
    email_endpoint: str | None = None
    sms_endpoint: str | None = None


class MCPManager:
    """
    Lightweight notification gateway placeholder.

    The current codebase does not have an MCP client implementation yet, so
    this class keeps the integration point explicit and safely no-ops when the
    feature is disabled.
    """

    def __init__(self, mcp_config: dict | None = None):
        mcp_config = mcp_config or {}
        self._settings = MCPSettings(
            enabled=bool(mcp_config.get("enabled", False)),
            email_enabled=bool(mcp_config.get("email_service", {}).get("enabled", False)),
            sms_enabled=bool(mcp_config.get("sms_service", {}).get("enabled", False)),
            email_endpoint=mcp_config.get("email_service", {}).get("endpoint"),
            sms_endpoint=mcp_config.get("sms_service", {}).get("endpoint"),
        )

    @property
    def settings(self) -> MCPSettings:
        return self._settings

    def send_email(self, recipient: str, subject: str, body: str,
                   template_name: str | None = None) -> dict:
        if not self._settings.enabled or not self._settings.email_enabled:
            log.debug("MCP email skipped because the service is disabled.")
            return {"success": False, "error": "Email service disabled."}

        log.info("MCP email queued to %s with subject %s", recipient, subject)
        return {
            "success": True,
            "data": {
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "template_name": template_name,
                "endpoint": self._settings.email_endpoint,
            },
        }

    def send_sms(self, recipient_phone: str, message: str) -> dict:
        if not self._settings.enabled or not self._settings.sms_enabled:
            log.debug("MCP SMS skipped because the service is disabled.")
            return {"success": False, "error": "SMS service disabled."}

        log.info("MCP SMS queued to %s", recipient_phone)
        return {
            "success": True,
            "data": {
                "recipient_phone": recipient_phone,
                "message": message,
                "endpoint": self._settings.sms_endpoint,
            },
        }


class AppManager:
    """Coordinates configuration, database, business logic, and sessions."""

    _instance: "AppManager | None" = None

    def __new__(cls, config_path: str | None = None):
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._config_path = config_path
            inst._initialised = False
            inst._config: ConfigManager | None = None
            inst._db_manager: DBManager | None = None
            inst._service: RestaurantService | None = None
            inst._sessions: SessionManager | None = None
            inst._mcp: MCPManager | None = None
            cls._instance = inst
        elif config_path and cls._instance._config_path != config_path:
            cls._instance._config_path = config_path
            cls._instance._initialised = False
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    # ------------------------------------------------------------------ setup

    def initialise(self) -> "AppManager":
        """Load config, connect DB, wire managers, and register event hooks."""
        if self._initialised:
            return self

        self._config = ConfigManager(self._config_path)
        self._db_manager = DBManager(self._config.sqlite_path())
        db = self._db_manager.initialise()
        self._bootstrap_demo_admin(db)

        self._sessions = SessionManager(self._config.session_timeout_minutes())
        self._service = RestaurantService(db, password_min_length=self._config.password_min_length())
        self._mcp = MCPManager(self._config.mcp)

        clear_all()
        self._register_event_handlers()
        self._initialised = True
        log.info("Application initialised: %s", self.app_name)
        return self

    def _ensure_ready(self) -> None:
        if not self._initialised:
            self.initialise()

    def _register_event_handlers(self) -> None:
        subscribe("user.registered", self._on_user_registered)
        subscribe("owner.verified", self._on_owner_verified)
        subscribe("order.created", self._on_order_created)
        subscribe("order.status_changed", self._on_order_status_changed)

    def _bootstrap_demo_admin(self, db) -> None:
        """
        Keep the local demo admin account consistent so the GUI always has a
        known login even if the SQLite file was edited manually.
        """
        admin_email = "admin@gmail.com"
        admin_password = "admin121"
        admin = db.fetchone("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
        if admin:
            db.execute(
                """UPDATE users
                   SET email = ?, password_hash = ?, full_name = ?, status = 'active',
                       failed_login_attempts = 0, locked_until = NULL, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (admin_email, hash_password(admin_password), "Admin", admin["id"]),
            )
            return

        db.execute(
            """INSERT INTO users
               (email, password_hash, full_name, role, status, failed_login_attempts)
               VALUES (?, ?, ?, 'admin', 'active', 0)""",
            (admin_email, hash_password(admin_password), "Admin"),
        )

    def seed_demo_data(self) -> dict:
        """
        Create a demo owner account and a small menu if they do not already exist.

        The method is safe to run multiple times. Existing demo rows are reused.
        """
        self._ensure_ready()
        db = self.database

        admin = db.fetchone(
            "SELECT id FROM users WHERE email = ? AND role = 'admin' ORDER BY id LIMIT 1",
            ("admin@gmail.com",),
        )
        admin_id = admin["id"] if admin else None

        created_dishes: list[str] = []

        def ensure_owner_account(*, full_name: str, email: str, password: str,
                                 business_name: str, license_number: str,
                                 phone: str, address: str, city: str,
                                 state: str, postal_code: str) -> tuple[dict, dict, bool]:
            user = self.service.user_dao.get_user_by_email(email)
            created = False
            if not user:
                account = self.service.register_account(
                    full_name=full_name,
                    email=email,
                    password=password,
                    role="owner",
                    phone=phone,
                    address=address,
                    business_name=business_name,
                    license_number=license_number,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                )
                user = account["user"]
                created = True
            owner = self.service.owner_dao.get_owner_by_user_id(user["id"])
            if owner and owner.get("verification_status") != "verified":
                self.service.owner_dao.update_verification_status(
                    owner["id"], "verified", verified_by=admin_id
                )
                owner = self.service.owner_dao.get_owner_by_id(owner["id"])
            return user, owner, created

        def ensure_dishes(owner_user: dict, owner: dict, menu: list[dict]) -> None:
            for item in menu:
                existing = db.fetchone(
                    "SELECT id FROM dishes WHERE owner_id = ? AND name = ?",
                    (owner["id"], item["name"]),
                )
                if existing:
                    continue
                self.service.create_dish(
                    actor_user_id=owner_user["id"],
                    actor_role="owner",
                    name=item["name"],
                    category=item["category"],
                    price=item["price"],
                    description=item["description"],
                    max_discount=item["max_discount"],
                )
                created_dishes.append(item["name"])

        owner_user_1, owner_1, created_owner_1 = ensure_owner_account(
            full_name="Aarav Mehta",
            email="saffron.garden@example.com",
            password="owner1234",
            business_name="Saffron Garden",
            license_number="SG-2026-001",
            phone="+91-9876543210",
            address="22 MG Road, Pune",
            city="Pune",
            state="Maharashtra",
            postal_code="411001",
        )
        ensure_dishes(owner_user_1, owner_1, [
            {"name": "Paneer Tikka", "category": "appetizers", "price": 249.00,
             "description": "Char-grilled paneer with mint chutney and onions.", "max_discount": 20},
            {"name": "Butter Chicken", "category": "mains", "price": 399.00,
             "description": "Creamy tomato gravy with tender chicken and naan pairing.", "max_discount": 15},
            {"name": "Veg Biryani", "category": "specials", "price": 279.00,
             "description": "Aromatic basmati rice layered with seasonal vegetables.", "max_discount": 18},
            {"name": "Chocolate Lava Cake", "category": "desserts", "price": 179.00,
             "description": "Warm chocolate cake with a molten center.", "max_discount": 10},
        ])

        owner_user_2, owner_2, created_owner_2 = ensure_owner_account(
            full_name="Nisha Rao",
            email="coastal.bowl@example.com",
            password="owner5678",
            business_name="Coastal Bowl",
            license_number="CB-2026-014",
            phone="+91-9988776655",
            address="14 Marine Drive, Mumbai",
            city="Mumbai",
            state="Maharashtra",
            postal_code="400020",
        )
        ensure_dishes(owner_user_2, owner_2, [
            {"name": "Fish Curry Rice", "category": "mains", "price": 349.00,
             "description": "Home-style coastal curry with steamed rice.", "max_discount": 12},
            {"name": "Prawn Fry", "category": "seafood", "price": 429.00,
             "description": "Spiced prawns pan-fried with curry leaves.", "max_discount": 10},
            {"name": "Mango Shake", "category": "beverages", "price": 129.00,
             "description": "Fresh mango milkshake served chilled.", "max_discount": 5},
        ])

        owner_user_3, owner_3, created_owner_3 = ensure_owner_account(
            full_name="Sophia Rossi",
            email="pasta.project@example.com",
            password="ownerpasta123",
            business_name="The Pasta Project",
            license_number="PP-2026-009",
            phone="+39-02-1234567",
            address="7 Via Roma, Milan",
            city="Milan",
            state="Lombardy",
            postal_code="20121",
        )
        ensure_dishes(owner_user_3, owner_3, [
            {"name": "Margherita Pizza", "category": "pizza", "price": 299.00,
             "description": "Fresh mozzarella, basil, and plum tomato sauce.", "max_discount": 15},
            {"name": "Fettuccine Alfredo", "category": "pasta", "price": 349.00,
             "description": "Rich and creamy parmesan sauce with garlic.", "max_discount": 10},
            {"name": "Tiramisu", "category": "desserts", "price": 199.00,
             "description": "Espresso-soaked ladyfingers with mascarpone cream.", "max_discount": 20},
            {"name": "Garlic Bread", "category": "sides", "price": 129.00,
             "description": "Toasted baguette with garlic butter and herbs.", "max_discount": 5},
            {"name": "Bruschetta", "category": "appetizers", "price": 149.00,
             "description": "Fresh tomatoes, garlic, and basil on toasted bread.", "max_discount": 12},
        ])

        owner_user_4, owner_4, created_owner_4 = ensure_owner_account(
            full_name="Kenji Tanaka",
            email="wok.roll@example.com",
            password="ownerwok123",
            business_name="Wok & Roll",
            license_number="WR-2026-037",
            phone="+81-3-9876-5432",
            address="3-chome Shinjuku, Tokyo",
            city="Tokyo",
            state="Tokyo",
            postal_code="160-0022",
        )
        ensure_dishes(owner_user_4, owner_4, [
            {"name": "Chicken Hakka Noodles", "category": "mains", "price": 269.00,
             "description": "Stir-fried noodles with crisp veggies and chicken.", "max_discount": 15},
            {"name": "Dim Sum Basket", "category": "appetizers", "price": 189.00,
             "description": "Steamed chicken and chive dumplings with chili oil.", "max_discount": 10},
            {"name": "Spring Rolls", "category": "appetizers", "price": 139.00,
             "description": "Crispy wrapper filled with seasoned vegetables.", "max_discount": 8},
            {"name": "Thai Green Curry", "category": "specials", "price": 329.00,
             "description": "Fragrant coconut milk curry with chicken and basil.", "max_discount": 12},
            {"name": "Jasmine Rice", "category": "sides", "price": 99.00,
             "description": "Steamed aromatic jasmine rice.", "max_discount": 5},
        ])

        owner_user_5, owner_5, created_owner_5 = ensure_owner_account(
            full_name="Marcus Miller",
            email="burger.bistro@example.com",
            password="ownerburger123",
            business_name="Burger Bistro",
            license_number="BB-2026-088",
            phone="+1-212-555-0199",
            address="456 Broadway, New York",
            city="New York",
            state="NY",
            postal_code="10013",
        )
        ensure_dishes(owner_user_5, owner_5, [
            {"name": "Classic Cheeseburger", "category": "burgers", "price": 249.00,
             "description": "Flame-grilled beef patty with cheddar cheese and house sauce.", "max_discount": 15},
            {"name": "BBQ Bacon Burger", "category": "burgers", "price": 299.00,
             "description": "Gourmet beef patty with crispy bacon and smoky BBQ sauce.", "max_discount": 10},
            {"name": "Truffle Fries", "category": "sides", "price": 149.00,
             "description": "Crispy golden fries tossed in truffle oil and parmesan.", "max_discount": 8},
            {"name": "Onion Rings", "category": "appetizers", "price": 119.00,
             "description": "Beer-battered crispy thick-cut onion rings.", "max_discount": 5},
            {"name": "Vanilla Bean Milkshake", "category": "beverages", "price": 159.00,
             "description": "Creamy premium vanilla bean shake.", "max_discount": 5},
        ])

        customer_email = "maya.customer@example.com"
        customer_password = "customer123"
        customer_user = self.service.user_dao.get_user_by_email(customer_email)
        created_customer = False
        if not customer_user:
            customer_user = self.service.register_user(
                email=customer_email,
                password=customer_password,
                full_name="Maya Patel",
                role="customer",
                phone="+91-9123456780",
                address="88 Park Street, Kolkata",
            )
            created_customer = True

        if not db.fetchone("SELECT id FROM orders WHERE customer_id = ?", (customer_user["id"],)):
            dish_rows = db.fetchall(
                """SELECT d.id
                   FROM dishes d
                   JOIN restaurant_owners ro ON d.owner_id = ro.id
                   WHERE ro.business_name = ? AND d.status = 'active'
                   ORDER BY d.id ASC
                   LIMIT 2""",
                ("Saffron Garden",),
            )
            if dish_rows:
                cart_items = [{"dish_id": row["id"], "quantity": 1} for row in dish_rows]
                self.service.create_order(
                    customer_id=customer_user["id"],
                    cart_items=cart_items,
                    delivery_address="88 Park Street, Kolkata",
                    payment_method="cash_on_delivery",
                    special_instructions="Ring the bell twice.",
                )

        return {
            "success": True,
            "data": {
                "created_owner_1": created_owner_1,
                "created_owner_2": created_owner_2,
                "created_owner_3": created_owner_3,
                "created_owner_4": created_owner_4,
                "created_owner_5": created_owner_5,
                "created_customer": created_customer,
                "created_dishes": created_dishes,
                "owner_accounts": [
                    {"email": owner_user_1["email"], "business_name": owner_1["business_name"]},
                    {"email": owner_user_2["email"], "business_name": owner_2["business_name"]},
                    {"email": owner_user_3["email"], "business_name": owner_3["business_name"]},
                    {"email": owner_user_4["email"], "business_name": owner_4["business_name"]},
                    {"email": owner_user_5["email"], "business_name": owner_5["business_name"]},
                ],
                "customer_email": customer_email,
                "sample_passwords": {
                    "owner_1": "owner1234",
                    "owner_2": "owner5678",
                    "owner_3": "ownerpasta123",
                    "owner_4": "ownerwok123",
                    "owner_5": "ownerburger123",
                    "customer": customer_password,
                },
            },
        }

    # ------------------------------------------------------------------ events

    def _on_user_registered(self, **payload: Any) -> None:
        user = payload.get("user") or {}
        email = user.get("email")
        if email:
            self._mcp.send_email(
                email,
                "Welcome to Restaurant Management System",
                "Your account has been created successfully.",
            )

    def _on_owner_verified(self, **payload: Any) -> None:
        owner = payload.get("owner") or {}
        user = owner.get("user") or {}
        email = user.get("email") or owner.get("email")
        if email:
            status = owner.get("verification_status", "verified")
            self._mcp.send_email(
                email,
                "Owner Verification Update",
                f"Your restaurant owner profile is now {status}.",
            )

    def _on_order_created(self, **payload: Any) -> None:
        order = payload.get("order") or {}
        log.info("Observed order.created event for order %s", order.get("id"))

    def _on_order_status_changed(self, **payload: Any) -> None:
        order = payload.get("order") or {}
        log.info(
            "Observed order.status_changed event for order %s -> %s",
            order.get("id"),
            order.get("status"),
        )

    # ------------------------------------------------------------------ public

    @property
    def app_name(self) -> str:
        self._ensure_ready()
        return self._config.app.get("name", "Restaurant Management System")

    @property
    def version(self) -> str:
        self._ensure_ready()
        return self._config.app.get("version", "1.0.0")

    @property
    def service(self) -> RestaurantService:
        self._ensure_ready()
        return self._service

    @property
    def database(self):
        self._ensure_ready()
        return self._db_manager.db

    @property
    def config(self) -> ConfigManager:
        self._ensure_ready()
        return self._config

    @property
    def mcp(self) -> MCPManager:
        self._ensure_ready()
        return self._mcp

    def start(self) -> dict:
        """Initialise the application and return a startup summary."""
        self.initialise()
        return {
            "success": True,
            "data": {
                "app_name": self.app_name,
                "version": self.version,
                "window_size": self._config.window_size(),
                "database_path": self._db_manager._path,
                "database_health": self._db_manager.ping(),
                "stats": self._db_manager.get_stats(),
            },
        }

    def login(self, email: str, password: str, ip_address: str = None,
              user_agent: str = None) -> dict:
        """Authenticate and create both in-memory and persisted sessions."""
        self._ensure_ready()
        try:
            user = self._service.login(email, password)
            token = self._sessions.create_session(user)
            self._service.session_dao.create_session(
                user["id"], token, ip_address=ip_address, user_agent=user_agent
            )
            return {
                "success": True,
                "data": {
                    "user": user,
                    "session_token": token,
                },
            }
        except Exception as exc:  # noqa: BLE001
            return handle(exc, context="login", user_id=None)

    def logout(self, token: str) -> dict:
        """Terminate a session in memory and in the sessions table."""
        self._ensure_ready()
        try:
            removed = self._sessions.end_session(token)
            self._service.session_dao.end_session(token)
            return {"success": True, "data": {"removed": removed}}
        except Exception as exc:  # noqa: BLE001
            return handle(exc, context="logout")

    def validate_session(self, token: str) -> dict:
        """Return the current session payload, raising on invalid tokens."""
        self._ensure_ready()
        session = self._sessions.get_session(token)
        return session.to_dict()

    def current_user(self, token: str) -> dict:
        """Return the safe user payload for a session token."""
        self._ensure_ready()
        return self._sessions.get_current_user(token)

    def get_active_sessions(self) -> list[dict]:
        """Return active sessions from the in-memory store."""
        self._ensure_ready()
        return self._sessions.get_active_sessions()

    def get_dashboard_summary(self) -> dict:
        """Combine DB counts and session info for a simple dashboard snapshot."""
        self._ensure_ready()
        stats = self._db_manager.get_stats()
        stats["active_sessions"] = len(self._sessions.get_active_sessions())
        stats["app_name"] = self.app_name
        stats["version"] = self.version
        return stats

    def shutdown(self) -> dict:
        """Release connections and reset ephemeral state."""
        if self._initialised:
            SessionManager.reset()
            self._db_manager.close()
            self._initialised = False
            log.info("Application shutdown complete.")
        return {"success": True}
