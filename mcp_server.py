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
def read_inventory(tenant_id: str) -> str:
    """Read inventory for a specific tenant.

    Args:
        tenant_id: The ID of the tenant (e.g., 'Tenant_A' or 'Tenant_B').
    """
    sql = "SELECT * FROM inventory WHERE tenant_id = ?"
    log_sql(f"{sql} [param: {tenant_id}]", tenant_id)

    try:
        rows = execute_query(
            sql,
            params=[tenant_id]
        )
    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps(rows)

if __name__ == "__main__":
    mcp.run()
