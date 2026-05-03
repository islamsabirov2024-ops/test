from aiohttp import web

async def payme_webhook(request):
    data = await request.json()
    # TODO: Payme merchant secret tekshiriladi.
    # TODO: order/payment id bo‘yicha db.update_payment(..., 'approved') va premium beriladi.
    return web.json_response({"result": {"status": "ok"}})

async def click_webhook(request):
    data = await request.post()
    # TODO: Click secret key tekshiriladi.
    # TODO: order/payment id bo‘yicha db.update_payment(..., 'approved') va premium beriladi.
    return web.json_response({"error": 0, "error_note": "Success"})
