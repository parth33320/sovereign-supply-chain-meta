import re
import json
from mcp.server.fastmcp import FastMCP
from db import execute_query, execute_mutation, get_db_connection

mcp = FastMCP("ZeroTrustLogistics")

def is_safe_query(query: str) -> bool:
    unsafe_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
    upper_query = query.upper()
    for keyword in unsafe_keywords:
        if re.search(rf"\b{keyword}\b", upper_query):
            return False
    return True

def log_sql(query: str, tenant_id: str):
    conn, engine = get_db_connection()
    try:
        if engine == "postgres":
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS mcp_sql_logs (id SERIAL PRIMARY KEY, query TEXT, tenant_id TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
                cur.execute("INSERT INTO mcp_sql_logs (query, tenant_id) VALUES (%s, %s)", (query, tenant_id))
        else:
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS mcp_sql_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT, tenant_id TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            cur.execute("INSERT INTO mcp_sql_logs (query, tenant_id) VALUES (?, ?)", (query, tenant_id))
            conn.commit()
    finally:
        conn.close()

@mcp.tool()
def read_inventory(tenant_id: str,
                   low_stock_only: bool = False,
                   limit: int = 50) -> str:
    base = "SELECT id, item_name, quantity, transit_time, spot_rate, supplier_id, tenant_id FROM inventory WHERE tenant_id = ?"
    params = [tenant_id]
    if low_stock_only:
        base += " AND quantity < 100"
    base += f" ORDER BY quantity ASC LIMIT {limit}"
    rows = execute_query(base, params=params)
    return json.dumps(rows)

if __name__ == "__main__":
    mcp.run()
