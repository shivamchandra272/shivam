import mysql.connector
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

# ==========================================
# ⚙️ BACKEND PYTHON ROUTING RUNTIME
# ==========================================

def get_db_connection():
    # Make sure these credentials match your XAMPP MySQL setup
    return mysql.connector.connect(
        host="localhost", 
        user="root", 
        password="", 
        database="my_website_db"
    )

class MyWebServer(BaseHTTPRequestHandler):
    
    def do_GET(self):
        # In an SPA ecosystem, both root route and dashboard paths receive the exact same layout file
        if self.path == "/" or self.path.startswith("/dashboard"):
            try:
                # 1. Open and read your external HTML template file
                with open('index.html', 'r', encoding='utf-8') as file:
                    html_content = file.read()
                
                # 2. Send the successful response
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                
                # 3. Serve the HTML content to the browser
                self.wfile.write(bytes(html_content, "utf-8"))
                
            except FileNotFoundError:
                # Fallback if you forgot to create the index.html file
                self.send_error(500, "Internal Server Error: 'index.html' template file not found in the directory.")
                
        else:
            self.send_error(404, "Page Not Found")

    def do_POST(self):
        # Handle the Login Form submission
        if self.path == "/login-submit":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = parse_qs(post_data)
            
            username_typed = parsed_data['username'][0]
            password_typed = parsed_data['password'][0]

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username_typed,))
            user_found = cursor.fetchone()
            cursor.close()
            conn.close()

            # Verify credentials
            if user_found and user_found['password'] == password_typed:
                self.send_response(302)  
                self.send_header('Location', '/dashboard')
                self.end_headers()
            else:
                self.show_error_page("Invalid credentials! Access denied.")

        # Handle the Registration Form submission
        elif self.path == "/register-submit":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = parse_qs(post_data)
            
            username_typed = parsed_data['username'][0]
            email_typed = parsed_data['email'][0]
            password_typed = parsed_data['password'][0]

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
                cursor.execute(query, (username_typed, email_typed, password_typed))
                conn.commit()
                cursor.close()
                conn.close()

                # Redirect to dashboard with a success flag
                self.send_response(302)
                self.send_header('Location', '/dashboard?new=true')
                self.end_headers()

            except mysql.connector.Error:
                self.show_error_page("That username is already taken!")

    def show_error_page(self, message):
        # Simple inline HTML for error messages
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        error_html = f"""
        <body style='font-family:Arial; text-align:center; padding:50px; background-color:#f5f7fb;'>
            <div style='background:white; padding:40px; border-radius:12px; display:inline-block; box-shadow:0px 4px 15px rgba(0,0,0,0.1);'>
                <h2 style='color:#ef4444;'>❌ Access Error</h2>
                <p style='font-size:18px;'>{message}</p>
                <br>
                <a href='/' style='padding:10px 20px; background-color:#0f172a; color:white; text-decoration:none; border-radius:6px;'>Go Back</a>
            </div>
        </body>
        """
        self.wfile.write(bytes(error_html, "utf-8"))

def run():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, MyWebServer)
    print("🚀 SPA Gateway running smoothly on http://127.0.0.1:8000 ...")
    print("Press Ctrl+C to stop the server.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()

if __name__ == "__main__":
    run()
