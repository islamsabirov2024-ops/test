from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def reply(rows, one_time: bool = False):
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=one_time, input_field_placeholder='Menyudan tanlang...')


def inline(rows):
    out = []
    for row in rows:
        buttons = []
        for item in row:
            text, data = item[0], item[1]
            if isinstance(data, str) and (data.startswith('http://') or data.startswith('https://') or data.startswith('t.me/')):
                url = data if data.startswith('http') else 'https://' + data
                buttons.append(InlineKeyboardButton(text, url=url))
            else:
                buttons.append(InlineKeyboardButton(text, callback_data=data))
        out.append(buttons)
    return InlineKeyboardMarkup(out)
