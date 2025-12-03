from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import os
from typing import List, Optional
from ..config import DB_FILE, LOG_FILE

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Bedel AI Dashboard API")

# Mount Static Files
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse('src/api/static/index.html')

class Product(BaseModel):
    name: str
    price: int
    description: str

class PromptUpdate(BaseModel):
    content: str

# --- DATABASE HELPERS ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- ENDPOINTS ---

@app.get("/products", response_model=List[Product])
def get_products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return [dict(p) for p in products]

@app.post("/products")
def add_product(product: Product):
    conn = get_db_connection()
    conn.execute("INSERT INTO products (name, price, description) VALUES (?, ?, ?)", 
                 (product.name, product.price, product.description))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/products/{name}")
def delete_product(name: str):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.get("/logs")
def get_logs():
    if not os.path.exists(LOG_FILE):
        return {"logs": []}
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return {"logs": [l.strip() for l in lines[-100:]]} # Last 100 lines

@app.get("/prompt")
def get_prompt():
    try:
        with open("data/system_prompt.txt", "r", encoding="utf-8") as f:
            return {"content": f.read()}
    except:
        return {"content": ""}

@app.post("/prompt")
def update_prompt(prompt: PromptUpdate):
    with open("data/system_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt.content)
    return {"status": "updated"}

@app.get("/")
def read_root():
    return {"message": "Bedel AI Dashboard API is running"}
