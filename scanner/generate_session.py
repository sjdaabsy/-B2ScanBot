"""
================================================================
 این اسکریپت رو فقط "یک بار" اجرا کن تا Session String بگیری.
 بهترین جا برای اجرا: Google Colab (رایگان، نیازی به نصب چیزی نیست)
 راهنمای کامل توی فایل GUIDE.md هست.
================================================================
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("API_ID رو وارد کن: "))
api_hash = input("API_HASH رو وارد کن: ")

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n" + "=" * 60)
    print("این رشته رو کپی کن و به عنوان SESSION_STRING در")
    print("GitHub Secrets ذخیره کن (به کسی نشونش نده!):")
    print("=" * 60)
    print(client.session.save())
    print("=" * 60)
  
