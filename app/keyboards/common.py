from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def reply(rows, resize=True, one_time=False, selective=False):
    """
    Reply keyboard — pastdagi katta knopkalar.
    Har bir row = bitta qator.
    """
    keyboard = []

    for row in rows:
        keyboard.append([KeyboardButton(str(text)) for text in row])

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=resize,
        one_time_keyboard=one_time,
        selective=selective,
        input_field_placeholder="👇 Menyudan tanlang"
    )


def inline(rows):
    """
    Inline keyboard — xabar ichidagi knopkalar.
    Format:
    [
        [("Text", "callback:data")],
        [("Text", "callback:data"), ("Text2", "callback:data2")]
    ]
    """
    keyboard = []

    for row in rows:
        buttons = []
        for item in row:
            if len(item) == 2:
                text, data = item
                buttons.append(InlineKeyboardButton(str(text), callback_data=str(data)))
            elif len(item) == 3:
                text, key, value = item
                if key == "url":
                    buttons.append(InlineKeyboardButton(str(text), url=str(value)))
        keyboard.append(buttons)

    return InlineKeyboardMarkup(keyboard)


def back(data="home"):
    return inline([
        [("🔙 Orqaga", data)]
    ])


def cancel(data="home"):
    return inline([
        [("❌ Bekor qilish", data)]
    ])


def yes_no(yes_data, no_data="home"):
    return inline([
        [("✅ Ha", yes_data), ("❌ Yo‘q", no_data)]
    ])


def page_nav(prev_data=None, next_data=None, back_data="home"):
    rows = []

    nav = []
    if prev_data:
        nav.append(("⬅️ Oldingi", prev_data))
    if next_data:
        nav.append(("Keyingi ➡️", next_data))

    if nav:
        rows.append(nav)

    rows.append([("🔙 Orqaga", back_data)])
    return inline(rows)


def open_url(text, url, back_data="home"):
    return inline([
        [(text, "url", url)],
        [("🔙 Orqaga", back_data)]
    ])
