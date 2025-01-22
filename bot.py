from dotenv import load_dotenv
import os
from telegram import Update, ChatPermissions, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters
from telegram import Bot
import logging
from functools import wraps

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Variabel global untuk menyimpan status bot
status_bot = "Running"  # Status awal adalah Running

# Fungsi untuk memeriksa apakah pengguna adalah admin
async def is_admin(update: Update) -> bool:
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    admins = await update.message.chat.get_administrators()
    return any(admin.user.id == user_id for admin in admins)

# Dekorator untuk memeriksa apakah pengguna adalah admin
def admin_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not await is_admin(update):
            await update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Fungsi untuk menyambut anggota baru
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_image_url = "https://i.pinimg.com/236x/1f/c8/24/1fc8244a27f7665e2d694a44665a4d83.jpg"
    welcome_text = "Selamat datang di grup, {}! 😊 Jangan lupa baca aturan grup dan jadikan tempat ini menyenangkan untuk semua!"
    
    for member in update.message.new_chat_members:
        await update.message.reply_photo(welcome_image_url, caption=welcome_text.format(member.first_name))

# Fungsi untuk menampilkan menu dengan ReplyKeyboard
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Daftar tombol untuk menu
    keyboard = [
        ["Start", "Help"],
        ["Rules", "Warn"],
        ["Mute", "Kick"]
    ]
    
    # Membuat reply keyboard
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    # Mengirimkan menu dengan tombol
    await update.message.reply_text(
        "Pilih salah satu menu:",
        reply_markup=reply_markup
    )

# Fungsi untuk menanggapi tombol yang ditekan
async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Start":
        await update.message.reply_text("Bot telah dimulai!")
    elif text == "Help":
        await update.message.reply_text("Ini adalah daftar perintah yang tersedia:\n/start - Memulai bot\n/help - Melihat bantuan")
    elif text == "Rules":
        await update.message.reply_text("Aturan grup:\n1. Hormati sesama anggota.\n2. Jangan spam.\n3. Ikuti arahan admin.")
    elif text == "Warn":
        await update.message.reply_text("Gunakan perintah /warn untuk memberi peringatan.")
    elif text == "Mute":
        await update.message.reply_text("Gunakan perintah /mute untuk membisukan anggota.")
    elif text == "Kick":
        await update.message.reply_text("Gunakan perintah /kick untuk mengeluarkan anggota.")

# Fungsi untuk menangani perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Saya adalah bot pengelola grup Anda. Ketik /help untuk melihat daftar perintah.")

# Fungsi untuk menangani perintah /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Daftar Perintah:\n/start - Memulai bot\n/help - Melihat bantuan\n/rules - Menampilkan aturan grup\n/report - Melaporkan masalah ke admin\n/warn - Memberikan peringatan ke anggota\n/mute - Membisukan anggota\n/kick - Mengeluarkan anggota")

# Fungsi untuk menampilkan aturan grup
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Aturan Grup:\n1. Hormati sesama anggota.\n2. Jangan spam.\n3. Ikuti arahan admin.")

# Fungsi untuk memberikan peringatan
@admin_required
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Harap balas pesan anggota yang ingin diberi peringatan.")
        return

    warned_user = update.message.reply_to_message.from_user
    await update.message.reply_text(f"{warned_user.first_name} telah diberi peringatan.")

# Fungsi untuk membisukan anggota
@admin_required
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Harap balas pesan anggota yang ingin dibisukan.")
        return

    muted_user = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        update.message.chat_id,
        muted_user.id,
        permissions=ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text(f"{muted_user.first_name} telah dibisukan.")

# Fungsi untuk mengeluarkan anggota
@admin_required
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Harap balas pesan anggota yang ingin dikeluarkan.")
        return

    kicked_user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.message.chat_id, kicked_user.id)
    await update.message.reply_text(f"{kicked_user.first_name} telah dikeluarkan dari grup.")

# Fungsi untuk menangani laporan
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report_message = "Seorang anggota melaporkan masalah di grup."
    await update.message.reply_text("Laporan Anda telah dikirim ke admin.")

# Fungsi untuk menangani perintah yang tidak dikenal
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Perintah yang Anda masukkan tidak dikenal. Ketik /help untuk daftar perintah yang tersedia.")

# Fungsi utama untuk menjalankan bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("kick", kick))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("menu", menu))  # Menambahkan perintah /menu
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))  # Menangani respons tombol

    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    application.run_polling()

if __name__ == "__main__":
    main()
