from fastapi import FastAPI, Response
from db import get_db_connection

app = FastAPI()

@app.get("/health")
def health(response: Response):
    try:
        conn, engine = get_db_connection()
        conn.close()
        return {"status": "ok", "db": engine}
    except Exception as e:
        response.status_code = 500
        return {"status": "error", "detail": str(e)}
