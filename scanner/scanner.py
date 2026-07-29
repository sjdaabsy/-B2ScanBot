"""
================================================================
 اسکنر کانال‌ها - اجرا می‌شه توسط GitHub Actions (هر چند دقیقه)
================================================================
این اسکریپت:
  1. تنظیمات (لیست کانال‌ها، کلمات فیلتر) رو از Cloudflare Worker می‌گیره
  2. با اکانت تلگرام خودت (MTProto) هر کانال عمومی رو بدون نیاز به
     عضویت چک می‌کنه (دقیقاً مثل پیش‌نمایش کانال قبل از Join)
  3. اگه کپشن/متن پست شامل یکی از کلمات فیلتر بود، پست رو به
     کانال شخصی مقصد فوروارد می‌کنه
  4. آخرین آیدی پیام هر کانال رو دوباره توی Worker ذخیره می‌کنه
     تا دفعه‌ی بعد از همون‌جا ادامه بده (پست تکراری نیاد)

ENV های لازم (به‌صورت GitHub Secrets تنظیم می‌شن):
  API_ID          -> از my.telegram.org
  API_HASH        -> از my.telegram.org
  SESSION_STRING  -> با اسکریپت generate_session.py ساخته می‌شه
  DEST_CHANNEL    -> یوزرنیم یا آیدی کانال شخصی مقصد (مثلاً @mychannel)
  WORKER_URL      -> آدرس Worker (مثلاً https://xxx.workers.dev)
  API_SECRET      -> همون رمزی که توی Worker تنظیم کردی
================================================================
"""

import os
import requests
from telethon.sync import TelegramClient
from telethon.errors import ChatForwardsRestrictedError, FloodWaitError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
DEST_CHANNEL = os.environ["DEST_CHANNEL"]
WORKER_URL = os.environ["WORKER_URL"].rstrip("/")
API_SECRET = os.environ["API_SECRET"]

HEADERS = {"X-API-Key": API_SECRET}


def get_config():
    r = requests.get(f"{WORKER_URL}/api/config", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def get_last_id(channel):
    r = requests.get(f"{WORKER_URL}/api/state", headers=HEADERS,
                      params={"channel": channel}, timeout=30)
    r.raise_for_status()
    return r.json().get("last_id", 0)


def set_last_id(channel, last_id):
    requests.post(f"{WORKER_URL}/api/state", headers=HEADERS,
                   json={"channel": channel, "last_id": last_id}, timeout=30)


def message_matches(msg, keywords):
    if not keywords:
        return False
    text = (msg.message or "") + " " + (getattr(msg, "raw_text", "") or "")
    text = text.lower()
    return any(kw.strip().lower() in text for kw in keywords if kw.strip())


def main():
    config = get_config()
    channels = config.get("channels", {})
    global_keywords = config.get("keywords", [])

    if not channels:
        print("هیچ کانالی برای اسکن ثبت نشده.")
        return

    import time
    now_ms = time.time() * 1000

    with TelegramClient(
        session=SESSION_STRING, api_id=API_ID, api_hash=API_HASH
    ) as client:
        for channel_username, ch_conf in channels.items():
            muted_until = ch_conf.get("muted_until")
            if muted_until and muted_until > now_ms:
                print(f"⏭  {channel_username} میوت است، رد شد.")
                continue

            keywords = ch_conf.get("keywords") or global_keywords
            last_id = get_last_id(channel_username)

            try:
                entity = client.get_entity(channel_username)
            except Exception as e:
                print(f"❌ خطا در دسترسی به {channel_username}: {e}")
                continue

            max_id_seen = last_id
            try:
                messages = list(client.iter_messages(
                    entity, min_id=last_id, limit=100, reverse=True
                ))
            except FloodWaitError as e:
                print(f"⏳ FloodWait روی {channel_username}: {e.seconds} ثانیه صبر لازم است. رد شد.")
                continue
            except Exception as e:
                print(f"❌ خطا در خواندن پیام‌های {channel_username}: {e}")
                continue

            for msg in messages:
                if msg.id > max_id_seen:
                    max_id_seen = msg.id

                if not message_matches(msg, keywords):
                    continue

                try:
                    client.forward_messages(DEST_CHANNEL, msg, entity)
                    print(f"✅ فوروارد شد: {channel_username} -> پیام {msg.id}")
                except ChatForwardsRestrictedError:
                    # کانال فوروارد رو غیرفعال کرده - پس محتوا رو دوباره می‌فرستیم
                    try:
                        caption = msg.message or ""
                        if msg.media:
                            client.send_file(DEST_CHANNEL, msg.media, caption=caption)
                        else:
                            client.send_message(DEST_CHANNEL, caption)
                        print(f"✅ (بازفرستاده‌شده) {channel_username} -> پیام {msg.id}")
                    except Exception as e2:
                        print(f"❌ ارسال دستی هم ناموفق بود: {e2}")
                except FloodWaitError as e:
                    print(f"⏳ FloodWait هنگام فوروارد: {e.seconds} ثانیه")
                except Exception as e:
                    print(f"❌ خطا در فوروارد پیام {msg.id}: {e}")

            if max_id_seen != last_id:
                set_last_id(channel_username, max_id_seen)
                print(f"📌 وضعیت {channel_username} به‌روزرسانی شد (آخرین آیدی: {max_id_seen})")


if __name__ == "__main__":
    main()

