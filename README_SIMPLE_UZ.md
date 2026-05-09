# READY SIMPLE MULTIBOT FINAL

Bu bot 2 qismdan iborat:

1. ASOSIY BOT
- Bot yaratish
- Botlarim
- Hisob to'ldirish
- Admin chek tasdiqlash
- Platforma tariflari
- Referal
- Smart limit

2. KINO BOT
- Kino qo'shish
- Kod orqali kino berish
- Premium kino
- Majburiy obuna
- Reklama
- To'lov tizimlari
- Admin panel

## Railway uchun kerakli Variables

BOT_TOKEN=asosiy_bot_tokeni
SUPER_ADMIN_ID=5907118746
DATABASE_URL=postgresql://...

## Start Command

python -m app.main

## Qanday ishlaydi

1. User asosiy botda Hisob to'ldirish bosadi.
2. Summa yozadi.
3. Chek yuboradi.
4. Chek adminga keladi.
5. Admin ✅ Tasdiqlash bosadi.
6. Balans userga qo'shiladi.
7. User Bot yaratish bosadi, tarif tanlaydi, token yuboradi.
8. Kino bot avtomatik yaratiladi.
9. Kino botga kirib /panel bosadi va sozlaydi.


## MUHIM
Railway’da PostgreSQL ishlating. DB_PATH ni o‘chiring. DATABASE_URL to‘liq postgresql://... bo‘lsin.
Chek tasdiqlansa admin xabari TASDIQLANDI bo‘lib o‘zgaradi.


## FULL PRO qo‘shimchalar
- Smart Limit: limit oshsa bot darrov o‘chmaydi, 24 soat sekin rejimda ishlaydi.
- DB tozalash: eski chek/reklama/runtime yozuvlarini tozalaydi, balans va kinolarni o‘chirmaydi.
- Premium to‘lov: faqat avtomat emas, admin tasdiq va avtomat ikkalasi ham alohida ON/OFF.
- Reklama queue: xabarlar navbat bilan yuboriladi.



## FINAL FULL PRO qo‘shimchalar
- Kino botda PRO xabar yuborish: matn/rasm/video/document, preview, tugma, progress, pauza/davom ettirish/o‘chirish.
- Foydalanuvchilar paneli real ishlaydi: ro‘yxat, qidirish, premium/aktivlik.
- IT Dars Bot qo‘shildi: kompyuter savodxonligi, HTML/CSS, Python, Telegram bot, Database va test darslari.
- Main bot token qabul qilish jarayoni va child bot manager saqlangan.
