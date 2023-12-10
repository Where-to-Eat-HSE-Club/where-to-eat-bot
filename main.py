import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

try:
    from config import TOKEN, DEV, LINE_SEPARATOR
except ModuleNotFoundError:
    print("Config file config.py not found! Please create one and fill with TOKEN, DEV and LINE_SEPARATOR")
    sys.exit(1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

admin_ids = []
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

POST_NAME, PLACE_NAME, AUTHOR_NAME, BODY_TEXT, ADDRESS_ADD, CONFIRM, WAITING_FOR_CONFIRM = range(7)


async def new_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"{update.message.from_user.name} is creating a new post...")
    await update.message.reply_text(
        "Начинаю создавать пост. \n"
        "Отправьте /cancel чтобы отменить создание поста. \n\n"
        "Введите название поста.",
    )

    return POST_NAME


async def process_post_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    post_name = update.message.text.strip()
    write_to_file(post_name)
    logger.info(f"Post name from {user.first_name}: {post_name}")
    await update.message.reply_text(
        f"Принял название поста - '{post_name}'.\n"
        "Отправьте название места, о котором пост (например Андерсон).",
    )

    return PLACE_NAME


async def process_place_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    place_name = update.message.text.strip()
    write_to_file(place_name)
    logger.info(f"Place name from {user.first_name}: {place_name}")
    await update.message.reply_text(
        f"Принял название места - '{place_name}'.\n"
        "Отправьте имя автора (например Игорь).",
    )

    return AUTHOR_NAME


async def process_author_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    author_name = update.message.text.strip()
    write_to_file(author_name)
    logger.info(f"Author name of {user.first_name} is {author_name}")
    await update.message.reply_text(
        f"Принял имя автора - '{author_name}'.\n"
        "Отправьте весь текст поста.",
    )

    return BODY_TEXT


async def process_body_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    body_text = update.message.text.strip()
    write_to_file(body_text)
    logger.info(f"Body text of post starts with {body_text[:10]}")
    await update.message.reply_text(
        f"Принял текст поста.\n"
        "Отправляйте последовательно адреса, которые связаны с местом, о котором пост.\n"
        "Когда отправили все адреса или адресов нет, отправьте СТОП."
    )

    return ADDRESS_ADD


def get_cur_new_post_contents():
    with open("new_post.txt", "r", encoding="utf-8") as f:
        contents = "".join(list(map(lambda x: x.replace(LINE_SEPARATOR, ""), f.readlines())))
    return contents


async def process_address_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    address = update.message.text.strip()

    if address.lower() == "стоп":
        logger.info("Stopped adding addresses")

        await update.effective_chat.send_message(get_cur_new_post_contents())
        await update.message.reply_text(
            "Перепроверьте и подтвердите введённые данные.\n"
            "Отправьте НЕТ, чтобы изменить данные, ДА, чтобы подтвердить создание поста."
        )
        return CONFIRM

    logger.info(f"Added new address {address}")
    write_to_file(address)
    await update.message.reply_text(
        f"Принял адрес - '{address}'.\n"
        "Отправьте следующий адрес или отправьте СТОП."
    )

    return ADDRESS_ADD


async def process_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    confirmation = update.message.text.strip()
    if confirmation.lower() == "да":
        logger.info("Confirmed new post")
        await update.message.reply_text(
            "Начинаю голосование... Кто-нибудь из админов, отправьте /confirm, тогда добавлю пост на сайт."
        )
        return WAITING_FOR_CONFIRM
    elif confirmation.lower() == "нет":
        logger.info("Cancelled new post to create new one")
        await update.message.reply_text(
            "Пока изменение введённых данных невозможно, "
            "отмените создание поста (/cancel) и введите заново уже верные данные."
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Не понял... Попробуйте ещё раз. Отправьте ДА или НЕТ."
        )
        return CONFIRM


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Отменил создание поста."
    )
    clear_file()

    return ConversationHandler.END


def clear_file():
    with open("new_post.txt", "w", encoding="utf-8"):
        pass


def write_to_file(text: str):
    with open("new_post.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n" + LINE_SEPARATOR + "\n")


def get_admin_ids():
    try:
        with open("admin_ids.txt", "r") as f:
            ids = list(map(int, f.readline().strip().split()))
        return ids
    except FileNotFoundError:
        logger.error("File admin_ids.txt does not exist! Please create one and populate it with telegram admin ids")

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    current_admin_ids = get_admin_ids()
    if user_id in current_admin_ids:
        await update.message.reply_text(f"Принял подтверждение от {update.message.from_user.first_name}.\n"
                                        f"Добавляю пост на сайт...")

        # TODO Insert data extraction to DB here, before the file is cleaned

        clear_file()

        return ConversationHandler.END

    else:
        logger.warning(f"User id {user_id} not in list")
        await update.message.reply_text(f"Пользователя {update.message.from_user.first_name} нет в списке админов.\n"
                                        f"Если это ошибка, обратитесь к разработчику ({DEV}).")
        return WAITING_FOR_CONFIRM


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Ничего не понимаю... Напишите /help для помощи.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет, я бот для создания постов на сайте, напишите /help для справки.")


async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Чтобы начать создавать новый пост напишите /new_post и следуйте всем инструкциям.")


async def send_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.from_user.id)


def main() -> None:
    clear_file()
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("new_post", new_post)],
        states={
            POST_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), process_post_name)],
            PLACE_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), process_place_name), ],
            AUTHOR_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), process_author_name), ],
            BODY_TEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), process_body_text)],
            ADDRESS_ADD: [MessageHandler(filters.TEXT & (~filters.COMMAND), process_address_add)],
            CONFIRM: [MessageHandler(filters.TEXT & (~filters.COMMAND), process_confirmation)],
            WAITING_FOR_CONFIRM: [CommandHandler("confirm", handle_confirmation)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    help_handler = CommandHandler('help', send_help)
    application.add_handler(help_handler)

    get_id_handler = CommandHandler('get_id', send_get_id)
    application.add_handler(get_id_handler)

    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
