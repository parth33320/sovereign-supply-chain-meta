"""
init_db.py - Initializes and seeds the supply chain inventory database.
Supports PostgreSQL (via POSTGRES_DB_URI) with SQLite fallback (mock_sap.db).
Seeds 20 items per tenant (Tenant_A and Tenant_B) with diverse SKUs
and at least 2 zero-quantity items per tenant to trigger the A2A negotiation demo path.
"""

import os
import sqlite3
from typing import List, Tuple

try:
    import psycopg
    from psycopg.rows import dict_row
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False

from db import is_postgres_configured, get_db_connection

SEED_DATA: List[Tuple[str, str, int, int, float, str]] = [
    # --- Tenant A (Electronics & Industrial Hardware) ---
    ('Tenant_A', 'Widget-A', 50, 7, 8.20, 'SUP_APEX'),
    ('Tenant_A', 'Semiconductors', 500, 14, 1500.50, 'SUP_001'),
    ('Tenant_A', 'Copper Wire Spools', 2000, 7, 300.00, 'SUP_002'),
    ('Tenant_A', 'Lithium Batteries', 100, 21, 2500.00, 'SUP_003'),
    ('Tenant_A', 'Structural Steel Plates', 10000, 30, 800.25, 'SUP_004'),
    ('Tenant_A', 'Polymer Resin Pellets', 5000, 5, 120.00, 'SUP_005'),
    ('Tenant_A', 'Aluminum Extrusions', 3200, 10, 410.00, 'SUP_011'),
    ('Tenant_A', 'Ceramic Capacitors', 50000, 4, 15.00, 'SUP_012'),
    ('Tenant_A', 'Optical Sensors', 1200, 8, 220.00, 'SUP_013'),
    ('Tenant_A', 'Microcontrollers 32-bit', 0, 18, 95.00, 'SUP_014'),    # Stockout (Qty = 0)
    ('Tenant_A', 'Hydraulic Actuators', 0, 25, 1450.00, 'SUP_015'),      # Stockout (Qty = 0)
    ('Tenant_A', 'Industrial Control Panels', 45, 12, 4800.00, 'SUP_016'),
    ('Tenant_A', 'Brushless DC Motors', 850, 15, 340.00, 'SUP_017'),
    ('Tenant_A', 'Digital Multimeters', 600, 6, 85.00, 'SUP_018'),
    ('Tenant_A', 'Solar Inverter Modules', 250, 14, 1890.00, 'SUP_019'),
    ('Tenant_A', 'Thermal Imaging Units', 80, 20, 3100.00, 'SUP_020'),
    ('Tenant_A', 'Anti-Static ESD Bags', 15000, 3, 12.50, 'SUP_021'),
    ('Tenant_A', 'Reinforced Corrugated Cartons', 6000, 4, 18.00, 'SUP_022'),
    ('Tenant_A', 'Thermal Interface Paste', 3000, 5, 45.00, 'SUP_023'),
    ('Tenant_A', 'Foam Cushion Inserts', 4500, 4, 22.00, 'SUP_024'),
    ('Tenant_A', 'Heavy-Duty Pallet Wrap', 800, 2, 65.00, 'SUP_025'),

    # --- Tenant B (Apparel, Textiles & Soft Goods) ---
    ('Tenant_B', 'Organic Cotton Yarn', 3000, 10, 200.00, 'SUP_006'),
    ('Tenant_B', 'Synthetic Textile Dye', 500, 12, 450.75, 'SUP_007'),
    ('Tenant_B', 'Heavy-Duty Metal Zippers', 10000, 5, 50.00, 'SUP_008'),
    ('Tenant_B', 'Raw Indigo Denim Fabric', 1500, 15, 600.00, 'SUP_009'),
    ('Tenant_B', 'Waterproof Membrane Rolls', 800, 14, 750.00, 'SUP_026'),
    ('Tenant_B', 'Recycled Polyester Fiber', 4000, 9, 180.00, 'SUP_027'),
    ('Tenant_B', 'Elastic Waistband Webbing', 0, 7, 35.00, 'SUP_028'),    # Stockout (Qty = 0)
    ('Tenant_B', 'Brass Snap Buttons', 0, 11, 40.00, 'SUP_029'),          # Stockout (Qty = 0)
    ('Tenant_B', 'Merino Wool Roving', 900, 16, 920.00, 'SUP_030'),
    ('Tenant_B', 'Reflective Safety Strips', 2200, 6, 85.00, 'SUP_031'),
    ('Tenant_B', 'All-Weather Technical Parkas', 350, 14, 210.00, 'SUP_032'),
    ('Tenant_B', 'Reinforced Workwear Trousers', 1200, 10, 85.00, 'SUP_033'),
    ('Tenant_B', 'High-Visibility Safety Vests', 2500, 5, 28.00, 'SUP_034'),
    ('Tenant_B', 'Insulated Thermal Gloves', 1800, 8, 42.00, 'SUP_035'),
    ('Tenant_B', 'Steel-Toe Tactical Boots', 600, 12, 145.00, 'SUP_036'),
    ('Tenant_B', 'Recyclable Shipping Boxes', 8000, 3, 20.00, 'SUP_010'),
    ('Tenant_B', 'Biodegradable Garment Polybags', 12000, 2, 8.50, 'SUP_037'),
    ('Tenant_B', 'Branded Kraft Hangtags', 25000, 4, 5.00, 'SUP_038'),
    ('Tenant_B', 'Moisture Absorber Desiccant Packs', 10000, 3, 14.00, 'SUP_039'),
    ('Tenant_B', 'Reinforced Gummed Paper Tape', 1500, 2, 32.00, 'SUP_040'),
]


def init_sqlite():
    conn = sqlite3.connect('mock_sap.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            transit_time INTEGER NOT NULL,
            spot_rate REAL NOT NULL,
            supplier_id TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_inv_tenant_qty ON inventory(tenant_id, quantity);
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            status TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            action TEXT NOT NULL,
            item_id INTEGER,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            transit_time INTEGER NOT NULL,
            spot_rate REAL NOT NULL,
            supplier_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dpo_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT,
            chosen TEXT,
            rejected TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('DELETE FROM inventory')
    cursor.executemany('''
        INSERT INTO inventory (tenant_id, item_name, quantity, transit_time, spot_rate, supplier_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', SEED_DATA)

    conn.commit()
    conn.close()
    print(f"SQLite (mock_sap.db) initialized with {len(SEED_DATA)} inventory records.")


def init_postgres(db_uri: str):
    conn = psycopg.connect(db_uri, autocommit=True)
    with conn.cursor() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                transit_time INTEGER NOT NULL,
                spot_rate DOUBLE PRECISION NOT NULL,
                supplier_id TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_inv_tenant_qty ON inventory(tenant_id, quantity);
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_queue (
                id SERIAL PRIMARY KEY,
                request_id TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_requests (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                action TEXT NOT NULL,
                item_id INTEGER,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                transit_time INTEGER NOT NULL,
                spot_rate DOUBLE PRECISION NOT NULL,
                supplier_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dpo_logs (
                id SERIAL PRIMARY KEY,
                prompt TEXT,
                chosen TEXT,
                rejected TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('DELETE FROM inventory')
        cursor.executemany('''
            INSERT INTO inventory (tenant_id, item_name, quantity, transit_time, spot_rate, supplier_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', SEED_DATA)

    conn.close()
    print(f"PostgreSQL initialized with {len(SEED_DATA)} inventory records.")


def init_db():
    init_sqlite()

    # Always initialize portfolio database and seed demo data unconditionally
    try:
        from portfolio import init_portfolio_db
        init_portfolio_db()
    except Exception as e:
        print(f"Warning: Failed to initialize portfolio DB ({e}).")

    db_uri = os.environ.get("POSTGRES_DB_URI")
    if db_uri and db_uri.strip() and HAS_PSYCOPG:
        try:
            init_postgres(db_uri)
        except Exception as e:
            print(f"Warning: Failed to initialize PostgreSQL ({e}). Continuing with SQLite fallback.")


if __name__ == '__main__':
    init_db()
