from autogen import AssistantAgent, UserProxyAgent
from tools import setup_tools

llm_config = {
    "config_list": [{
        "model": "qwen2.5:7b",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "api_type": "openai",
        "price": [0, 0],
    }],
    "cache_seed": None,
}

# Ассистент с инструкцией использовать инструменты
assistant = AssistantAgent(
    name="assistant",
    llm_config=llm_config,
    system_message=(
        "Ты — полезный ассистент. У тебя есть инструменты. "
        "Когда пользователь спрашивает время или просит посчитать — "
        "вызывай соответствующий инструмент. "
        "Когда задача выполнена — заверши ответ словом TERMINATE."
    )
)

# Пользователь-прокси: теперь исполняет tools
user_proxy = UserProxyAgent(
    name="user",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=5,
    code_execution_config=False,
    is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or "")
)

setup_tools(assistant, user_proxy)

user_proxy.initiate_chat(
    assistant,
    message="Посчитай 123 * 456 и скажи, сколько сейчас времени."
)