import requests
from flask import Flask, request

# =========================
# НАСТРОЙКИ (SETTINGS)
# =========================
TOKEN = "9159865735:AAEUGdp6SFXjOQ5aJ7guN02Gn_9N1wvRSb4"
ADMIN_ID = 7793697237
WEBHOOK_URL = f"https://ixxky.pythonanywhere.com/9159865735:AAEUGdp6SFXjOQ5aJ7guN02Gn_9N1wvRSb4"
BASE_URL = f"https://api.telegram.org/bot9159865735:AAEUGdp6SFXjOQ5aJ7guN02Gn_9N1wvRSb4/"

app = Flask(__name__)
user_states = {}
admin_reply_target = {}


def api_request(method, data=None):
    url = BASE_URL + method
    try:
        if data:
            r = requests.post(url, json=data, timeout=10)
        else:
            r = requests.get(url, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Ошибка API: {e}")
        return {"ok": False, "error": str(e)}


def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    if parse_mode:
        data["parse_mode"] = parse_mode
    return api_request("sendMessage", data)


def copy_message(chat_id, from_chat_id, message_id):
    return api_request("copyMessage", {
        "chat_id": chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id
    })


main_menu = {
    "keyboard": [[{"text": "Подать заявку"}], [{"text": "Подать жалобу"}]],
    "resize_keyboard": True
}

cancel_menu = {
    "keyboard": [[{"text": "Отмена"}]],
    "resize_keyboard": True
}


def admin_keyboard(user_id, is_application):
    buttons = [[{"text": "✉️ Ответить лично", "callback_data": f"reply:{user_id}"}]]
    if is_application:
        buttons.append([{"text": "❌ Отклонить заявку", "callback_data": f"reject:{user_id}"}])
    return {"inline_keyboard": buttons}


def handle_message(message):
    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    user_id = user.get("id")
    username = f"@{user['username']}" if user.get("username") else "не указан"
    text = message.get("text", "")
    message_id = message["message_id"]
    state = user_states.get(user_id)

    if text == "/start":
        user_states.pop(user_id, None)
        send_message(chat_id, "Добро пожаловать в Telegram-бот!\n\nПожалуйста, выберите необходимую команду:", reply_markup=main_menu)
        return

    if text in ["/cancel", "Отмена"]:
        user_states.pop(user_id, None)
        send_message(chat_id, "Текущая операция отменена.", reply_markup=main_menu)
        return

    if text == "Подать заявку":
        user_states[user_id] = "application"
        send_message(
            chat_id,
            "ФОРМА ЗАЯВКИ\n\nПожалуйста, заполните все пункты и отправьте заявку одним сообщением.\n\n"
            "1. Роль: персонаж, от имени которого вы хотите вступить.\n"
            "2. Telegram username: ваш актуальный юзернейм.\n"
            "3. Возраст: укажите свой возраст.\n\n"
            "После отправки заявка будет передана администрации на рассмотрение.",
            reply_markup=cancel_menu
        )
        return

    if text == "Подать жалобу":
        user_states[user_id] = "complaint"
        send_message(
            chat_id,
            "ПОДАЧА ЖАЛОБЫ\n\nЖалоба подаётся в свободной форме. Пожалуйста, изложите в одном сообщении "
            "ситуацию и укажите, что именно вы считаете неприемлемым.\n\n"
            "Администрация рассмотрит обращение и при необходимости примет соответствующие меры.",
            reply_markup=cancel_menu
        )
        return

    if state == "admin_reply" and user_id == ADMIN_ID:
        target_id = admin_reply_target.get(ADMIN_ID)
        res = copy_message(target_id, chat_id, message_id)
        if res and res.get("ok"):
            send_message(chat_id, "✅ Ваше сообщение успешно отправлено пользователю.", reply_markup=main_menu)
        else:
            send_message(chat_id, "Не удалось отправить сообщение.", reply_markup=main_menu)
        user_states.pop(user_id, None)
        return

    if state == "application":
        send_message(
            ADMIN_ID,
            f"📩 <b>НОВАЯ ЗАЯВКА</b>\n\nПользователь: {username}\nTelegram ID: <code>{user_id}</code>",
            reply_markup=admin_keyboard(user_id, True),
            parse_mode="HTML"
        )
        copy_message(ADMIN_ID, chat_id, message_id)
        send_message(chat_id, "Ваша заявка успешно принята и передана администрации. Пожалуйста, ожидайте ответа администратора.", reply_markup=main_menu)
        user_states.pop(user_id, None)
        return

    if state == "complaint":
        send_message(
            ADMIN_ID,
            f"⚠️ <b>НОВАЯ ЖАЛОБА</b>\n\nПользователь: {username}\nTelegram ID: <code>{user_id}</code>",
            reply_markup=admin_keyboard(user_id, False),
            parse_mode="HTML"
        )
        copy_message(ADMIN_ID, chat_id, message_id)
        send_message(chat_id, "Ваша жалоба успешно принята и передана администрации. Благодарим за обращение.", reply_markup=main_menu)
        user_states.pop(user_id, None)
        return


def handle_callback(callback):
    cb_id = callback["id"]
    user_id = callback["from"]["id"]
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if user_id != ADMIN_ID:
        api_request("answerCallbackQuery", {"callback_query_id": cb_id, "text": "У вас нет доступа.", "show_alert": True})
        return

    if data.startswith("reply:"):
        target_id = int(data.split(":")[1])
        admin_reply_target[ADMIN_ID] = target_id
        user_states[ADMIN_ID] = "admin_reply"
        send_message(chat_id, f"Введите сообщение для пользователя с ID {target_id}.\nДля отмены нажмите Отмена или /cancel.", reply_markup=cancel_menu)
        api_request("answerCallbackQuery", {"callback_query_id": cb_id})

    elif data.startswith("reject:"):
        target_id = int(data.split(":")[1])
        res = send_message(target_id, "К сожалению, ваша заявка не была одобрена администрацией.\n\nБлагодарим за интерес к нашему сообществу.")
        if res and res.get("ok"):
            api_request("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}})
            api_request("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Заявка отклонена."})
        else:
            api_request("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Не удалось уведомить пользователя.", "show_alert": True})


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(silent=True)
    if update:
        if "message" in update:
            handle_message(update["message"])
        elif "callback_query" in update:
            handle_callback(update["callback_query"])
    return "OK", 200


@app.route("/")
def index():
    return "Сервер бота работает 24/7!"
