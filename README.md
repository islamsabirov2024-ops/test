# MultiBot Builder v5 fix4

Bu paket bitta katta **glavni bot** orqali mijozlarga bot yaratib berish uchun tayyorlangan.

## Ichidagi bot turlari

- 🎬 Kino bot — admin kino kodi qo‘shadi, user kod yuborsa kanal postini copy qiladi.
- 🧹 Reklama tozalovchi bot — guruhda link, @kanal, forward va spam matnlarni o‘chiradi. Bot guruhda admin va `Delete messages` huquqi bo‘lishi kerak.
- 🎵 Qo‘shiq topuvchi bot — TikTok/Instagram Reels ssilka yuborilsa `yt-dlp` orqali video metadata/title/music ma’lumotini olib, YouTube/Google qidiruv tugmalarini beradi. API kerak emas.
- 💻 IT darslik bot — 0 dan professional darajagacha dars bo‘limlari: Python, Telegram bot, Web, Database, Deploy, SaaS. Rasmli yo‘riqnoma bo‘limi bor.
- 👥 Invite bot — guruhga yangi kirganlarni sanaydi va salom beradi.

## Windowsda ishga tushirish

Terminalni `multibot_full` papkasida oching:

```bash
pip install -r requirements.txt
python -m app.main
```

## ENV

`.env` fayl yarating:

```env
BOT_TOKEN=MAIN_BUILDER_BOT_TOKEN
SUPER_ADMIN_ID=5907118746
DB_PATH=data/app.db
```

Env ishlatmasangiz `app/config.py` ichida `BOT_TOKEN` ni qo‘lda yozishingiz mumkin.

## Render

Worker Service tanlang.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python -m app.main
```

## Muhim

Multi-bot polling kichik miqdordagi botlar uchun ishlaydi. Ko‘p mijozli production uchun webhook/VPS yechim tavsiya qilinadi.
