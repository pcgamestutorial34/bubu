import subprocess
import logging
import os

logger = logging.getLogger(__name__)

GIT_REPO_DIR = os.path.abspath(".")
GIT_BRANCH = "main"
GIT_USERNAME = os.environ.get("GIT_USERNAME")
GIT_TOKEN = os.environ.get("GIT_TOKEN")
LANDING_DIR = "landing_pages"

def git_push():
    try:
        # Salva tutte le modifiche locali in stash
        subprocess.run(["git", "stash", "push", "-m", "bot_local_changes"], check=True, cwd=GIT_REPO_DIR)
        logger.info("💾 Modifiche locali salvate nello stash")

        # Aggiungi e committa solo la cartella landing_pages
        subprocess.run(["git", "add", LANDING_DIR], check=True, cwd=GIT_REPO_DIR)
        subprocess.run(["git", "commit", "-m", "Aggiornati file landing_pages"], check=True, cwd=GIT_REPO_DIR)
    except subprocess.CalledProcessError:
        logger.info("⚠ Nessun nuovo file da commitare")

    try:
        # Push diretto su GitHub
        remote_url = f"https://{GIT_USERNAME}:{GIT_TOKEN}@github.com/{GIT_USERNAME}/bubu.git"
        subprocess.run(["git", "push", remote_url, GIT_BRANCH], check=True, cwd=GIT_REPO_DIR)
        logger.info("✅ Tutti i file landing_pages pushati correttamente su GitHub")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Errore durante il push: {e}")

    try:
        # Ripristina le modifiche locali dallo stash
        subprocess.run(["git", "stash", "pop"], check=True, cwd=GIT_REPO_DIR)
        logger.info("♻ Modifiche locali ripristinate dallo stash")
    except subprocess.CalledProcessError:
        logger.warning("⚠ Nessuno stash da ripristinare")
