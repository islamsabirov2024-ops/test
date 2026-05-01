from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def reply(rows, resize=True):
    """Telegram reply keyboard. 2 ta tugma bir qatorda bo'lsa ham keng chiqadi."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton(str(x)) for x in row] for row in rows],
        resize_keyboard=resize,
        one_time_keyboard=False,
        input_field_placeholder="Menyudan tanlang...",
    )


def inline(rows):
    """Rows: [(text, data)] yoki [(text, url, True)] ni qo'llaydi."""
    out = []
    for row in rows:
        line = []
        for item in row:
            if len(item) == 3 and item[2] == "url":
                line.append(InlineKeyboardButton(item[0], url=item[1]))
            else:
                text, data = item[0], item[1]
                if isinstance(data, str) and (data.startswith("http://") or data.startswith("https://") or data.startswith("tg://")):
                    line.append(InlineKeyboardButton(text, url=data))
                else:
                    line.append(InlineKeyboardButton(text, callback_data=data))
        out.append(line)
    return InlineKeyboardMarkup(out)


def back(data='home'):
    return inline([[("🔙 Orqaga", data)]])
