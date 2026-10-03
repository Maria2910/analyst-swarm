import os
from datetime import datetime

MEMORY_FILE = "memory/journal.md"

def ensure_memory():
    os.makedirs("memory", exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            f.write("# Agent Memory Journal\n\n")
            f.write("Долгосрочная память агентов. Каждая запись — отдельный сеанс.\n\n")

def save_session(user_message: str, final_answer: str, score: str = ""):
    """Сохраняет сессию в Markdown-журнал."""
    ensure_memory()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"## Сессия {timestamp}\n\n")
        f.write(f"**Запрос:** {user_message}\n\n")
        f.write(f"**Ответ:** {final_answer}\n\n")
        if score:
            f.write(f"**Оценка:** {score}\n\n")
        f.write("---\n\n")

def recall_last(n: int = 3) -> str:
    """Читает последние n записей из журнала."""
    if not os.path.exists(MEMORY_FILE):
        return "Память пуста."
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    sessions = content.split("## Сессия")
    if len(sessions) <= 1:
        return "Память пуста."
    recent = sessions[-n:] if len(sessions) > n else sessions[1:]
    return "## Сессия" + "\n## Сессия".join(s.strip() for s in recent).strip()