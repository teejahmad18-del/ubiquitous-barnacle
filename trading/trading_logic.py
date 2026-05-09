from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.error

# Email configuration
SENDER_EMAIL = "dahmadu071@gmail.com"
RECIPIENT_EMAILS = ["teejeedeeone@gmail.com"]
EMAIL_PASSWORD = "oase wivf hvqn lyhr"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def send_email_notification(new_numbers):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(RECIPIENT_EMAILS)
        msg['Subject'] = f"New Temporary Numbers Available ({len(new_numbers)} found)"

        body = "New temporary phone numbers were just posted:\n\n"
        for number in new_numbers:
            body += f"📱 Phone: {number['phone_number']}\n"
            body += f"⏰ Posted: {number['time_posted']}\n"
            body += f"🔗 Link: https://temp-number.com/temporary-numbers/United-States/{number['phone_number']}/1\n"
            body += "-"*50 + "\n"

        body += "\nThis notification was sent because these numbers were posted within the last 5 minutes."
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAILS, msg.as_string())

        print(f"Email notification sent for {len(new_numbers)} new number(s)")
        return True

    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def get_phone_numbers(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }

        req = Request(url, headers=headers)
        response = urlopen(req, timeout=10)
        html_content = response.read().decode('utf-8')

        soup = BeautifulSoup(html_content, 'html.parser')
        phone_entries = []
        country_boxes = soup.find_all('div', class_='country-box')

        for box in country_boxes:
            try:
                phone_number = box.find('h4', class_='card-title').text.strip()
                time_text = box.find('div', class_='add_time-top').text.strip()

                phone_entries.append({
                    'phone_number': phone_number,
                    'time_posted': time_text
                })
            except AttributeError:
                continue

        return phone_entries

    except urllib.error.URLError as e:
        print(f"Error fetching the URL: {e.reason}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def check_for_new_numbers():
    url = 'https://temp-number.com/countries/United-States'
    print(f"Checking for new numbers at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    phone_numbers = get_phone_numbers(url)
    new_numbers = []

    for number in phone_numbers:
        time_text = number['time_posted'].lower()
        if 'minute' in time_text:
            minutes_ago = int(time_text.split()[0])
            if minutes_ago <= 5:
                new_numbers.append(number)
        elif 'second' in time_text:  # In case any are posted seconds ago
            new_numbers.append(number)

    if new_numbers:
        print(f"Found {len(new_numbers)} new number(s) posted within last 5 minutes")
        return send_email_notification(new_numbers)
    else:
        print("No new numbers found in the last 5 minutes")
        return False

if __name__ == "__main__":
    check_for_new_numbers()
