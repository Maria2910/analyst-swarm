"""
Evals для мультиагентной системы Analyst Swarm.

Прогоняет набор тестовых задач через агентов и считает метрики:
- pass_rate: доля задач, где ответ прошёл проверку
- avg_response_time: среднее время ответа (сек)
- avg_response_length: средняя длина ответа (символов)
- language_consistency: доля ответов на русском
- tool_usage_rate: доля задач, где использованы tools
"""

import json
import os
import re
import time
from datetime import datetime

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

from tools import setup_tools
from logger import get_logger

log = get_logger("eval")


# ---------- Конфигурация ----------
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


# ---------- Тестовые задачи ----------
TEST_CASES = [
    {
        "id": "sales_drop",
        "question": (
            "Проанализируй ситуацию: продажи компании упали на 15% за квартал. "
            "Что могло случиться? Предложи гипотезы."
        ),
        "expected_keywords": ["продаж", "гипотез", "конкурент", "спрос"],
        "forbidden_keywords": ["再见", "谢谢"],  # китайские маркеры
        "min_length": 200,
    },
    {
        "id": "marketing_growth",
        "question": (
            "Как увеличить узнаваемость бренда среди молодой аудитории? "
            "Предложи стратегии."
        ),
        "expected_keywords": ["бренд", "аудитор", "маркетинг"],
        "forbidden_keywords": ["再见", "谢谢"],
        "min_length": 150,
    },
    {
        "id": "customer_churn",
        "question": (
            "Клиенты стали чаще уходить к конкурентам. "
            "Предложи гипотезы причин и способы удержания."
        ),
        "expected_keywords": ["клиент", "удержан", "конкурент"],
        "forbidden_keywords": ["再见", "谢谢"],
        "min_length": 150,
    },
]


# ---------- Создание агентов ----------
def build_agents():
    analyst = AssistantAgent(
        name="Analyst",
        llm_config=llm_config,
        system_message=(
            "Ты — Аналитик. Твоя задача:\n"
            "1. Разобрать вопрос пользователя\n"
            "2. Предложить 2-3 гипотезы или подхода\n"
            "3. Кратко обосновать каждую\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Отвечай ТОЛЬКО на русском языке\n"
            "- НИКОГДА не используй китайский или английский\n"
            "- Не заканчивай диалог — передай слово Reviewer"
        )
    )

    reviewer = AssistantAgent(
        name="Reviewer",
        llm_config=llm_config,
        system_message=(
            "Ты — Рецензент. Твоя задача:\n"
            "1. Проверить выводы Аналитика\n"
            "2. Указать на слабые места\n"
            "3. Дать оценку от 1 до 10\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Отвечай ТОЛЬКО на русском языке\n"
            "- В конце финального ответа напиши TERMINATE"
        )
    )

    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=4,
        code_execution_config=False,
        is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or "")
    )

    setup_tools(analyst, user_proxy)

    groupchat = GroupChat(
        agents=[user_proxy, analyst, reviewer],
        messages=[],
        max_round=4,
        speaker_selection_method="round_robin",
    )

    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    return user_proxy, manager


# ---------- Проверки ----------
def check_language(text: str) -> bool:
    """True, если нет китайских иероглифов."""
    chinese = re.compile(r"[\u4e00-\u9fff]")
    return not bool(chinese.search(text))


def check_keywords(text: str, keywords: list) -> bool:
    """True, если хотя бы один ключ найден."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def check_forbidden(text: str, forbidden: list) -> bool:
    """True, если запрещённых слов нет."""
    return not any(fb in text for fb in forbidden)


def evaluate_response(case: dict, response: str) -> dict:
    """Проверяет один ответ по всем правилам."""
    return {
        "language_ok": check_language(response),
        "keywords_ok": check_keywords(response, case["expected_keywords"]),
        "forbidden_ok": check_forbidden(response, case["forbidden_keywords"]),
        "length_ok": len(response) >= case["min_length"],
        "terminate_ok": "TERMINATE" in response,
    }


# ---------- Основной прогон ----------
def run_eval():
    log.info("=== EVAL START ===")
    results = []

    for case in TEST_CASES:
        log.info(f"--- Test case: {case['id']} ---")
        user_proxy, manager = build_agents()

        start = time.time()
        try:
            result = user_proxy.initiate_chat(manager, message=case["question"])
            elapsed = time.time() - start

            # Берём последнее сообщение от Reviewer
            final_text = ""
            for msg in reversed(result.chat_history):
                content = msg.get("content") or ""
                if "TERMINATE" in content:
                    final_text = content
                    break
            if not final_text and result.chat_history:
                final_text = result.chat_history[-1].get("content", "")

            checks = evaluate_response(case, final_text)
            passed = all(checks.values())

            results.append({
                "id": case["id"],
                "passed": passed,
                "elapsed_sec": round(elapsed, 2),
                "response_length": len(final_text),
                "checks": checks,
                "response_preview": final_text[:200],
            })

            log.info(f"Test {case['id']}: {'PASS' if passed else 'FAIL'} ({elapsed:.1f}s)")

        except Exception as e:
            log.error(f"Test {case['id']} crashed: {e}")
            results.append({
                "id": case["id"],
                "passed": False,
                "error": str(e),
            })

    # ---------- Считаем метрики ----------
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    times = [r["elapsed_sec"] for r in results if "elapsed_sec" in r]
    lengths = [r["response_length"] for r in results if "response_length" in r]

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3) if total else 0,
        "avg_response_time_sec": round(sum(times) / len(times), 2) if times else 0,
        "avg_response_length": round(sum(lengths) / len(lengths)) if lengths else 0,
        "results": results,
    }

    # ---------- Сохраняем ----------
    os.makedirs("logs", exist_ok=True)
    out_file = f"logs/eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    log.info(f"=== EVAL DONE ===")
    log.info(f"Pass rate: {metrics['pass_rate']}")
    log.info(f"Avg time: {metrics['avg_response_time_sec']}s")
    log.info(f"Saved to: {out_file}")

    print("\n=== EVAL SUMMARY ===")
    print(f"Pass rate: {metrics['pass_rate'] * 100:.0f}% ({passed}/{total})")
    print(f"Avg response time: {metrics['avg_response_time_sec']}s")
    print(f"Avg response length: {metrics['avg_response_length']} chars")
    print(f"Report saved: {out_file}")


if __name__ == "__main__":
    run_eval()