from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.modules import ad_cleaner, music_finder, invite_gate, it_lessons, downloader

log = logging.getLogger(__name__)

MODULES = {
    'ad_cleaner': ad_cleaner.setup,
    'music_finder': music_finder.setup,
    'invite_gate': invite_gate.setup,
    'it_lessons': it_lessons.setup,
    'downloader': downloader.setup,
}

ROOT = Path(__file__).resolve().parent
KINO_TEMPLATE = ROOT / 'bot_templates' / 'kino_full'

class BotManager:
    def __init__(self):
        self.tasks: dict[int, asyncio.Task] = {}
        self.bots: dict[int, Bot] = {}
        self.processes: dict[int, asyncio.subprocess.Process] = {}

    async def start_child(self, row: dict):
        bid = int(row['id'])
        if bid in self.tasks and not self.tasks[bid].done():
            return True, 'Bot allaqachon ishlab turibdi.'
        if bid in self.processes and self.processes[bid].returncode is None:
            return True, 'Kino bot allaqachon ishlab turibdi.'
        if row['bot_type_code'] == 'movie':
            return await self._start_kino_full(row)
        setup = MODULES.get(row['bot_type_code'])
        if not setup:
            return False, 'Bot turi topilmadi.'

        async def run():
            bot = Bot(row['bot_token'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            self.bots[bid] = bot
            dp = Dispatcher()
            setup(dp, bid, int(row['owner_user_id']))
            try:
                await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.exception('Child bot failed %s: %s', bid, e)
            finally:
                try:
                    await bot.session.close()
                except Exception:
                    pass
                self.bots.pop(bid, None)
        self.tasks[bid] = asyncio.create_task(run())
        return True, 'Bot ishga tushirildi.'

    async def _start_kino_full(self, row: dict):
        bid = int(row['id'])
        if not (KINO_TEMPLATE / 'bot.py').exists():
            return False, 'Kino template bot.py topilmadi.'
        env = os.environ.copy()
        env['CHILD_BOT_TOKEN'] = str(row['bot_token'])
        env['CHILD_SUPER_ADMIN_ID'] = str(row['owner_user_id'])
        env['CHILD_BOT_NAME'] = str(row.get('bot_name') or 'Kino Bot')
        env['BOT_SCHEMA'] = f'kino_bot_{bid}'
        proc = await asyncio.create_subprocess_exec(
            sys.executable, 'bot.py', cwd=str(KINO_TEMPLATE), env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        self.processes[bid] = proc

        async def watch():
            assert proc.stdout is not None
            try:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    log.info('[kino:%s] %s', bid, line.decode(errors='ignore').rstrip())
                await proc.wait()
                log.warning('Kino child stopped: %s code=%s', bid, proc.returncode)
            except asyncio.CancelledError:
                raise
            finally:
                self.processes.pop(bid, None)
        self.tasks[bid] = asyncio.create_task(watch())
        return True, 'To‘liq kino bot ishga tushirildi.'

    async def stop_child(self, bid: int):
        bid = int(bid)
        proc = self.processes.get(bid)
        if proc and proc.returncode is None:
            try:
                if os.name == 'nt':
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
                await asyncio.wait_for(proc.wait(), timeout=8)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self.processes.pop(bid, None)
        task = self.tasks.get(bid)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self.tasks.pop(bid, None)
        bot = self.bots.pop(bid, None)
        if bot:
            try:
                await bot.session.close()
            except Exception:
                pass

    async def start_many(self, rows):
        for r in rows:
            try:
                await self.start_child(dict(r))
            except Exception as e:
                log.exception('start_many error: %s', e)

    async def stop_all(self):
        for bid in list(self.tasks):
            await self.stop_child(bid)
        for bid in list(self.processes):
            await self.stop_child(bid)
