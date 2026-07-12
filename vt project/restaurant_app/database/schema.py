"""
database/schema.py
Creates all database tables and indexes. Safe to call multiple times (IF NOT EXISTS).
"""
from database.connection import Database

SCHEMA_SQL = """
-- USERS
CREATE TABLE IF NOT EXISTS users (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    email                VARCHAR(255) UNIQUE NOT NULL,
    password_hash        VARCHAR(255) NOT NULL,
    full_name            VARCHAR(255) NOT NULL,
    phone                VARCHAR(20),
    address              TEXT,
    role                 TEXT NOT NULL DEFAULT 'customer'
                             CHECK(role IN ('admin','owner','customer')),
    status               TEXT NOT NULL DEFAULT 'active'
                             CHECK(status IN ('active','inactive','locked')),
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login           TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until         TIMESTAMP
);

-- RESTAURANT_OWNERS
CREATE TABLE IF NOT EXISTS restaurant_owners (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                   INTEGER UNIQUE NOT NULL,
    business_name             VARCHAR(255) NOT NULL,
    license_number            VARCHAR(100) UNIQUE NOT NULL,
    license_image_path        TEXT,
    business_registration_path TEXT,
    phone                     VARCHAR(20),
    email                     VARCHAR(255),
    city                      VARCHAR(100),
    state                     VARCHAR(100),
    postal_code               VARCHAR(20),
    verification_status       TEXT NOT NULL DEFAULT 'pending'
                                  CHECK(verification_status IN ('pending','verified','rejected')),
    verification_date         TIMESTAMP,
    verified_by               INTEGER,
    rejection_reason          TEXT,
    rating                    REAL DEFAULT 0,
    total_dishes              INTEGER DEFAULT 0,
    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)     REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by) REFERENCES users(id)
);

-- DISHES
CREATE TABLE IF NOT EXISTS dishes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id              INTEGER NOT NULL,
    name                  VARCHAR(255) NOT NULL,
    description           TEXT,
    category              VARCHAR(100) NOT NULL,
    price                 REAL NOT NULL CHECK(price >= 0),
    current_discount      REAL DEFAULT 0 CHECK(current_discount >= 0 AND current_discount <= 100),
    max_discount_allowed  REAL NOT NULL DEFAULT 30 CHECK(max_discount_allowed >= 0 AND max_discount_allowed <= 100),
    image_path            TEXT,
    thumbnail_path        TEXT,
    status                TEXT NOT NULL DEFAULT 'active'
                              CHECK(status IN ('active','inactive')),
    rating                REAL DEFAULT 0,
    total_orders          INTEGER DEFAULT 0,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES restaurant_owners(id) ON DELETE CASCADE
);

-- ORDERS
CREATE TABLE IF NOT EXISTS orders (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number          VARCHAR(50) UNIQUE NOT NULL,
    customer_id           INTEGER NOT NULL,
    owner_id              INTEGER NOT NULL,
    subtotal              REAL NOT NULL,
    tax                   REAL DEFAULT 0,
    delivery_fee          REAL DEFAULT 0,
    total_amount          REAL NOT NULL,
    discount_applied      REAL DEFAULT 0,
    status                TEXT NOT NULL DEFAULT 'pending'
                              CHECK(status IN ('pending','confirmed','preparing','on_the_way','delivered','cancelled')),
    delivery_address      TEXT NOT NULL,
    payment_method        TEXT NOT NULL
                              CHECK(payment_method IN ('credit_card','debit_card','wallet','cash_on_delivery')),
    payment_status        TEXT NOT NULL DEFAULT 'pending'
                              CHECK(payment_status IN ('pending','completed','failed','refunded')),
    special_instructions  TEXT,
    estimated_delivery_time TIMESTAMP,
    actual_delivery_time  TIMESTAMP,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id),
    FOREIGN KEY (owner_id)    REFERENCES restaurant_owners(id)
);

-- ORDER_ITEMS
CREATE TABLE IF NOT EXISTS order_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id          INTEGER NOT NULL,
    dish_id           INTEGER NOT NULL,
    quantity          INTEGER NOT NULL CHECK(quantity > 0),
    unit_price        REAL NOT NULL,
    discount_at_time  REAL DEFAULT 0,
    subtotal          REAL NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (dish_id)  REFERENCES dishes(id)
);

-- SESSIONS
CREATE TABLE IF NOT EXISTS sessions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    session_token  VARCHAR(255) UNIQUE NOT NULL,
    ip_address     VARCHAR(50),
    user_agent     TEXT,
    login_time     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time    TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- AUDIT_LOG
CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER,
    operation     VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id   INTEGER,
    old_value     TEXT,
    new_value     TEXT,
    timestamp     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address    VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_id INTEGER NOT NULL,
    type         TEXT NOT NULL CHECK(type IN ('email','sms','in_app')),
    subject      VARCHAR(255),
    body         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK(status IN ('pending','sent','failed')),
    sent_at      TIMESTAMP,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipient_id) REFERENCES users(id)
);

-- PRICE_HISTORY
CREATE TABLE IF NOT EXISTS price_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_id      INTEGER NOT NULL,
    old_price    REAL,
    new_price    REAL,
    old_discount REAL,
    new_discount REAL,
    changed_by   INTEGER,
    changed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dish_id)    REFERENCES dishes(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id)
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_users_email       ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role        ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_status      ON users(status);
CREATE INDEX IF NOT EXISTS idx_dishes_owner      ON dishes(owner_id);
CREATE INDEX IF NOT EXISTS idx_dishes_category   ON dishes(category);
CREATE INDEX IF NOT EXISTS idx_dishes_status     ON dishes(status);
CREATE INDEX IF NOT EXISTS idx_orders_customer   ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_owner      ON orders(owner_id);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders(status);
CREATE INDEX IF NOT EXISTS idx_sessions_token    ON sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_user     ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_user        ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_rcv ON notifications(recipient_id);
"""


def create_schema(db: Database):
    """Execute schema SQL against the connected database."""
    conn = db.get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        print("[Schema] All tables and indexes created/verified.")
    finally:
        db.release_connection(conn)


def drop_all(db: Database):
    """Drop everything — used for testing resets."""
    tables = [
        "price_history", "notifications", "audit_log",
        "sessions", "order_items", "orders",
        "dishes", "restaurant_owners", "users"
    ]
    conn = db.get_connection()
    try:
        for tbl in tables:
            conn.execute(f"DROP TABLE IF EXISTS {tbl}")
        conn.commit()
    finally:
        db.release_connection(conn)
