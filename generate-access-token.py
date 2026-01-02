
from kiteconnect import KiteConnect
import os

# === CONFIG ===
API_KEY = "awh2j04pcd83zfvq"
API_SECRET = "gfjmlgcn28pirja9b1e3xtww8ep7xthb"
ACCESS_TOKEN_FILE = "access_token.txt"

# === Initialize KiteConnect ===
kite = KiteConnect(api_key=API_KEY)

# === Step 1: Show login URL ===
print("🔗 Visit this URL to log in and get your request_token:")
print(kite.login_url())

# === Step 2: Enter request_token manually ===
request_token = input("\n📥 Paste your request_token here: ").strip()

try:
    # === Step 3: Generate access token ===
    session = kite.generate_session(request_token, api_secret=API_SECRET)
    access_token = session["access_token"]
    
    # === Step 4: Save it to file ===
    with open(ACCESS_TOKEN_FILE, "w") as f:
        f.write(access_token)
    
    print(f"\n✅ Access Token generated and saved to '{ACCESS_TOKEN_FILE}' 📝")
except Exception as e:
    print(f"❌ Error generating access token: {e}")

