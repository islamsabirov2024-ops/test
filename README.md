# Super MultiBot PRO FIXED

## Ishga tushirish
1. `.env.example` ni `.env` qilib ko‘chiring.
2. `BOT_TOKEN` va `SUPER_ADMIN_ID` yozing.
3. `pip install -r requirements.txt`
4. `python -m app.main`

## Muhim tuzatishlar
- Python 3.11 event loop xatosi tuzatildi.
- Menyular rasmdagidek 2 ustun va keng tugmalar bilan qayta yozildi.
- Kino Bot child bot sifatida alohida ishga tushadi.
- Kino serverga yuklanmaydi: `file_id` yoki Telegram post `message_id` orqali saqlanadi.
- Majburiy obuna kanal qo‘shilganda avtomatik yoqiladi.
- To‘lov cheki admin tasdiqlasa bot active bo‘ladi.

## Kino qo‘shish
Admin panel → Kontent boshqaruvi → Kinolar → Kino yuklash
1. Kod yuboring.
2. Video yuboring yoki `https://t.me/kanal/123` link yuboring.

Agar link orqali ishlatsangiz, child bot kino kanalida admin bo‘lishi kerak.
