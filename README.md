# MultiBot SaaS v10 Full

Start command:
```bash
python -m app.main
```

Build command:
```bash
pip install -r requirements.txt
```

Muhim ENV:
- `BOT_TOKEN` — glavni SaaS bot tokeni
- `SUPER_ADMIN_ID` — sizning Telegram ID
- `DATABASE_URL` — FULL kino botlar uchun PostgreSQL URL
- `PAYMENT_CARD`, `PAYMENT_PAYME_LINK`, `PAYMENT_VISA_INFO` — to'lov ma'lumotlari

## Nima o'zgardi
- Kino bot: yuborilgan tayyor `kino_bot_majburiy_premium_menyu_100_fix` kodi template sifatida qo'shildi.
- Har bir kino bot alohida child process sifatida yuradi.
- Har kino bot uchun PostgreSQL schema alohida: `kino_bot_<bot_id>`.
- Kino bot egasi avtomatik o'z botida admin bo'ladi.
- Kino baza kanali bot ichidan admin panel orqali ulanadi: forward/link/file usullari ishlaydi.
- IT darslik botda bepul/pullik darslar modeli bor.
- Yuklovchi bot qo'shildi.

## Qorovul bot
Botni guruhga admin qiling va BotFather’da `/setprivacy` -> Disable qiling.
