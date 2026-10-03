# Архитектура Analyst Swarm

## C4 — Context Diagram (уровень 1)

Показывает систему в контексте пользователя и внешних сущностей.

```mermaid
graph TB
    User[👤 Пользователь<br/>Задаёт вопросы на естественном языке]
    System[🤖 Analyst Swarm<br/>Мультиагентная система<br/>анализа данных]
    Data[(📁 CSV-данные<br/>data/sales.csv)]
    Reports[(📊 Артефакты<br/>reports/*.png, *.md)]

    User -->|Вопрос| System
    System -->|Читает| Data
    System -->|Создаёт| Reports
    System -->|Ответ| User

    style System fill:#4A90E2,color:#fff
    style User fill:#F5A623,color:#fff
    style Data fill:#7ED321,color:#fff
    style Reports fill:#7ED321,color:#fff
```

## C4 — Container Diagram (уровень 2)

Показывает контейнеры (Docker), из которых состоит система.

```mermaid
graph TB
    subgraph Host["Windows Host (WSL2)"]
        User[👤 Пользователь]
        CLI[💻 PowerShell / PyCharm]
    end

    subgraph Docker["Docker Engine"]
        subgraph Net["Docker Network: agent-net"]
            Agent["🐍 Container: agent<br/>Python 3.11<br/>AG2 + AutoGen<br/>Non-root appuser"]
            Ollama["🦙 Container: ollama<br/>Ollama Server<br/>port 11434"]
        end

        Vol["💾 Volume: ollama-data<br/>Модель Qwen 2.5 7B (4.7 GB)"]
    end

    subgraph FS["Хост-файловая система (Bind Mounts)"]
        Data["📁 data/ (ro)"]
        Memory["📁 memory/ (rw)"]
        Reports["📁 reports/ (rw)"]
        Logs["📁 logs/ (rw)"]
    end

    User -->|docker compose up| CLI
    CLI --> Agent
    Agent -->|HTTP POST /v1/chat/completions| Ollama
    Ollama -->|читает модель| Vol
    Agent -->|read_csv| Data
    Agent -->|save_session| Memory
    Agent -->|save_report, plot_chart| Reports
    Agent -->|logging| Logs

    style Agent fill:#4A90E2,color:#fff
    style Ollama fill:#E27B4A,color:#fff
    style Vol fill:#F5A623,color:#fff
```

## C4 — Component Diagram (уровень 3)

Показывает модули внутри контейнера `agent`.

```mermaid
graph LR
    subgraph AgentContainer["Container: agent"]
        Main["📄 multi_agent.py<br/>Точка входа"]
        Tools["🔧 tools.py<br/>7 инструментов"]
        Memory["💾 memory_store.py<br/>Markdown-память"]
        Logger["📝 logger.py<br/>Логирование"]
        Eval["📊 eval.py<br/>Оценка качества"]
    end

    subgraph LLM["LLM-клиент"]
        LLMClient["OpenAI-совместимый клиент<br/>base_url=ollama:11434"]
    end

    Main --> Tools
    Main --> Memory
    Main --> Logger
    Main --> LLMClient
    Eval --> Main

    LLMClient -->|HTTP| OllamaSrv["Ollama Server"]

    style Main fill:#4A90E2,color:#fff
    style Tools fill:#7ED321,color:#fff
    style Memory fill:#F5A623,color:#fff
    style Logger fill:#9013FE,color:#fff
    style Eval fill:#E27B4A,color:#fff
```

---

## Sequence Diagram — Типичный сценарий

Показывает полный поток выполнения задачи «Проанализируй sales.csv».

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 Пользователь
    participant UP as UserProxy
    participant A as 🐍 Analyst
    participant T as 🔧 Tools
    participant O as 🦙 Ollama (Qwen)
    participant R as 🔍 Reviewer
    participant M as 💾 Memory

    U->>UP: "Проанализируй sales.csv,<br/>построй график, сохрани отчёт"
    UP->>M: recall_last()
    M-->>UP: Предыдущие сессии

    UP->>A: Передаёт задачу

    Note over A,O: Шаг 1: Изучение схемы
    A->>O: LLM-запрос: нужен read_csv
    O-->>A: tool_call: read_csv("sales.csv")
    A->>T: read_csv("sales.csv")
    T-->>A: Схема + первые 5 строк

    Note over A,O: Шаг 2: Статистика
    A->>O: LLM-запрос
    O-->>A: tool_call: analyze_data(...)
    A->>T: analyze_data("sales.csv", "sales")
    T-->>A: mean=148890, std=43312, ...

    Note over A,O: Шаг 3: SQL-сводка
    A->>O: LLM-запрос
    O-->>A: tool_call: execute_sql(...)
    A->>T: execute_sql("SELECT region, SUM(sales)...")
    T-->>A: East=352750, West=812000, ...

    Note over A,O: Шаг 4: Визуализация
    A->>O: LLM-запрос
    O-->>A: tool_call: plot_chart(...)
    A->>T: plot_chart(...)
    T-->>A: reports/chart_*.png

    Note over A,O: Шаг 5: Отчёт
    A->>O: LLM-запрос
    O-->>A: tool_call: save_report(...)
    A->>T: save_report("Анализ продаж", markdown)
    T-->>A: reports/report_*.md

    A->>R: Передаёт результаты

    Note over R,O: Рецензия
    R->>O: LLM-запрос: проверь
    O-->>R: Критика + оценка 7/10 + TERMINATE

    R->>UP: Готово
    UP->>M: save_session(...)
    M-->>UP: OK

    UP-->>U: Итоговый результат
```

---

## Flow Diagram — Алгоритм работы группы

```mermaid
flowchart TD
    Start([Пользователь задаёт вопрос]) --> LoadMemory[Загрузить последние сессии из памяти]
    LoadMemory --> AnalystTurn{Ход Analyst}

    AnalystTurn --> NeedTool{Нужен tool?}
    NeedTool -->|Да| CallTool[Вызвать tool]
    CallTool --> ToolResult[Получить результат]
    ToolResult --> AnalystTurn

    NeedTool -->|Нет| CheckComplete{Все 5 шагов<br/>выполнены?}
    CheckComplete -->|Нет| AnalystTurn
    CheckComplete -->|Да| Summarize[Краткое резюме для Reviewer]

    Summarize --> ReviewerTurn{Ход Reviewer}
    ReviewerTurn --> Critique[Проверка + критика]
    Critique --> Score[Оценка 1-10]
    Score --> Terminate{TERMINATE?}

    Terminate -->|Нет| AnalystTurn
    Terminate -->|Да| SaveMemory[Сохранить сессию в память]
    SaveMemory --> SaveLog[Записать лог]
    SaveLog --> End([Готово])

    style Start fill:#4A90E2,color:#fff
    style End fill:#7ED321,color:#fff
    style AnalystTurn fill:#F5A623,color:#fff
    style ReviewerTurn fill:#9013FE,color:#fff
```

---

## Инфраструктурная схема — Сеть и Volumes

```mermaid
graph TB
    subgraph Windows["Windows Host"]
        P[Порт 11434<br/>только внутри Docker-сети]
    end

    subgraph DockerNet["Docker Network: agent-net (bridge)"]
        AgentC["Container: agent<br/>IP: 172.x.x.2"]
        OllamaC["Container: ollama<br/>IP: 172.x.x.3<br/>listens 0.0.0.0:11434"]
    end

    subgraph Volumes["Volumes & Mounts"]
        V1["Volume: ollama-data<br/>/root/.ollama (в контейнере)"]
        M1["Bind: ./data → /app/data (ro)"]
        M2["Bind: ./memory → /app/memory (rw)"]
        M3["Bind: ./reports → /app/reports (rw)"]
        M4["Bind: ./logs → /app/logs (rw)"]
    end

    AgentC -->|HTTP на ollama:11434| OllamaC
    OllamaC -.->|монтирует| V1
    AgentC -.->|читает| M1
    AgentC -.->|пишет| M2
    AgentC -.->|пишет| M3
    AgentC -.->|пишет| M4

    style AgentC fill:#4A90E2,color:#fff
    style OllamaC fill:#E27B4A,color:#fff
```

---

## Обоснование архитектурных решений

### Почему GroupChat, а не обычный pipeline?

**GroupChat** с `round_robin` даёт **детерминированный** порядок агентов: Analyst → Reviewer → Analyst → Reviewer. Это **предсказуемо** для отладки и не требует LLM-роутера.

Альтернативы:
- **Sequential pipeline** (Analyst → Reviewer фиксировано) — проще, но не даёт Analyst'у ответить на критику.
- **Auto speaker selection** (LLM выбирает, кто говорит) — гибче, но 7B-модель часто ошибается.
- **Hierarchical** (manager + workers) — избыточно для 2 агентов.

### Почему 2 агента, а не больше?

Для задачи анализа данных достаточно:
- **Analyst** — делает работу
- **Reviewer** — критикует и оценивает

Добавление третьего агента (Writer, Critic, Judge) увеличивает контекст и время, но не улучшает результат на 7B-модели.

### Почему Ollama в том же compose?

Из-за WSL2 + Docker Desktop: `host.docker.internal` не пробрасывается. Ollama в одной сети с агентом — надёжное решение.