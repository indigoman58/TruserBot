from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest
import telegram
from telegram.error import Forbidden
from telegram.ext import (
    Application,
    ChatJoinRequestHandler,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
import os

# Bot tokeninizi daxil edin
TOKEN = "7261554455:AAFOKss9hSPsLAh1q2V4c02cOydXuaIMdlg"
ADMIN_ID = 5344901095

# Qlobal dəyişənlər
pending_requests = {}  # Gözləmədə olan istifadəçilər
users_file = "users.json"  # Fayl adı
channels_file = "channels.json"  # Kanalları saxlayan fayl
custom_message = "Salam kanala xoş gəlmisiniz!"  # Şəxsi mesaj məzmunu
custom_image_path = "images/default.jpg"  # Default şəkil yolu
buttons_file = "buttons.json"  # Düymələri saxlayan fayl
MAX_BUTTONS = 5  # Maksimum düymə sayı

# Qovluq yaradılır
os.makedirs("images", exist_ok=True)


# Fayl təmizləmə funksiyası


# Fayl oxuma və yazma funksiyaları
# Kanalları fayldan oxumaq funksiyası
def read_channels():
    if not os.path.isfile(channels_file):
        open(channels_file, "w", encoding="utf-8").close()
    with open(channels_file, "r", encoding="utf-8") as file:
        return file.read().splitlines()


# Kanalları fayla yazmaq funksiyası
def write_channels(channels):
    with open(channels_file, "w", encoding="utf-8") as file:
        file.write("\n".join(channels) + "\n")


def read_buttons():
    if not os.path.isfile(buttons_file):
        open(
            buttons_file, "w", encoding="utf-8"
        ).close()  # Fayl mövcud deyilsə yaradılır
        return []
    with open(buttons_file, "r", encoding="utf-8") as file:
        buttons = []
        for line in file:
            try:
                text, link = line.strip().split("||", 1)
                buttons.append((text, link))
            except ValueError:
                print(f"Düzgün olmayan sətir tapıldı: {line.strip()}")
        return buttons


def write_buttons(buttons):
    if len(buttons) > MAX_BUTTONS:
        raise ValueError(f"Düymə sayı maksimum {MAX_BUTTONS} ola bilər!")
    with open(buttons_file, "w", encoding="utf-8") as file:
        for text, link in buttons:
            file.write(f"{text}||{link}\n")


# Unicode font dönüşüm funksiyası
def convert_to_font(text: str, font: str) -> str:
    fonts = {
        "bold": lambda char: chr(0x1D400 + (ord(char) - 0x41))
        if "A" <= char <= "Z"
        else chr(0x1D41A + (ord(char) - 0x61))
        if "a" <= char <= "z"
        else char,
        "italic": lambda char: chr(0x1D434 + (ord(char) - 0x41))
        if "A" <= char <= "Z"
        else chr(0x1D44E + (ord(char) - 0x61))
        if "a" <= char <= "z"
        else char,
        "bold_italic": lambda char: chr(0x1D468 + (ord(char) - 0x41))
        if "A" <= char <= "Z"
        else chr(0x1D482 + (ord(char) - 0x61))
        if "a" <= char <= "z"
        else char,
        "monospace": lambda char: chr(0x1D670 + (ord(char) - 0x41))
        if "A" <= char <= "Z"
        else chr(0x1D68A + (ord(char) - 0x61))
        if "a" <= char <= "z"
        else char,
    }
    if font not in fonts:
        return text  # Əgər font tapılmazsa, orijinal mətni qaytarır
    return "".join(fonts[font](char) for char in text)



# Düymələri düzmək üçün funksiyanı əlavə edin
def arrange_buttons(buttons, vertical=False):
    if vertical:
        keyboard = [[InlineKeyboardButton(text, url=link)] for text, link in buttons]
    else:
        keyboard = []
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                keyboard.append(
                    [
                        InlineKeyboardButton(buttons[i][0], url=buttons[i][1]),
                        InlineKeyboardButton(buttons[i + 1][0], url=buttons[i + 1][1]),
                    ]
                )
            else:
                keyboard.append(
                    [InlineKeyboardButton(buttons[i][0], url=buttons[i][1])]
                )
    return InlineKeyboardMarkup(keyboard)


# Button silmək
def remove_button(button_index):
    buttons = read_buttons()
    if 0 <= button_index < len(buttons):
        removed_button = buttons.pop(button_index)
        write_buttons(buttons)
        return removed_button
    else:
        raise IndexError("Düymə indeksi mövcud deyil.")


def admin_only(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if update.message and update.message.from_user.id != ADMIN_ID:
            await update.message.reply_text(
                "Bu əməliyyat yalnız adminlər üçün mümkündür!"
            )
            return
        if update.callback_query and update.callback_query.from_user.id != ADMIN_ID:
            await update.callback_query.answer(
                "Bu əməliyyat yalnız adminlər üçün mümkündür!"
            )
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


# statistikalar
async def send_statistics(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Bu əməliyyat yalnız adminlər üçün mümkündür!")
        return

    try:
        # İstifadəçi faylının mövcudluğunu təmin edin
        if not os.path.isfile(users_file):
            open(users_file, "w", encoding="utf-8").close()

        # Statistikanı hesablamaq
        total_requests = len(pending_requests)
        total_users = 0
        if os.path.isfile(users_file):
            with open(users_file, "r", encoding="utf-8") as file:
                total_users = sum(1 for _ in file)

        stats_message = (
            f"Statistika:\n"
            f"- Gözləmədə olan istəklərin sayı: {total_requests}\n"
            f"- Toplam qoşulan istifadəçilər: {total_users}"
        )

        # Sıfırlama düyməsi
        keyboard = [
            [
                InlineKeyboardButton(
                    "Statistikanı Sıfırla", callback_data="reset_statistics"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(stats_message, reply_markup=reply_markup)

    except Exception as e:
        print(f"Statistika hesablama zamanı xəta baş verdi: {e}")
        await update.message.reply_text(
            "Statistika məlumatları alınarkən xəta baş verdi."
        )


async def handle_statistics_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "reset_statistics":
        pending_requests.clear()
        if os.path.isfile(users_file):
            open(users_file, "w", encoding="utf-8").close()
        await query.edit_message_text("Statistika sıfırlandı!")



# --- Statistikaları sıfırlamaq ---
async def reset_statistics(update: Update, context: CallbackContext) -> None:
    try:
        # Gözləmədə olan istəkləri təmizləyirik
        pending_requests.clear()
        # Faylı təmizləyirik
        if os.path.isfile(users_file):
            open(users_file, "w", encoding="utf-8").close()
        await update.message.reply_text("Statistika sıfırlandı!")
        print("Statistika sıfırlandı.")
    except Exception as e:
        error_message = f"Statistikanı sıfırlamaq zamanı xəta baş verdi: {e}"
        print(error_message)
        await update.message.reply_text(error_message)


# Admin paneli
async def send_admin_panel(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Bu əməliyyat yalnız adminlər üçün mümkündür!")
        return

    admin_keyboard = [
        [InlineKeyboardButton("Mesajı Dəyiş", callback_data="change_message")],
        [InlineKeyboardButton("Şəkil Yolunu Dəyiş", callback_data="change_image")],
        [InlineKeyboardButton("Düymə Əlavə Et", callback_data="add_button")],
        [InlineKeyboardButton("Düymələri Görüntülə", callback_data="view_buttons")],
        [InlineKeyboardButton("Düyməni Sil", callback_data="remove_button")],
        [
            InlineKeyboardButton(
                "Düymələri Alt-Alta Düz", callback_data="set_vertical_buttons"
            )
        ],
        [
            InlineKeyboardButton(
                "Düymələri Maksimum 2 Yanaşı Düz",
                callback_data="set_horizontal_buttons",
            )
        ],
    ]
    admin_markup = InlineKeyboardMarkup(admin_keyboard)
    await update.message.reply_text("Admin Paneli:", reply_markup=admin_markup)


#   məhdudiyyətlər
def is_channel_allowed(chat_id: int) -> bool:
    """İcazə verilmiş kanalları yoxlayır."""
    allowed_channels = read_channels()  # Əlavə edilmiş kanalları fayldan oxuyur
    return str(chat_id) in allowed_channels


# Qoşulma istəklərini idarə et
button_layout = "vertical"  # Standart dəyər


async def handle_join_request(update: Update, context: CallbackContext) -> None:
    global button_layout
    chat_id = update.chat_join_request.chat.id
    user = update.chat_join_request.from_user

    if not is_channel_allowed(chat_id):
        print(f"İcazəsiz kanal: {chat_id}")
        return

    pending_requests[user.id] = chat_id

    with open(users_file, "a", encoding="utf-8") as file:
        file.write(f"{user.id},{user.first_name}\n")

    buttons = read_buttons()
    if button_layout == "vertical":
        reply_markup = arrange_buttons(buttons, vertical=True)
    else:
        reply_markup = arrange_buttons(buttons, vertical=False)

    try:
        if custom_image_path and os.path.isfile(custom_image_path):
            with open(custom_image_path, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=photo,
                    caption=custom_message,
                    reply_markup=reply_markup,
                )
        else:
            await context.bot.send_message(
                chat_id=user.id, text=custom_message, reply_markup=reply_markup
            )
    except telegram.error.Forbidden:
        print(f"Bot istifadəçi ilə söhbəti başlada bilmir: {user.id}")
    except Exception as e:
        print(f"Mesaj göndərmə zamanı xəta: {e}")


# --- 2. Qarşılama mesajı ---
async def start(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Bu bot yalnız admin üçün aktivdir!")
        return



    keyboard = [[InlineKeyboardButton("Kanal Əlavə Et", callback_data="add_channel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        "🤖 Bot Haqqında Məlumat \n\n"
        " 📂 Funksiyalar:\n"
        "- Kanala qoşulma istəklərini idarə edir\n"
        "- Statistikaları izləyir\n"
        "- Adminlər üçün xüsusi panel təqdim edir\n"
        "- İstifadəçilərə şəxsi mesaj və düymələr göndərir\n"
        "- Qoşulma istəklərini təsdiq və rədd edir\n\n"
        "🔑  Admin Əmrləri:\n"
        "/panel - Admin panelini açır\n"
        "/statistika - İstifadəçi və istək statistikalarını göstərir\n"
        "/kanallar - Əlavə edilmiş kanalların siyahısını göstərir\n"
        "/istek - İstək menyusunu açır\n"
        "/gonder_fayl - İstifadəçilərin siyahısını fayl olaraq göndərir\n\n"
        " ℹ️ Bu bot Azərbaycanda kanalları idarə etmək üçün yaradılmış ilk idarə botudur.\n"
    )
    if update.message:
        # Əgər mesaj mövcuddursa
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    elif update.callback_query:
        # Əgər callback query mövcuddursa
        await update.callback_query.edit_message_text(
            welcome_text, reply_markup=reply_markup
        )


async def handle_start_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "add_channel":
        context.user_data["awaiting_channel"] = True
        await query.message.reply_text("Zəhmət olmasa kanal ID-sini göndərin:")


# Yeni düymələri əlavə etmək
async def unified_message_handler(update: Update, context: CallbackContext) -> None:
    message_text = update.message.text.strip()
    user_data = context.user_data

    if user_data.get("awaiting_message"):
        global custom_message
        custom_message = message_text
        await update.message.reply_text("Mesaj məzmunu yeniləndi!")
        user_data["awaiting_message"] = False

    elif user_data.get("awaiting_image"):
        global custom_image_path
        if os.path.isfile(message_text):
            custom_image_path = message_text
            await update.message.reply_text("Şəkil yolu yeniləndi!")
        else:
            await update.message.reply_text("Xəta: Fayl yolu tapılmadı.")
        user_data["awaiting_image"] = False

    elif user_data.get("awaiting_button_text"):
        user_data["new_button_text"] = message_text
        user_data["awaiting_button_text"] = False
        user_data["awaiting_button_link"] = True
        await update.message.reply_text("Düymənin linkini göndərin:")

    elif user_data.get("awaiting_button_link"):
        new_button_text = user_data.pop("new_button_text", None)
        new_button_link = message_text
        if new_button_text:
            buttons = read_buttons()
            buttons.append((new_button_text, new_button_link))
            write_buttons(buttons)
            await update.message.reply_text("Düymə uğurla əlavə edildi!")
        user_data["awaiting_button_link"] = False

    # 2. Kanal əlavə etmə
    elif user_data.get("awaiting_channel"):
        user_data["awaiting_channel"] = False  # Bayrağı sıfırlayırıq
        if not (message_text.startswith("-100") and message_text[1:].isdigit()):
            await update.message.reply_text("Xəta: Kanal ID-si düzgün formatda deyil!")
            return



        try:
            chat = await context.bot.get_chat(chat_id=message_text)
            bot_member = await context.bot.get_chat_member(
                chat_id=message_text, user_id=context.bot.id
            )
            if bot_member.status not in ["administrator", "creator"]:
                await update.message.reply_text(
                    f"Bot bu kanalda admin deyil: {chat.title}"
                )
            else:
                added_channels = read_channels()
                if message_text in added_channels:
                    await update.message.reply_text(
                        f"Bot artıq bu kanala əlavə olunub: {chat.title}"
                    )
                else:
                    added_channels.append(message_text)
                    write_channels(added_channels)
                    await update.message.reply_text(
                        f"Kanal uğurla əlavə edildi: {chat.title}"
                    )
        except Exception as e:
            await update.message.reply_text(
                f"Kanal əlavə edilərkən xəta baş verdi və ya ID düzgün deyil: {e}"
            )


# Callback Query idarəetməsi
@admin_only
async def handle_admin_actions(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    global button_layout  # Dəyişəni qlobal etmək
    if query.data == "set_vertical_buttons":
        button_layout = "vertical"
        await query.message.reply_text("Düymələr alt-alta düzüləcək.")
        buttons = read_buttons()
        if not buttons:
            await query.message.reply_text("Heç bir düymə əlavə edilməyib.")
            return
        reply_markup = arrange_buttons(buttons, vertical=True)  # Alt-alta düzülüş
        await query.message.reply_text(
            "Düymələr alt-alta düzülüb:", reply_markup=reply_markup
        )

    elif query.data == "set_horizontal_buttons":
        button_layout = "horizontal"
        await query.message.reply_text("Düymələr maksimum iki yanaşı düzüləcək.")
        buttons = read_buttons()
        if not buttons:
            await query.message.reply_text("Heç bir düymə əlavə edilməyib.")
            return
        reply_markup = arrange_buttons(
            buttons, vertical=False
        )  # Maksimum 2 yanaşı düzülüş
        await query.message.reply_text(
            "Düymələr maksimum iki yanaşı düzülüb:", reply_markup=reply_markup
        )
    if query.data == "change_message":
        context.user_data["awaiting_message"] = True
        await query.message.reply_text("Yeni mesaj məzmununu göndərin:")
    elif query.data == "change_image":
        context.user_data["awaiting_image"] = True
        await query.message.reply_text("Şəkil yolunu göndərin:")
    elif query.data == "add_button":
        context.user_data["awaiting_button_text"] = True
        await query.message.reply_text("Düymənin mətnini göndərin:")

    if query.data == "view_buttons":
        buttons = []  # Default olaraq boş siyahı təyin edirik
        try:
            buttons = read_buttons()  # Düymələri oxuyuruq
        except Exception as e:
            await query.message.reply_text(f"Düymələri yükləyərkən xəta baş verdi: {e}")
            return

        if not buttons:
            await query.message.reply_text("Heç bir düymə əlavə edilməyib.")
            return

        # Mövcud düymələri göstəririk
        reply_text = "Mövcud düymələr:\n"
        for i, (text, link) in enumerate(buttons, start=1):
            reply_text += f"{i}. {text} - {link}\n"
        await query.message.reply_text(reply_text)



    elif query.data == "remove_button":
        buttons = read_buttons()
        if not buttons:
            await query.message.reply_text("Heç bir düymə əlavə edilməyib.")
            return
        keyboard = [
            [InlineKeyboardButton(f"{i+1}. {text}", callback_data=f"delete_{i}")]
            for i, (text, link) in enumerate(buttons)
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "Silinəcək düyməni seçin:", reply_markup=reply_markup
        )
    if query.data == "arrange_vertical":
        buttons = read_buttons()
        if not buttons:
            await query.message.reply_text("Heç bir düymə əlavə edilməyib.")
            return
        reply_markup = arrange_buttons(buttons, vertical=True)  # Alt-alta düz
        await query.message.reply_text(
            "Düymələr alt-alta düzülüb:", reply_markup=reply_markup
        )

    elif query.data == "arrange_horizontal":
        buttons = read_buttons()
        if not buttons:
            await query.message.reply_text("Heç bir düymə əlavə edilməyib.")
            return
        reply_markup = arrange_buttons(
            buttons, vertical=False
        )  # Maksimum 2 düymə yanaşı
        await query.message.reply_text(
            "Düymələr maksimum iki yanaşı düzülüb:", reply_markup=reply_markup
        )


async def handle_delete_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    button_index = int(query.data.replace("delete_", ""))
    try:
        removed_button = remove_button(button_index)
        await query.message.edit_text(
            f"Düymə silindi: {removed_button[0]} - {removed_button[1]}"
        )
    except IndexError:
        await query.message.edit_text("Xəta: Düymə mövcud deyil.")


async def handle_admin_input(update: Update, context: CallbackContext) -> None:
    global custom_message, custom_button_link, custom_image_path

    if context.user_data.get("awaiting_message"):  # Mesaj dəyişmək üçün
        custom_message = update.message.text
        await update.message.reply_text("Mesaj məzmunu yeniləndi!")
        context.user_data["awaiting_message"] = False
    elif context.user_data.get("awaiting_link"):  # Link dəyişmək üçün
        custom_button_link = update.message.text
        await update.message.reply_text("Düymə linki yeniləndi!")
        context.user_data["awaiting_link"] = False
    elif context.user_data.get("awaiting_image"):  # Şəkil dəyişmək üçün
        if os.path.isfile(update.message.text):
            custom_image_path = update.message.text
            await update.message.reply_text("Şəkil yolu yeniləndi!")
        else:
            await update.message.reply_text("Xəta: Fayl yolu tapılmadı.")
        context.user_data["awaiting_image"] = False
    else:
        await update.message.reply_text("Heç bir əməliyyat gözlənilmir.")


# --- 5. Yeni şəkil yükləmək ---
async def handle_photo_upload(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id == ADMIN_ID and update.message.photo:
        file_id = update.message.photo[-1].file_id
        new_file = await context.bot.get_file(file_id)
        file_path = f"images/uploaded_{file_id}.jpg"
        await new_file.download_to_drive(file_path)
        global custom_image_path
        custom_image_path = file_path
        await update.message.reply_text(f"Yeni şəkil yükləndi: {file_path}")
    else:
        await update.message.reply_text("Yalnız admin yeni şəkil yükləyə bilər!")



# --- 6. İstəkləri idarə paneli ---
async def send_request_panel(update: Update, context: CallbackContext) -> None:
    # Yalnız adminlərə icazə vermək üçün yoxlama
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Bu əməliyyat yalnız adminlər üçün mümkündür!")
        return
    request_keyboard = [
        [
            InlineKeyboardButton(
                "Bütün istəkləri Təsdiq Et", callback_data="approve_all"
            )
        ],
        [InlineKeyboardButton("Bütün istəkləri Rədd Et", callback_data="deny_all")],
    ]
    request_markup = InlineKeyboardMarkup(request_keyboard)
    await update.message.reply_text("İstəkləri idarə et:", reply_markup=request_markup)


# --- 7. Bütün istəkləri təsdiq et və ya rədd et ---
async def approve_all_requests(update: Update, context: CallbackContext) -> None:
    if not pending_requests:
        await update.callback_query.answer("Təsdiqlənəcək istək yoxdur.")
        return

    for user_id, chat_id in pending_requests.items():
        try:
            await context.bot.approve_chat_join_request(
                chat_id=chat_id, user_id=user_id
            )
        except Exception as e:
            print(f"Təsdiq xətası: {e}")
    pending_requests.clear()
    await update.callback_query.edit_message_text("Bütün istəklər təsdiq edildi!")


async def deny_all_requests(update: Update, context: CallbackContext) -> None:
    pending_requests.clear()
    await update.callback_query.edit_message_text("Bütün istəklər rədd edildi!")


# --- 9. Kanal əlavə etmək---
@admin_only
async def add_channel(update: Update, context: CallbackContext) -> None:
    try:
        if len(context.args) != 1:
            await update.message.reply_text(
                "Zəhmət olmasa kanal ID-sini daxil edin: /add <kanal_id>"
            )
            return

        channel_id = context.args[0]

        # Kanalın mövcud olub olmadığını yoxlayırıq
        try:
            chat = await context.bot.get_chat(chat_id=channel_id)
        except Exception as e:
            await update.message.reply_text("Kanal ID-si yanlışdır və ya mövcud deyil.")
            print(f"Kanal yoxlama zamanı xəta: {e}")
            return

        # Botun admin olub olmadığını yoxlayırıq
        bot_member = await context.bot.get_chat_member(
            chat_id=channel_id, user_id=context.bot.id
        )
        if bot_member.status not in ["administrator", "creator"]:
            await update.message.reply_text(f"Bot bu kanalda admin deyil: {chat.title}")
            return

        # Fayla əlavə edirik
        added_channels = []
        if os.path.isfile(channels_file):
            with open(channels_file, "r", encoding="utf-8") as file:
                added_channels = file.read().splitlines()

        if channel_id in added_channels:
            await update.message.reply_text(
                f"Bot artıq bu kanala əlavə olunub: {chat.title}"
            )
        else:
            with open(channels_file, "a", encoding="utf-8") as file:
                file.write(channel_id + "\n")
            await update.message.reply_text(f"Kanal uğurla əlavə edildi: {chat.title}")
    except Exception as e:
        error_message = f"Kanal əlavə edilərkən xəta baş verdi: {e}"
        print(error_message)
        await update.message.reply_text(error_message)



# 9. Kanalları Göstərən Funksiya
async def list_channels(update: Update, context: CallbackContext) -> None:
    # Admin yoxlaması
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Bu əməliyyat yalnız adminlər üçün mümkündür!")
        return
    try:
        channels = read_channels()
        if channels:
            keyboard = []
            for channel_id in channels:
                try:
                    chat = await context.bot.get_chat(chat_id=channel_id)
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                text=f"{chat.title}",
                                callback_data=f"remove_{channel_id}",
                            )
                        ]
                    )
                except Exception:
                    continue

            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "Əlavə olunmuş kanallar:", reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("Heç bir kanal əlavə edilməyib.")
        else:
            await update.message.reply_text("Heç bir kanal əlavə edilməyib.")
    except Exception as e:
        print(f"Kanal siyahısı göstərilərkən xəta: {e}")
        await update.message.reply_text("Kanal siyahısı alınarkən xəta baş verdi.")


async def handle_remove_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    channel_id = query.data.replace("remove_", "")

    channels = read_channels()
    if channel_id in channels:
        channels.remove(channel_id)
        write_channels(channels)
        await query.edit_message_text(f"Kanal silindi: {channel_id}")
    else:
        await query.edit_message_text("Kanal tapılmadı və ya artıq silinib.")


# --- 10. Kanal silmək ---
@admin_only
async def remove_channel(update: Update, context: CallbackContext) -> None:
    try:
        if len(context.args) != 1:
            await update.message.reply_text(
                "Zəhmət olmasa silmək istədiyiniz kanalın ID-sini daxil edin: /remove <kanal_id>"
            )
            return

        channel_id = context.args[0]

        # Fayldan oxuyuruq
        if os.path.isfile(channels_file):
            with open(channels_file, "r", encoding="utf-8") as file:
                channels = file.read().splitlines()

            if channel_id in channels:
                channels.remove(channel_id)
                with open(channels_file, "w", encoding="utf-8") as file:
                    file.write("\n".join(channels) + "\n")
                await update.message.reply_text(f"Kanal uğurla silindi: {channel_id}")
            else:
                await update.message.reply_text(f"Kanal tapılmadı: {channel_id}")
        else:
            await update.message.reply_text("Heç bir kanal əlavə edilməyib.")
    except Exception as e:
        error_message = f"Kanal silinərkən xəta baş verdi: {e}"
        print(error_message)
        await update.message.reply_text(error_message)


# --- 11. İstifadəçiləri göstərmək ---
async def show_users(update: Update, context: CallbackContext) -> None:
    # Yalnız admin istifadəçilər bu əmri icra edə bilər
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Bu əməliyyat yalnız adminlər üçün mümkündür!")
        return

    # Faylı oxumaq və məzmunu göstərmək
    if os.path.isfile(users_file):
        with open(users_file, "r", encoding="utf-8") as file:
            content = file.read()
            if content.strip():  # Fayl boş deyilsə
                await update.message.reply_text(f"İstifadəçilər:\n{content}")
            else:
                await update.message.reply_text(
                    "Fayl boşdur, heç bir istifadəçi məlumatı yoxdur."
                )
    else:
        await update.message.reply_text("users.txt faylı mövcud deyil.")



# --- 12. Fayl ---
async def send_users_file(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Bu əməliyyat yalnız adminlər üçün mümkündür!")
        return

    # Faylı yoxlayın
    import os

    print("users.txt mövcuddur:", os.path.isfile("users.txt"))
    print("users.txt ölçüsü:", os.path.getsize("users.txt"))

    if not os.path.isfile(users_file):
        await update.message.reply_text("Fayl mövcud deyil!")
        return

    if os.path.getsize(users_file) == 0:
        await update.message.reply_text("Fayl boşdur!")
        return

    try:
        await context.bot.send_document(
            chat_id=update.message.chat_id,
            document=open(users_file, "rb"),
            filename="users.json",
        )
    except Exception as e:
        await update.message.reply_text(f"Faylı göndərərkən xəta baş verdi: {e}")


# İstifadəçi mesajı font
async def send_formatted_message(update: Update, context: CallbackContext) -> None:
    # İstifadəçi mesajı
    user_message = update.message.text
    args = user_message.split(" ", 2)  # Əmri, font və mətni ayırır
    if len(args) < 3:
        await update.message.reply_text(
            "Zəhmət olmasa font, formatlanacaq və normal mətn daxil edin: /font bold 'Çox sevirəm' Azərbaycanı"
        )
        return

    font, special_text, remaining_text = args[1], args[2].strip("'"), args[2]
    font = font.lower()

    # Formatlanmış mətn
    formatted_text = convert_to_font(special_text.strip(), font)
    if formatted_text == special_text:
        await update.message.reply_text("Daxil etdiyiniz font mövcud deyil.")
    else:
        # Bütün mətnləri birləşdirib göndəririk
        full_message = f"{formatted_text}\n\n{remaining_text.strip()}"
        await update.message.reply_text(full_message)


# --- 13. Botu başlat ---
def main() -> None:
    # Faylı təmizləyirik
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", send_admin_panel))
    application.add_handler(
        CallbackQueryHandler(
            handle_admin_actions,
            pattern="^(change_|add_button|view_buttons|remove_button)$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(handle_delete_button, pattern="^delete_\\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_admin_actions, pattern="^change_(message|link|image)$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(handle_start_callback, pattern="^add_channel$")
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, unified_message_handler)
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_admin_actions,
            pattern="^(set_vertical_buttons|set_horizontal_buttons)$",
        )
    )

    application.add_handler(
        CommandHandler("istek", send_request_panel)
    )  # İstəkləri idarə et
    application.add_handler(
        CommandHandler("statistika", send_statistics)
    )  # Statistikalar
    application.add_handler(
        CommandHandler("sifirla", reset_statistics)
    )  # Statistikaları sıfırla
    application.add_handler(CommandHandler("kanallar", list_channels))  # Kanal siyahısı

    # Callback query üçün spesifik handler-lar
    application.add_handler(
        CallbackQueryHandler(handle_statistics_callback, pattern="^reset_statistics$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_remove_callback, pattern="^remove_.*$")
    )

    # ChatJoinRequest üçün handler
    application.add_handler(ChatJoinRequestHandler(handle_join_request))

    # Foto üçün handler
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_upload))



    # Bütün təsdiq və rədd əməliyyatları
    application.add_handler(
        CallbackQueryHandler(approve_all_requests, pattern="approve_all")
    )
    application.add_handler(CallbackQueryHandler(deny_all_requests, pattern="deny_all"))
    application.add_handler(CommandHandler("istifadeciler", show_users))
    application.add_handler(CommandHandler("gonder_fayl", send_users_file))
    application.add_handler(CommandHandler("font", send_formatted_message))

    print("Bot başlad...")
    application.run_polling()

if __name__ == "__main__":
    main()
