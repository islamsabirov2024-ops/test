from app.keyboards.common import reply, inline


def admin_menu():
    return reply([
        ["🧹 Moderator panel"],
        ["👥 Odam qo‘shish limiti"],
        ["⏱ Blok vaqti"],
        ["📊 Statistika"],
    ])


def limit_menu():
    return inline([[(f"{n} odam", f"mod:limit:{n}")] for n in [5,10,15,20,25,30]] + [[("🔙 Orqaga", "mod:home")]])


def mute_menu():
    return inline([[("30 sekund", "mod:mute:30")],[("1 minut", "mod:mute:60")],[("5 minut", "mod:mute:300")],[("🔙 Orqaga", "mod:home")]])
