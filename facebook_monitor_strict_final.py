import os
import json
import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def load_list(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

def save_list(filename, items):
    with open(filename, "w", encoding="utf-8") as f:
        for item in items:
            f.write(item + "\n")

def load_config(path="config.txt"):
    config = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                config[key.strip()] = value.strip()
    return config

config = load_config()
TOKEN = config.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = config.get("TELEGRAM_CHAT_ID")

def send_to_telegram(text, author, link):
    message = f"👤 {author}\n{text}\n\n🔗 {link}"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=payload)
        if r.status_code != 200:
            print("❌ שגיאה בשליחה:", r.text)
    except Exception as e:
        print("❌ שגיאה בשליחה:", e)

def setup_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(service=Service(), options=options)

def login(driver, cookie_path):
    driver.get("https://www.facebook.com/home.php")
    time.sleep(5)
    try:
        with open(cookie_path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        for c in cookies:
            if "sameSite" in c:
                del c["sameSite"]
            driver.add_cookie(c)
        driver.get("https://www.facebook.com/home.php")
        time.sleep(5)
    except Exception as e:
        print("❌ שגיאת התחברות:", e)

def main():
    whitelist = load_list("filter_keywords.txt")
    blacklist = load_list("negative_keywords_cleaned.txt")
    sent = load_list("matching_posts.txt")
    groups = load_list("group_urls.txt")

    driver = setup_driver()
    login(driver, "fb_cookies.json")

    for url in groups:
        print("📂 קבוצה:", url)
        try:
            driver.get(url)
            time.sleep(5)
            posts = driver.find_elements(By.XPATH, '//div[@role="article"]')
            for post in posts:
                try:
                    try:
                        content = post.find_element(By.XPATH, ".//div[@data-ad-preview='message']").text.strip()
                    except:
                        continue

                    if len(content) < 100:
                        print("❌ פוסל: תוכן קצר מדי")
                        continue

                    if any(bad.strip('"') in content for bad in blacklist):
                        print("❌ פוסל: מילת פסילה מזוהה")
                        continue

                    matches = [w for w in whitelist if w in content]
                    if len(matches) < 3:
                        print(f"❌ פוסל: רק {len(matches)} מילות סינון ({matches})")
                        continue

                    if content[:50] in sent:
                        print("⚠️ דילוג: כבר נשלח בעבר")
                        continue

                    try:
                        author = post.find_element(By.XPATH, ".//strong/span").text.strip()
                    except:
                        print("❌ פוסל: אין שם מפרסם")
                        continue

                    post_id, group_id = None, None
                    try:
                        data = post.get_attribute("data-ft")
                        if data:
                            m = re.search(r'"top_level_post_id":"(\d+)"', data)
                            if m:
                                post_id = m.group(1)
                        g = re.search(r"facebook.com/groups/(\d+)", url)
                        if g:
                            group_id = g.group(1)
                    except:
                        pass

                    if not group_id:
                        print("❌ פוסל: אין group_id")
                        continue

                    link = f"https://www.facebook.com/groups/{group_id}/permalink/{post_id}" if post_id else url
                    print("✅ שולח פוסט:", author)
                    send_to_telegram(content, author, link)
                    sent.append(content[:50])
                except Exception as e:
                    print("⚠️ חריגה בפוסט:", e)
        except Exception as e:
            print("⚠️ לא נטענה קבוצה:", e)

    save_list("matching_posts.txt", sent)
    driver.quit()

if __name__ == "__main__":
    main()