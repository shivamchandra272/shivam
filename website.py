import mysql.connector
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "nova_website_db"
}

# --- DATABASE SETUP ---
def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

def init_db():
    # 1. Connect without database to ensure it exists in XAMPP MySQL
    server_conn = mysql.connector.connect(
        host=MYSQL_CONFIG["host"],
        user=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"]
    )
    server_cursor = server_conn.cursor()
    server_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_CONFIG['database']}`")
    server_cursor.close()
    server_conn.close()

    # 2. Connect to the database and create users table
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(150) NOT NULL,
            password VARCHAR(255) NOT NULL DEFAULT '123456',
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Seed default admin and user if not exists
    cursor.execute("SELECT id FROM users WHERE username = %s", ("admin",))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
        """, ("admin", "admin@novasocial.in", "admin123", "admin"))
        cursor.execute("""
            INSERT INTO users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
        """, ("johndoe", "john@example.com", "user123", "user"))

    conn.commit()
    cursor.close()
    conn.close()

# --- WEB SERVER HANDLER ---
class WebsiteHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(data), "utf-8"))

    def send_html(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(bytes(content, "utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html" or path == "/admin":
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_html(content)
            except FileNotFoundError:
                self.send_error(404, "index.html not found")

        elif path == "/api/users":
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, username, email, role, DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') as created_at FROM users ORDER BY id DESC")
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            self.send_json({"users": users})

        else:
            self.send_error(404, "Page Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')

        try:
            payload = json.loads(post_data) if self.headers.get('Content-Type') == 'application/json' else parse_qs(post_data)
            if isinstance(payload, dict):
                for k, v in payload.items():
                    if isinstance(v, list) and len(v) == 1:
                        payload[k] = v[0]
        except Exception:
            payload = {}

        if path == "/api/login":
            username = payload.get("username", "").strip()
            password = payload.get("password", "").strip()

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, username, email, role FROM users WHERE (username = %s OR email = %s) AND password = %s", 
                           (username, username, password))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                self.send_json({"success": True, "user": user})
            else:
                self.send_json({"success": False, "message": "Invalid username/email or password."}, status=401)

        elif path == "/api/register":
            username = payload.get("username", "").strip()
            email = payload.get("email", "").strip()
            password = payload.get("password", "").strip()
            role = "user"  # All newly registered users default to 'user' role

            if not username or not email or not password:
                self.send_json({"success": False, "message": "All fields are required."}, status=400)
                return

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                               (username, email, password, role))
                conn.commit()
                new_id = cursor.lastrowid
                cursor.close()
                conn.close()
                self.send_json({"success": True, "user": {"id": new_id, "username": username, "email": email, "role": role}})
            except mysql.connector.IntegrityError:
                self.send_json({"success": False, "message": "Username already exists."}, status=400)
            except Exception as e:
                self.send_json({"success": False, "message": str(e)}, status=500)

        elif path == "/api/delete-user":
            user_id = payload.get("id")
            if not user_id:
                self.send_json({"success": False, "message": "Missing user ID."}, status=400)
                return

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            cursor.close()
            conn.close()
            self.send_json({"success": True})

        elif path == "/api/toggle-role":
            user_id = payload.get("id")
            new_role = payload.get("role")
            if not user_id or not new_role:
                self.send_json({"success": False, "message": "Missing arguments."}, status=400)
                return

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
            conn.commit()
            cursor.close()
            conn.close()
            self.send_json({"success": True})

        else:
            self.send_error(404, "API endpoint not found")

def run():
    init_db()
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, WebsiteHandler)
    print("Server running on http://127.0.0.1:8000 (XAMPP MySQL backed)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()

if __name__ == "__main__":
    run()
