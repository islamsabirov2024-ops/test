from aiohttp import web
from app.config import HOST, PORT

async def handle(request):
    return web.Response(text='OK')

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_head('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
