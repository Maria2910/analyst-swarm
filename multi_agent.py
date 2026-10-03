import os
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from tools import setup_tools
from logger import get_logger
from memory_store import save_session, recall_last

log = get_logger("multi_agent")

# Берём URL Ollama из переменной окружения.
# На хосте (PyCharm) её нет → localhost.
# В Docker она передаётся через docker-compose → host.docker.internal.
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

# --- Агенты ---
analyst = AssistantAgent(
    name="Analyst",
    llm_config=llm_config,
    system_message=(
        "Ты — Аналитик данных. У тебя есть инструменты:\n"
        "- read_csv, analyze_data, execute_sql, plot_chart, save_report\n\n"
        "САМОЕ ВАЖНОЕ ПРАВИЛО:\n"
        "Пока ты не вызвал save_report — задача НЕ ВЫПОЛНЕНА.\n"
        "save_report — ЭТО ФИНАЛЬНЫЙ ОБЯЗАТЕЛЬНЫЙ ШАГ.\n\n"
        "ПЛАН:\n"
        "1. read_csv('sales.csv')\n"
        "2. analyze_data('sales.csv', 'sales')\n"
        "3. execute_sql('SELECT region, SUM(sales) as total FROM sales GROUP BY region')\n"
        "4. plot_chart('sales.csv', 'region', 'sales', 'bar', 'Продажи по регионам')\n"
        "5. save_report('Анализ продаж', '# Анализ продаж\\n\\n## Статистика\\n...\\n## Сводка по регионам\\n...')\n"
        "6. Только ПОСЛЕ save_report — напиши краткое резюме и передай слово Reviewer\n\n"
        "КРИТИЧЕСКИ ВАЖНО:\n"
        "- save_report ОБЯЗАТЕЛЕН. Без него задача считается проваленной.\n"
        "- Отвечай ТОЛЬКО на русском языке.\n"
        "- НЕ пропускай шаги."
    )
)

reviewer = AssistantAgent(
    name="Reviewer",
    llm_config=llm_config,
    system_message=(
        "Ты — Рецензент. Аналитик уже выполнил работу.\n"
        "Твоя задача:\n"
        "1. Проверить инсайты Аналитика\n"
        "2. Указать на слабые места\n"
        "3. Дать оценку от 1 до 10\n\n"
        "КРИТИЧЕСКИ ВАЖНО:\n"
        "- Отвечай ТОЛЬКО на русском языке\n"
        "- НЕ вызывай tools сам\n"
        "- В конце напиши TERMINATE"
    )
)

user_proxy = UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=6,   # ← было 4, стало 6
    code_execution_config=False,
    is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or "")
)

# Регистрируем tools (calculate, get_current_time)
setup_tools(analyst, user_proxy)

# --- Групповой чат ---
groupchat = GroupChat(
    agents=[user_proxy, analyst, reviewer],
    messages=[],
    max_round=16,                   # ← было 14, стало 16
    speaker_selection_method="round_robin",
)

manager = GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_config,
)

# --- Запрос ---
USER_MESSAGE = (
    "Проанализируй данные о продажах из data/sales.csv. "
    "Найди ключевые тренды, посчитай статистику по колонке sales, "
    "построй график продаж по регионам И ОБЯЗАТЕЛЬНО сохрани "
    "итоговый отчёт в файл через save_report."
)

# --- Показываем последние записи из памяти (контекст) ---
log.info("=== Previous memory ===")
log.info(recall_last(2))

log.info("=== Starting multi-agent chat ===")

result = user_proxy.initiate_chat(
    manager,
    message=USER_MESSAGE,
)

log.info("=== Chat finished ===")

# --- Сохраняем в память ---
final_message = ""
if result and result.chat_history:
    # Ищем последнее сообщение Reviewer с оценкой
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