import logging
import os
import uuid
import re
import subprocess
import sys
import time
import requests
from flask import Flask, send_from_directory, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import yt_dlp

# =======================
# CONFIGURAZIONE LOGGING
# =======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =======================
# CONFIGURAZIONE BOT
# =======================
TELEGRAM_TOKEN = "7491754682:AAHx4h4q9eNRaMWuvezF9joAR1Qn0gDCjZE"
CHANNEL_ID = "-1002326870207"

# =======================
# CONFIGURAZIONE SERVER
# =======================
LOCAL_PORT = 5000
LANDING_DIR = "landing_pages"
NETLIFY_SITE_DIR = LANDING_DIR
os.makedirs(LANDING_DIR, exist_ok=True)

# =======================
# FLASK APP
# =======================
app = Flask(__name__)

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory(LANDING_DIR, filename)

@app.route('/impression')
def impression():
    zoneid = request.args.get("zoneid")
    if zoneid:
        with open("impressions.log", "a", encoding="utf-8") as f:
            f.write(f"{time.time()},{zoneid}\n")
        logger.info(f"✅ Impression registrata per zoneid {zoneid}")
    return "ok"

# =======================
# ESCAPE MARKDOWN
# =======================
def escape_markdown(text: str) -> str:
    return re.sub(r"([_*\[\]()~`>#+-=|{}.!])", r"\\\1", text)

# =======================
# RECUPERO INFO VIDEO
# =======================
class VideoUtils:
    @staticmethod
    def get_video_info(url: str):
        try:
            ydl_opts = {"quiet": True, "extract_flat": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    return {
                        "thumbnail": info.get("thumbnail"),
                        "title": info.get("title", "Video senza titolo")
                    }
                return None
        except Exception as e:
            logger.error(f"Errore yt-dlp: {e}")
            return None

# =======================
# CREAZIONE LANDING PAGE
# =======================
def create_landing_page(video_url: str) -> str:
    file_id = str(uuid.uuid4().int)[:5]
    file_name = f"landing_{file_id}.html"
    file_path = os.path.join(LANDING_DIR, file_name)

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Video Landing Page</title>
<style>
body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f2f2f2; }}
h1 {{ color: #333; }}
.video-button {{ display: inline-block; padding: 15px 25px; margin: 20px 0; font-size: 18px; color: #fff; background-color: #007bff; border: none; border-radius: 5px; text-decoration: none; cursor: pointer; }}
.ad-container {{ margin-top: 30px; }}
</style>
</head>
<body>
<h1>🎥 Il tuo video è pronto!</h1>
<p>Clicca sul pulsante qui sotto per guardare il video.</p>
<a href="{video_url}" class="video-button" target="_blank">Guarda il video</a>
<div class="ad-container">
<script async type="application/javascript" src="https://a.pemsrv.com/ad-provider.js"></script>
<ins class="eas6a97888e33" data-zoneid="5719964"></ins>
<script>(AdProvider = window.AdProvider || []).push({{"serve": {{}}}});</script>

<script type="application/javascript">
document.addEventListener('creativeDisplayed-5719964', function() {{
    console.log("✅ Impression registrata per zoneid 5719964");
    fetch("/impression?zoneid=5719964").catch(console.error);
}}, false);
</script>
</div>
</body>
</html>
"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return file_name

# =======================
# DEPLOY NETLIFY
# =======================
def deploy_netlify(message="Aggiornamento landing page"):
    try:
        subprocess.run(
            ["netlify.cmd", "deploy", "--dir", NETLIFY_SITE_DIR, "--prod", "--message", message],
            check=True
        )
        logger.info("✅ Deploy Netlify completato!")
    except Exception as e:
        logger.error(f"Errore deploy Netlify: {e}")

# =======================
# AVVIO NGROK
# =======================
def start_ngrok():
    # opzionale se vuoi testare con ngrok, altrimenti commenta
    return None

# =======================
# COMANDI BOT
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Benvenuto! Invia /link seguito dall'URL del video per creare una landing page con pubblicità."
    )

async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /link <video_url>")
        return

    video_url = context.args[0]
    logger.info(f"Ricevuto URL: {video_url}")

    video_info = VideoUtils.get_video_info(video_url)
    if not video_info:
        await update.message.reply_text("❌ Impossibile ottenere informazioni sul video")
        return

    file_name = create_landing_page(video_url)
    logger.info(f"Landing page creata: {file_name}")

    # Deploy automatico su Netlify
    deploy_netlify(f"Landing page {file_name}")

    landing_url = f"https://YOUR_NETLIFY_SITE_NAME.netlify.app/{file_name}"  # Inserisci il tuo sito Netlify
    title_safe = escape_markdown(video_info["title"])
    caption = f"🎥 {title_safe}"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Guarda il video", url=landing_url)]])
    bot = context.bot

    try:
        if video_info.get("thumbnail"):
            await bot.send_photo(chat_id=CHANNEL_ID, photo=video_info["thumbnail"],
                                 caption=caption, reply_markup=keyboard, parse_mode="MarkdownV2")
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text=caption,
                                   reply_markup=keyboard, parse_mode="MarkdownV2")
        await update.message.reply_text(f"✅ Landing page generata!\n\n{landing_url}", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Errore invio Telegram: {e}")
        await update.message.reply_text("❌ Errore invio al canale")

# =======================
# AVVIO BOT E FLASK
# =======================
def main():
    # Avvia Flask in background
    subprocess.Popen([sys.executable, __file__, "flask"], shell=True)

    # Avvia bot Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("link", handle_video_link))
    logger.info("🤖 Bot in esecuzione...")
    application.run_polling()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "flask":
        app.run(port=LOCAL_PORT, host="0.0.0.0")
    else:
        main()
