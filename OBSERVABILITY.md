# Observability — Наблюдаемость системы

## Что мы мониторим

### 1. Метрики производительности
- **Latency per tool call:** сколько миллисекунд занимает каждый tool
- **LLM response time:** время генерации ответа Qwen 2.5 7B
- **Tokens per second:** пропускная способность модели
- **Round count:** сколько раундов понадобилось для задачи
- **Tool usage count:** сколько раз вызван каждый tool

### 2. Метрики качества
- **Pass rate:** доля успешно завершённых задач (из evals)
- **Language consistency:** нет ли language drift (китайский/английский)
- **Terminate correctness:** корректно ли агент завершает диалог
- **Response length:** не слишком коротко и не слишком длинно
- **Memory recall hit:** используются ли записи из памяти

### 3. Системные метрики
- **CPU / RAM контейнера** (через `docker stats`)
- **Disk I/O** при записи в `reports/`, `memory/`, `logs/`
- **Restart count:** не падает ли контейнер

### 4. Бизнес-метрики
- **Reports generated:** сколько отчётов создано агентом
- **Charts generated:** сколько графиков построено
- **Unique sessions:** сколько сессий в журнале памяти

---

## Что у нас есть сейчас (реализовано)

### Логи (Logs)

**Где:** папка `logs/`, файлы `agent_YYYYMMDD_HHMMSS.log`

**Что пишется:**
```
2026-10-03 13:39:21,618 [INFO] HTTP Request: POST http://ollama:11434/v1/chat/completions "HTTP/1.1 200 OK"
2026-10-03 13:39:33,866 [INFO] Test case sales_drop: PASS (137.2s)
```

**Формат:** `timestamp [LEVEL] message`

**Уровни:** INFO, WARNING, ERROR

**Реализация:** `logger.py` — центральный модуль, `logging.FileHandler` + `StreamHandler`.

**Ротация:** каждая сессия — новый файл, старые сохраняются. Автоматической ротации нет, но при необходимости легко добавить `RotatingFileHandler`.

### Трейсы (Traces)

**Что считается трейсом:** один полный прогон `initiate_chat` от первого сообщения пользователя до `TERMINATE`.

**Как отслеживается:**
- **Start trace:** `[INFO] === Starting multi-agent chat ===`
- **Per-step traces:** каждый `HTTP Request: POST http://ollama:...` — это шаг LLM
- **Tool traces:** `>>>>>>>> EXECUTING FUNCTION <name>...` и `>>>>>>>> EXECUTED FUNCTION <name>...`
- **End trace:** `[INFO] === Chat finished ===`

**Идентификатор трейса:** `run_id` AutoGen (UUID) в сообщениях `TERMINATING RUN (uuid)`. По нему можно связать все события одного прогона.

### Метрики (Metrics)

**Реализовано в `eval.py`:**
- `pass_rate` — доля успешных тестов
- `avg_response_time_sec` — среднее время ответа
- `avg_response_length` — средняя длина ответа
- `language_consistency` — есть ли китайский
- `tool_usage_rate` — доля задач с tools

Результаты сохраняются в `logs/eval_YYYYMMDD_HHMMSS.json`.

**Пример:**
```json
{
  "timestamp": "2026-10-03T11:29:24.088666",
  "total_tests": 3,
  "passed": 3,
  "pass_rate": 1.0,
  "avg_response_time_sec": 134.69,
  "avg_response_length": 1217,
  "results": [...]
}
```

### Артефакты (Artifacts)

**Что создаёт агент:**
- `reports/chart_*.png` — графики matplotlib
- `reports/report_*.md` — Markdown-отчёты
- `memory/journal.md` — сессии с запросами и ответами

---

## Специфика мониторинга для агентских систем

В отличие от обычных приложений, у LLM-агентов нужно мониторить:

| Обычное приложение | Агентская система |
|---------------------|-------------------|
| HTTP-коды | Правильность tool calls |
| Latency запросов | Токены на запрос + стоимость |
| Ошибки | Галлюцинации и language drift |
| CPU/RAM | Context length usage |
| — | Разнообразие ответов (не зациклился ли) |
| — | Соотношение tool calls / reasoning |

**Наши метрики покрывают:**
- ✅ Tool calls (логи `EXECUTING FUNCTION`)
- ✅ Токены (можно извлечь из ответов Ollama)
- ✅ Language drift (check в `eval.py`)
- ✅ Context length (косвенно — по `max_round`)
- ✅ Зацикливание (по `max_consecutive_auto_reply`)

---

## Что можно улучшить (план развития)

### 1. LLM-native observability

**Langfuse / LangSmith / Langtrace** — специализированные платформы для LLM-приложений:

- Автоматический трейсинг цепочек prompts → LLM → tools → LLM
- Учёт токенов и стоимости (для локальных моделей — условный)
- A/B-тестирование промптов
- Оценка ответов через LLM-as-judge

**Почему не используем сейчас:** требует внешнего сервиса или облачного аккаунта. Для учебного проекта достаточно локальных логов.

**Как добавить:**
```python
from langfuse import Langfuse
langfuse = Langfuse(public_key=..., secret_key=...)
trace = langfuse.trace(name="agent_run")
trace.generation(name="llm_call", model="qwen2.5:7b", input=prompt, output=response)
```

### 2. Стандартный стек (не LLM-native)

**OpenTelemetry + Prometheus + Grafana + Loki:**

| Компонент | Роль |
|-----------|------|
| **OpenTelemetry** | Сбор трейсов и метрик (стандарт) |
| **Prometheus** | Time-series БД для метрик |
| **Grafana** | Дашборды и алертинг |
| **Loki** | Хранилище логов |
| **Alertmanager** | Уведомления при срабатывании правил |

**Плюсы:** стандарт индустрии, много готовых дашбордов.
**Минусы:** избыточно для одного агента, требует дополнительных контейнеров.

**Как добавить:**
1. Добавить в `docker-compose.yml` сервисы `prometheus`, `grafana`, `loki`
2. Экспортировать метрики из `agent` через `prometheus_client`
3. Настроить дашборды в Grafana

### 3. Алертинг

**Что алертить:**
- Pass rate < 80% (деградация качества)
- Language drift detected (появление китайского)
- Tool execution error rate > 5%
- LLM response time > 5 минут
- Контейнер перезапустился

**Как:** Alertmanager → Slack/Telegram/Email.

### 4. Distributed tracing

Для мультиагентных систем с 5+ агентами — **Jaeger** или **Tempo**. Позволяет видеть граф вызовов между агентами.

---

## Реализованная архитектура observability

```
┌────────────────────────────────────────────────┐
│              Container: agent                  │
│                                                │
│  ┌──────────────┐    ┌─────────────────────┐  │
│  │   logger.py  │───▶│ logs/agent_*.log    │  │
│  └──────────────┘    └─────────────────────┘  │
│                                                │
│  ┌──────────────┐    ┌─────────────────────┐  │
│  │   eval.py    │───▶│ logs/eval_*.json    │  │
│  └──────────────┘    └─────────────────────┘  │
│                                                │
│  ┌──────────────┐    ┌─────────────────────┐  │
│  │  artifacts   │───▶│ reports/*.png/*.md  │  │
│  └──────────────┘    └─────────────────────┘  │
│                                                │
│  ┌──────────────┐    ┌─────────────────────┐  │
│  │  memory      │───▶│ memory/journal.md   │  │
│  └──────────────┘    └─────────────────────┘  │
└────────────────────────────────────────────────┘
                       │
                       ▼ bind mounts
┌────────────────────────────────────────────────┐
│           Хост-файловая система                │
│  (можно читать через PyCharm / PowerShell)     │
└────────────────────────────────────────────────┘
```

## Итог

**Реализовано сейчас:**
- ✅ Логи в файл
- ✅ Метрики в JSON (через evals)
- ✅ Артефакты (графики, отчёты)
- ✅ Персистентная память

**Возможные улучшения:**
- ⬜ Langfuse для LLM-трейсинга
- ⬜ Prometheus + Grafana для метрик
- ⬜ Alertmanager для алертинга
- ⬜ Jaeger для distributed tracing

Для учебного проекта текущий уровень observability **достаточен** и **обоснован**: используются лёгкие решения без внешних зависимостей, все данные доступны на хосте через bind mounts.