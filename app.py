import requests
from flask import Flask, request

# ==========================
# НАСТРОЙКИ (SETTINGS)
# ==========================
TOKEN = "915986735:AAEUGdp6SFXjOQ5aj7gun02Gn_9N1wvRSb4"
ADMIN_ID = 7793697237
BASE_URL = f"https://api.telegram.org/bot915986735:AAEUGdp6SFXjOQ5aj7gun02Gn_9N1wvRSb4/"

app = Flask(__name__)
user_states = {}
admin_reply_target = {}

def api_request(method, data=None):
    url = BASE_URL + method
    try:
        if data:
            response = requests.post(url, json=data)
        else:
            response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"API Error ({method}): {e}")
        return None

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    res = api_request("sendMessage", data)
    return res

def copy_message(chat_id, from_chat_id, message_id):
    data = {
        "chat_id": chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id
    }
    return api_request("copyMessage", data)

# Клавиатуры (Keyboards)
main_menu = {
    "keyboard": [
        [{"text": "Подать заявку"}, {"text": "Подать жалобу"}]
    ],
    "resize_keyboard": True
}

cancel_menu = {
    "keyboard": [
        [{"text": "Отмена"}]
    ],
    "resize_keyboard": True
}

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user_id = message["from"]["id"]

    if text == "/start":
        user_states.pop(user_id, None)
        send_message(chat_id, "Привет! Добро пожаловать в бота.", reply_markup=main_menu)
        return

    if text == "Отмена":
        user_states.pop(user_id, None)
        admin_reply_target.pop(user_id, None)
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
            "Администрация рассмотрит обращение и примет соответствующие меры.",
            reply_markup=cancel_menu
        )
        return

    state = user_states.get(user_id)

    # Обработка ответа администратора
    if state == "admin_reply" and user_id == ADMIN_ID:
        target_id = admin_reply_target.get(ADMIN_ID)
        res = copy_message(target_id, chat_id, message["message_id"])
        if res and res.get("ok"):
            send_message(ADMIN_ID, "Сообщение успешно отправлено пользователю!", reply_markup=main_menu)
        else:
            send_message(ADMIN_ID, "Не удалось отправить сообщение пользователю.", reply_markup=main_menu)
        user_states.pop(user_id, None)
        admin_reply_target.pop(user_id, None)
        return

    # Обработка пользовательской заявки
    if state == "application":
        user_states.pop(user_id, None)
        send_message(chat_id, "Ваша заявка успешно отправлена администрации!", reply_markup=main_menu)
        
        admin_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Одобрить", "callback_data": f"approve:{user_id}"},
                    {"text": "❌ Отклонить", "callback_data": f"reject:{user_id}"}
                ]
            ]
        }
        send_message(ADMIN_ID, f"Новая заявка от пользователя (ID: {user_id}):")
        copy_message(ADMIN_ID, chat_id, message["message_id"])
        send_message(ADMIN_ID, "Выберите действие:", reply_markup=admin_keyboard)
        return

    # Обработка пользовательской жалобы
    if state == "complaint":
        user_states.pop(user_id, None)
        send_message(chat_id, "Ваша жалоба отправлена администрации.", reply_markup=main_menu)
        
        send_message(ADMIN_ID, f"Новая жалоба от пользователя (ID: {user_id}):")
        copy_message(ADMIN_ID, chat_id, message["message_id"])
        return

    send_message(chat_id, "Пожалуйста, используйте кнопки меню.", reply_markup=main_menu)

def handle_callback(callback_query):
    data = callback_query["data"]
    message = callback_query["message"]
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    cb_id = callback_query["id"]

    if data.startswith("approve:"):
        target_id = int(data.split(":")[1])
        res = send_message(target_id, "Поздравляем! Ваша заявка одобрена администрацией.")
        if res and res.get("ok"):
            api_request("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}})
            api_request("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Заявка одобрена."})
        else:
            api_request("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Не удалось уведомить пользователя."})

    elif data.startswith("reject:"):
        target_id = int(data.split(":")[1])
        res = send_message(target_id, "К сожалению, ваша заявка не была одобрена администрацией.")
        if res and res.get("ok"):
            api_request("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}})
            api_request("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Заявка отклонена."})
        else:
            api_request("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Не удалось уведомить пользователя."})

@app.route("/", methods=["POST"])
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
