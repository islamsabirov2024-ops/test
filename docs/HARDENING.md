# HARDENING UPDATE

Bu versiyada production uchun yashirin muammolar kamaytirildi:

- Atomic balance: balans yechish `BEGIN IMMEDIATE` + `WHERE balance>=amount` bilan xavfsizlandi.
- Referral balance: referral balans ham atomic yechiladi, haqiqiy pul bilan aralashmaydi.
- Tarif muddati: platforma tarifi muddati tugasa child bot avtomatik bloklanadi.
- Kunlik limit: kunlik unique user limiti tekshiriladi, limit to‘lsa bot paused bo‘ladi.
- Owner notify: limit/muddat sababli to‘xtaganda ownerga kuniga bir marta ogohlantirish yuboriladi.
- Conflict kamaytirish: pollingdan oldin webhook tozalanadi.
- Runtime events: conflict, crash, ad send fail kabi muhim xatolar DBga yoziladi.
- Reklama interval: kino reklama har safar emas, default har 3 ta kino ko‘rishda yuboriladi.
- /cancel: asosiy bot va child botda state qotib qolsa bekor qilish komandasi qo‘shildi.
- Indexes: users, bots, movies, views, payments, premium, ads uchun indekslar qo‘shildi.
- Cache cleanup: pycache/pyc fayllari olib tashlandi.

Muhim: bir token faqat bitta deploy/instance ichida ishlashi kerak. Aks holda Telegram getUpdates conflict beradi.
