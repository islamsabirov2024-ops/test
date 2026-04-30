# Super MultiBot FULL

Bu loyiha bitta glavni bot ichida foydalanuvchilarga o'z botini yaratish imkonini beradi.

## Ichida bor

- 👑 Super Admin panel faqat `SUPER_ADMIN_ID` uchun
- 🤖 Oddiy user paneli
- 🎬 Kino bot shabloni
- 🧹 Reklama tozalovchi bot shabloni
- 💳 Har bir bot egasi o'z kartasini qo'shadi
- 💰 Har bir bot egasi oylik narxini belgilaydi
- 📸 To'lov cheki Super Admin'ga keladi
- ✅ Super Admin tasdiqlasa bot ishga tushadi
- ▶️/⏸ Botni yoqish/o'chirish faqat Super Admin'da
- 👥 Cleaner botda 5/10/15/20/25/30 odam qo'shish limiti sozlanadi
- 🚫 Reklama link tashlagan user 30 sekund bloklanadi

## .env

```env
BOT_TOKEN=GLAVNI_BOT_TOKEN
SUPER_ADMIN_ID=5907118746
DATABASE_PATH=data.db
PLATFORM_NAME=Super MultiBot
DEFAULT_CARD=8600 0000 0000 0000
DEFAULT_PRICE=30000
```

## Ishga tushirish

```bash
pip install -r requirements.txt
python -m app.main
```

## Railway / Render start command

```bash
python -m app.main
```

## Qanday ishlaydi

1. User `/start` bosadi.
2. `🤖 Bot yaratish` tanlaydi.
3. `🎬 Kino bot` yoki `🧹 Reklama tozalovchi bot` tanlaydi.
4. BotFather tokenini yuboradi.
5. Bot `pending_payment` holatda saqlanadi.
6. User `Mening botlarim` → karta/narx sozlaydi → chek yuboradi.
7. Super Admin chekni tasdiqlaydi.
8. Bot `active` bo'ladi va ishga tushadi.

## Muhim

Telegramda har bir child bot alohida token bilan ishlaydi. Bitta serverda ko'p bot ishlatish mumkin, lekin juda ko'p bot bo'lsa server kuchliroq bo'lishi kerak.

## Kino bot

Owner o'z child kino botiga kiradi:

- `/admin` — admin panel
- `/add` — kino qo'shish
- User kod yuborsa, bot video chiqaradi.

## Cleaner bot

Cleaner botni guruhga qo'shib admin qilish kerak. U link/reklama tashlangan xabarni o'chiradi va userni 30 sekund yozishdan cheklaydi.
