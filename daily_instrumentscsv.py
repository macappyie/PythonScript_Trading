
import requests

def download_instruments_csv():
    url = "https://api.kite.trade/instruments"
    response = requests.get(url)
    if response.status_code == 200:
        with open("instruments.csv", "wb") as f:
            f.write(response.content)
        print("✅ instruments.csv updated")
    else:
        print("❌ Failed to update instruments.csv")

# 🔁 Run when script is executed
if __name__ == "__main__":
    download_instruments_csv()

