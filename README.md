# Aiogram MultiBot + Kino Bot PRO FINAL

Bu paket professional struktura bilan tayyorlangan:

- Asosiy MultiBot: bot yaratish, botlarim, kabinet, referal, hisob to‘ldirish.
- Kino Bot template: kino kod, premium, tarif, chek tasdiqlash, majburiy obuna, reklama, sevimlilar, TOP, yangi kinolar, so‘rovlar.
- Referal balans alohida: referral pul faqat premium tarifga ishlaydi, haqiqiy pul bilan qo‘shilmaydi.
- Bitta kodga birinchi kino 1-qism bo‘ladi, shu kodga yana qo‘shilsa qism qo‘shish/almashtirish/bekor qilish chiqadi.
- Botlarim ichida yoqish/to‘xtatish, token almashtirish, o‘chirish flow bor.

## Ishga tushirish

```bash
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

## Majburiy sozlamalar

```env
BOT_TOKEN=BotFather token
SUPER_ADMIN_ID=5907118746
DATABASE_PATH=bot.db
```

## Deploy

Railway/Render start command:

```bash
python -m app.main
```

To‘liq test rejasi: `docs/TEST_PLAN.md`.
