# Analyst Swarm

Мультиагентная система анализа данных на локальной LLM.

Три агента (**Planner** + **Analyst** + **Reviewer**) на модели **Qwen 2.5 7B** работают в изолированном Docker-контейнере.

---

## Возможности

- 🗂️ Планирование задачи (Planner) перед выполнением
- 📂 Чтение CSV из `data/`
- 📊 Описательная статистика (mean, median, std)
- 🔍 SQL-запросы к CSV как к таблицам SQLite
- 📈 Графики через matplotlib → PNG
- 📝 Markdown-отчёты с инсайтами
- 🇷🇺 Всё локально, без интернета, на русском

---

## Быстрый старт

**Требования:** Docker Desktop, Windows 10/11 + WSL 2, 16 GB RAM.

```powershell
.\run.ps1
```

Или пошагово:

```bash
docker compose build agent
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:7b
docker compose up agent
```

Linux/macOS: `make run`

---

## Архитектура

```
┌──────────────────────────────────────┐
│         Windows Host (WSL2)          │
│                                      │
│   ┌──────────┐      ┌──────────┐    │
│   │  ollama  │◄─────│  agent   │    │
│   │  :11434  │ HTTP │ non-root │    │
│   └──────────┘      └────┬─────┘    │
│                          │          │
│         ┌────────────────┼────────┐ │
│         ▼        ▼       ▼        ▼ │
│      data/   memory/  reports/  logs/
│      (ro)    (rw)     (rw)      (rw)
└──────────────────────────────────────┘
```

Оба контейнера — в одной Docker-сети `agent-net`. Агент обращается к Ollama по имени сервиса `http://ollama:11434/v1`.

Подробнее — [`docs/architecture.md`](docs/architecture.md).

---

## Изоляция агента

| Параметр | Значение |
|----------|----------|
| Root FS | read-only |
| Capabilities | все убраны |
| Privileges | no-new-privileges |
| PIDs | 100 |
| RAM / CPU | 2 GB / 2 ядра |
| User | `appuser` (uid 1000) |
| Volumes | `data:ro`, `memory:rw`, `reports:rw`, `logs:rw` |

---

## Инструменты

| Tool | Назначение |
|------|-----------|
| `read_csv` | Чтение CSV из `data/` |
| `analyze_data` | Статистика по колонке |
| `execute_sql` | SELECT к CSV как SQLite |
| `plot_chart` | График (line/bar/scatter) |
| `save_report` | Markdown-отчёт в `reports/` |
| `calculate` | Безопасная математика (AST) |
| `get_current_time` | Текущее время |

---

## Память

- **Краткосрочная** — история текущего чата
- **Долгосрочная** — `memory/journal.md`
- **Семантическая** — `memory/SOUL.md`

Обоснование — [`MEMORY.md`](MEMORY.md).

---

## PostgreSQL

Агент работает с реальной БД PostgreSQL 17 в отдельном контейнере.

- БД: `analytics` (порт `5433`)
- Таблицы: `sales`, `customers`
- Tools: `list_tables`, `describe_table`, `query_postgres`

Подключение через pgAdmin: `localhost:5433`, user `analyst`, password `analyst_secret`.

---

## Evals

```bash
docker compose run --rm agent python eval.py
```

Результат: **100% pass rate** (3/3 теста). Метрики — в `logs/eval_*.json`.

---

## Наблюдаемость

- Логи → `logs/agent_*.log`
- Метрики → `logs/eval_*.json`
- Артефакты → `reports/*.png`, `reports/*.md`

Подробнее — [`OBSERVABILITY.md`](OBSERVABILITY.md).

---

## Структура

```
analyst-swarm/
├── agents/          ТЗ на агента
├── data/            Входные CSV
├── docs/            C4 + Sequence диаграммы
├── memory/          Память + SOUL.md
├── reports/         Артефакты (PNG, MD)
├── skills/          Описания навыков
├── logs/            Логи
├── multi_agent.py   Точка входа
├── tools.py         7 инструментов
├── eval.py          Оценка качества
├── Dockerfile
├── docker-compose.yml
└── run.ps1 / Makefile
```

---

## Результат работы

После запуска в `reports/` появляются:
- `chart_*.png` — график продаж по регионам
- `report_*.md` — отчёт с таблицей и инсайтами

Агент **сам** вызывает цепочку:
`read_csv → analyze_data → execute_sql → plot_chart → save_report` → Reviewer проверяет и ставит оценку.
