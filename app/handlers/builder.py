from __future__ import annotations

import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from app.config import SUPER_ADMIN_ID
from app.states import CreateBot
from app.services.validator import validate_bot_token
from app.keyboards.common import *
from app.db import *

router = Router()
manager = None


def set_manager(m):
    global manager
    manager = m


def is_admin(uid: int):
    return uid == SUPER_ADMIN_ID


# ================= START =================
@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await add_user(m.from_user.id, m.from_user.full_name, m.from_user.username or "")
    await m.answer("🤖 Glavni SaaS Bot", reply_markup=main_menu(is_admin(m.from_user.id)))


# ================= BOTLAR =================
@router.message(F.text == "🤖 Botlarim")
async def bots(m: Message):
    bs = await list_user_bots(m.from_user.id)
    if not bs:
        await m.answer("📭 Bot yo‘q")
        return

    for b in bs:
        await m.answer(
            f"🤖 {b['bot_name']}\n🆔 {b['bot_username']}",
            reply_markup=manage_bot(b["id"], b["status"] == "active")
        )


# ================= TOKEN UPDATE =================
@router.callback_query(F.data.startswith("token:"))
async def token_start(c: CallbackQuery, state: FSMContext):
    bid = int(c.data.split(":")[1])
    await state.set_state(CreateBot.token)
    await state.update_data(update_bot_id=bid)
    await c.message.answer("🔑 Yangi token yuboring:")
    await c.answer()


@router.message(CreateBot.token)
async def token_process(m: Message, state: FSMContext):
    data = await state.get_data()

    if "update_bot_id" in data:
        bid = data["update_bot_id"]

        token = m.text.strip()
        ok, info = await validate_bot_token(token)

        if not ok:
            await m.answer("❌ Token noto‘g‘ri")
            return

        await update_bot_token(
            bid,
            m.from_user.id,
            token,
            info.get("username", ""),
            info.get("first_name", ""),
        )

        if manager:
            await manager.stop_child(bid)
            b = await get_bot(bid)
            await manager.start_child(dict(b))

        await state.clear()
        await m.answer("✅ Token yangilandi")
        return


# ================= BOTNI YOQISH =================
@router.callback_query(F.data.startswith("run:"))
async def run(c: CallbackQuery):
    bid = int(c.data.split(":")[1])
    b = await get_bot(bid)

    ok, msg = await manager.start_child(dict(b))
    await c.message.answer(msg)
    await c.answer()


# ================= BOTNI O‘CHIRISH =================
@router.callback_query(F.data.startswith("stop:"))
async def stop(c: CallbackQuery):
    bid = int(c.data.split(":")[1])

    await manager.stop_child(bid)
    await set_bot_status(bid, "stopped")

    await c.message.answer("⏸ Bot o‘chirildi")
    await c.answer()


# ================= AUTO EXPIRE =================
async def expire_loop(bot, manager):
    while True:
        try:
            expired = await expire_due_bots()

            for b in expired:
                bid = int(b["id"])

                if manager:
                    await manager.stop_child(bid)

                await set_bot_status(bid, "expired")

                try:
                    await bot.send_message(
                        b["owner_user_id"],
                        "⛔️ Bot muddati tugadi!"
                    )
                except:
                    pass

        except Exception as e:
            print("EXPIRE ERROR:", e)

        await asyncio.sleep(60)
