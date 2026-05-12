from fastmcp import FastMCP
import os
import sqlite3
import tempfile


TEMP_DIR = tempfile.gettempdir()
DB_PATH  = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__),"categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")

def init_db():
    try:
        with sqlite3.connect(DB_PATH)  as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""
                  CREATE TABLE IF NOT EXISTS expenses(
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      date TEXT NOT NULL,
                      amount REAL NOT NULL,
                      category TEXT NOT NULL,
                      subcategory TEXT DEFAULT '',
                      note TEXT DEFAULT ''
                  )
                  """)
            
            # c.execute("INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01',0,'test)")
            c.execute(
                    "INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01',0,'test')"
                    )
            c.execute("DELETE FROM expenses WHERE category ='test'")
            print("Database initialized successfully with write access")
    except Exception as e:
        print(f"Database initialization error: {e}")
init_db()
    
@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    '''Add a new expenses entry to the database.'''
    
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
            )
            expense_id = cur.lastrowid
        c.commit()

        return {"status": "success", "id":expense_id, "messages":"Expense added successfully"}
    except sqlite3.OperationalError as e:
        if "readonly"in str(e).lower():
            return {"status":"error", "message": "Database is in read-only mode. Check file permissions."}
        return {"status":"error", "message":f"Database error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error "}
        

@mcp.tool()
def list_expenses(start_date, end_date):
    '''List expenses entries within a inclusive date range.'''
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
        """
        SELECT id, date, amount, category, subcategory, note
        FROM expenses
        WHERE date BETWEEN ? AND ?
        ORDER BY id ASC 
        """,
        (start_date, end_date)
        )
        
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        return {"status":"error", "message": f"Error listing expenses: {str(e)}"}
    
    
@mcp.tool()
def summarize(start_date, end_date, category=None):
    '''Summarize expenses by category within an inclusive date range.'''
    try:
        with sqlite3.connect(DB_PATH) as c:

            query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """

        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY total_amount DESC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        return {"status":"error","message": f"Error summarizing expenses: {str(e)}"}
    
    
@mcp.resource("expenses://categories", mime_type="application/json")
def categories():
    try:
        default_categories ={
            "categories":[
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Other"
            ]
        }
        try:
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            import json
            return json.dumps(default_categories,indent=2)
    except Exception as e:
        return f'{{"error":"Could not load categories:{str(e)}"}}'
    
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001)