"""
================================================================
 این اسکریپت رو توی Google Colab اجرا کن اگه سایت my.telegram.org
 توی مرورگر گوشیت (حتی با VPN) درست کار نمی‌کنه.
 این کار دقیقاً همون کاری که توی فرم وب انجام می‌دادی رو از طریق
 کد انجام می‌ده، ولی از سرورهای Colab (بدون فیلترینگ) استفاده می‌کنه.
================================================================
مراحل استفاده:
  1. برو colab.research.google.com و یه Notebook جدید بساز
  2. این کد رو کامل توی یه سلول Paste کن و اجرا کن (پلی رو بزن)
  3. شماره تلفنت رو با کد کشور وارد کن (مثال: +989121234567)
  4. یه پیام از "Telegram" (خود اپ سرویس، نه SMS) میاد با یه کد
  5. اون کد رو وارد کن
  6. عنوان و Short name اپ رو وارد کن (بدون فاصله برای Short name)
  7. در آخر api_id و api_hash رو بهت نشون می‌ده - همونا رو ذخیره کن
================================================================
"""

import requests
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

BASE = "https://my.telegram.org"


def get_hidden_value(html, name):
    # کل تگ input شامل این name رو پیدا می‌کنیم (صرف‌نظر از ترتیب attribute ها)
    tag_match = re.search(rf'<input[^>]*name=["\']{name}["\'][^>]*>', html)
    if not tag_match:
        return None
    tag = tag_match.group(0)
    val_match = re.search(r'value=["\']([^"\']*)["\']', tag)
    return val_match.group(1) if val_match else None


def extract_api_creds(html):
    api_id = re.search(r"App api_id:\s*<[^>]*>\s*(\d+)", html)
    api_hash = re.search(r"App api_hash:\s*<[^>]*>\s*([a-f0-9]+)", html)
    return (api_id.group(1) if api_id else None,
            api_hash.group(1) if api_hash else None)


# مرحله ۱: ارسال شماره تلفن و گرفتن کد
phone = input("شماره تلفن با کد کشور (مثل +989121234567): ").strip()

r = session.post(f"{BASE}/auth/send_password", data={"phone": phone})
print("وضعیت درخواست send_password:", r.status_code)

try:
    data = r.json()
except Exception:
    print("❌ پاسخ سرور JSON نبود. متن پاسخ:")
    print(r.text[:2000])
    data = {}

if "random_hash" not in data:
    print("❌ خطا در ارسال کد. پاسخ سرور:", data)
else:
    random_hash = data["random_hash"]
    print("✅ یه کد از طرف Telegram (پیام درون‌برنامه‌ای، نه پیامک) برات اومد.")
    code = input("کدی که دریافت کردی رو وارد کن: ").strip()

    r = session.post(f"{BASE}/auth/login", data={
        "phone": phone,
        "random_hash": random_hash,
        "password": code,
    })
    print("وضعیت درخواست login:", r.status_code)

    if "Invalid code" in r.text or "PHONE_CODE_INVALID" in r.text:
        print("❌ کد اشتباه بود. از اول اسکریپت رو اجرا کن.")
    else:
        r2 = session.get(f"{BASE}/apps")

        if "Create new application" not in r2.text:
            api_id, api_hash = extract_api_creds(r2.text)
            print("\n✅ ظاهراً از قبل یه اپلیکیشن ساخته شده:")
            print("api_id:", api_id or "پیدا نشد - HTML زیر رو بررسی کن")
            print("api_hash:", api_hash or "پیدا نشد - HTML زیر رو بررسی کن")
            if not api_id or not api_hash:
                print("\n--- HTML برای بررسی دستی ---")
                print(r2.text[:3000])
        else:
            app_hash = get_hidden_value(r2.text, "hash")
            title = input("App title (دلخواه، مثلاً B2ScanBot): ").strip()
            shortname = input("Short name (بدون فاصله، فقط حروف/عدد انگلیسی، ۵ تا ۳۲ کاراکتر): ").strip()

            r3 = session.post(f"{BASE}/apps/create", data={
                "hash": app_hash,
                "app_title": title,
                "app_shortname": shortname,
                "app_url": "",
                "app_platform": "android",
                "app_desc": "",
            })
            print("وضعیت درخواست apps/create:", r3.status_code)

            api_id, api_hash = extract_api_creds(r3.text)
            if api_id and api_hash:
                print("\n✅ اپ ساخته شد!")
                print("api_id:", api_id)
                print("api_hash:", api_hash)
            else:
                print("❌ نتونستم api_id/api_hash رو استخراج کنم. متن پایین رو برام کپی کن:")
                print(r3.text[:3000])

