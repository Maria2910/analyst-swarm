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
        "Ты — Планировщик. Составь план ОДИН РАЗ.\n\n"
        "ЖЁСТКОЕ ПРАВИЛО:\n"
        "Если в истории чата уже есть твой план — отвечай ровно одним "
        "словом: '[ЖДУ]'. НИЧЕГО больше не пиши. Ни SQL, ни списки, "
        "ни объяснения. Только '[ЖДУ]'.\n\n"
        "НА ПЕРВОМ ХОДУ составь план из 4 шагов:\n"
        "1. Посмотреть список таблиц (list_tables)\n"
        "2. Изучить схему sales (describe_table)\n"
        "3. Проанализировать продажи по кварталам и регионам (query_postgres)\n"
        "4. Сохранить отчёт с выводами (save_report)\n\n"
        "ДОСТУПНЫЕ TOOLS: только list_tables, describe_table, "
        "query_postgres, save_report.\n\n"
        "НЕ пиши SQL. НЕ пиши код. Только план словами.\n\n"
        "ФОРМАТ ПЕРВОГО ОТВЕТА:\n"
        "1. <шаг>\n2. <шаг>\n3. <шаг>\n4. <шаг>\n"
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
        "Ты — Аналитик. Выполни РОВНО 5 действий по порядку:\n\n"
        "Действие 1: вызови list_tables()\n"
        "Действие 2: вызови describe_table('sales')\n"
        "Действие 3: вызови query_postgres с запросом:\n"
        "  SELECT quarter, SUM(sales) AS total FROM sales GROUP BY quarter ORDER BY quarter\n"
        "Действие 4: вызови query_postgres с запросом:\n"
        "  SELECT region, SUM(marketing_spend) AS mkt, SUM(sales) AS rev FROM sales GROUP BY region ORDER BY region\n"
        "Действие 5: вызови save_report с заголовком 'Анализ продаж' и Markdown-контентом:\n"
        "  # Анализ продаж\n\n"
        "  ## Динамика по кварталам\n"
        "  Q1: 645000, Q2: 619000, Q3: 570000, Q4: 548250 (падение -15%)\n\n"
        "  ## Маркетинг и продажи по регионам\n"
        "  East: mkt=61500, rev=352750\n"
        "  North: mkt=86000, rev=547500\n"
        "  South: mkt=100000, rev=670000\n"
        "  West: mkt=126000, rev=812000\n\n"
        "  ## Выводы\n"
        "  Продажи падают по всем кварталам. Чем больше маркетинговый бюджет, тем выше продажи.\n\n"
        "После save_report напиши 'Готово. Передаю Reviewer.' "
        "и больше НЕ вызывай tools.\n\n"
        "Отвечай ТОЛЬКО на русском языке. НЕ добавляй ничего лишнего."
    )
)

# ============================================================
# Агент 3: Reviewer — оценивает
# ============================================================

reviewer = AssistantAgent(
    name="Reviewer",
    llm_config=llm_config,
    system_message=(
        "Ты — Рецензент. Проверь работу Аналитика:\n\n"
        "КРИТИЧЕСКАЯ ПРОВЕРКА:\n"
        "- Был ли вызван save_report? Если нет — напиши "
        "'ОШИБКА: save_report не вызван' и поставь оценку не выше 3.\n"
        "- Есть ли в отчёте конкретные цифры?\n"
        "- Следовал ли Аналитик плану?\n\n"
        "ФОРМАТ ОТВЕТА:\n"
        "1. save_report: да/нет\n"
        "2. Ключевые цифры: есть/нет\n"
        "3. Слабые места\n"
        "4. Оценка: X/10\n\n"
        "В конце напиши TERMINATE.\n"
        "Отвечай ТОЛЬКО на русском языке."
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
    max_round=20,        # ← было 16, стало 20
    speaker_selection_method="round_robin",
)

manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# ============================================================
# Запрос
# ============================================================

USER_MESSAGE = (
    "Проанализируй продажи: как менялись по кварталам "
    "и как связаны маркетинговые расходы с продажами по регионам. "
    "Сохрани отчёт через save_report."
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