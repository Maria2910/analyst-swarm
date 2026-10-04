import os
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from tools import setup_tools
from logger import get_logger
from memory_store import save_session, recall_last

log = get_logger("multi_agent")

OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")

llm_config = {
    "config_list": [{
        "model": "qwen2.5:7b",
        "base_url": OLLAMA_URL,
        "api_key": "ollama",
        "api_type": "openai",
        "price": [0, 0],
    }],
    "cache_seed": None,
    "temperature": 0.2,
    "top_p": 0.9,
}

# ============================================================
# Агент 1: Planner — планирует, но не выполняет
# ============================================================

planner = AssistantAgent(
    name="Planner",
    llm_config=llm_config,
    system_message=(
        "Ты — Планировщик. Разбей запрос пользователя на 3-4 шага.\n\n"
        "ДОСТУПНЫЕ ИНСТРУМЕНТЫ (планируй только их):\n"
        "- list_tables — список таблиц в БД\n"
        "- describe_table — схема таблицы\n"
        "- query_postgres — SQL-запрос к БД\n"
        "- save_report — сохранение Markdown-отчёта\n\n"
        "ВАЖНО:\n"
        "- Для работы с PostgreSQL используй только эти 4 инструмента\n"
        "- НЕ включай в план plot_chart, read_csv, analyze_data — "
        "они работают только с CSV-файлами, а не с БД\n"
        "- НЕ включай connect_postgres — такого инструмента нет\n\n"
        "ПРАВИЛО ПОВТОРНОГО ХОДА:\n"
        "Если в истории чата уже есть твой план — напиши только '[ЖДУ]' "
        "и больше ничего.\n\n"
        "ФОРМАТ ПЕРВОГО ОТВЕТА:\n"
        "1. <действие>\n2. <действие>\n3. <действие>\n"
        "План готов. Передаю Аналитику.\n\n"
        "Отвечай ТОЛЬКО на русском языке."
    )
)

# ============================================================
# Агент 2: Analyst — выполняет план
# ============================================================

analyst = AssistantAgent(
    name="Analyst",
    llm_config=llm_config,
    system_message=(
        "Ты — Аналитик данных. Выполняй план от Планировщика.\n\n"
        "Доступные инструменты:\n"
        "- list_tables, describe_table, query_postgres\n"
        "- read_csv, analyze_data, execute_sql\n"
        "- plot_chart, save_report, calculate\n\n"
        "КРИТИЧЕСКИ ВАЖНО:\n"
        "- Отвечай ТОЛЬКО на русском языке\n"
        "- Следуй плану шаг за шагом\n"
        "- Вызывай tools, не выдумывай данные\n\n"
        "ПРАВИЛА ОБРАБОТКИ ОШИБОК:\n"
        "- Если tool вернул ошибку 'Файл не найден' — НЕ повторяй тот же вызов. "
        "Переходи к следующему шагу плана или заверши работу.\n"
        "- Если после 2 неудачных попыток не получается — "
        "просто переходи к save_report с тем, что есть.\n"
        "- НЕ зацикливайся на одном tool.\n\n"
        "- save_report ОБЯЗАТЕЛЕН. После него передай слово Reviewer."
        "ПОСЛЕ save_report:\n"
        "- Напиши 'Отчёт сохранён. Передаю Reviewer.'\n"
        "- БОЛЬШЕ НЕ ВЫЗЫВАЙ tools"
    )
)

# ============================================================
# Агент 3: Reviewer — оценивает
# ============================================================

reviewer = AssistantAgent(
    name="Reviewer",
    llm_config=llm_config,
    system_message=(
        "Ты — Рецензент. Проверь работу Аналитика:\n"
        "1. Следовал ли он плану Планировщика?\n"
        "2. Все ли шаги выполнены?\n"
        "3. Есть ли слабые места?\n"
        "4. Оценка от 1 до 10.\n\n"
        "КРИТИЧЕСКИ ВАЖНО:\n"
        "- Отвечай ТОЛЬКО на русском языке\n"
        "- НЕ вызывай tools сам\n"
        "- В конце финального ответа напиши TERMINATE"
    )
)

# ============================================================
# Пользователь-прокси
# ============================================================

user_proxy = UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=8,
    code_execution_config=False,
    is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or "")
)

setup_tools(analyst, user_proxy)

# ============================================================
# Групповой чат с 3 агентами
# ============================================================

groupchat = GroupChat(
    agents=[user_proxy, planner, analyst, reviewer],
    messages=[],
    max_round=18,        # ← было 14, стало 18
    speaker_selection_method="round_robin",
)

manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# ============================================================
# Запрос
# ============================================================

USER_MESSAGE = (
    "Подключись к базе данных analytics в PostgreSQL, "
    "посмотри какие таблицы есть, найди топ регионов по продажам, "
    "и сохрани итоговый отчёт через save_report."
)

log.info("=== Previous memory ===")
log.info(recall_last(2))

log.info("=== Starting multi-agent chat (3 agents) ===")

result = user_proxy.initiate_chat(manager, message=USER_MESSAGE)

log.info("=== Chat finished ===")

# Сохраняем в память
final_message = ""
if result and result.chat_history:
    for msg in reversed(result.chat_history):
        content = msg.get("content") or ""
        if "TERMINATE" in content:
            final_message = content
            break
    if not final_message:
        final_message = result.chat_history[-1].get("content", "")

save_session(
    user_message=USER_MESSAGE,
    final_answer=final_message,
)

print("\n📝 Сессия сохранена в memory/journal.md")
print("📄 Лог записан в папку logs/")