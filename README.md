# Analyst Swarm

Мультиагентная система анализа данных на локальной LLM.

Три агента (**Planner** + **Analyst** + **Reviewer**) на модели **Qwen 2.5 7B** работают в изолированном Docker-контейнере: читают CSV и PostgreSQL, считают статистику, выполняют SQL-запросы, строят графики и генерируют отчёты.

---

## Возможности

- 🗂️ **Планирование задачи** (Planner) перед выполнением
- 📂 Чтение CSV из `data/`
- 🐘 **Работа с PostgreSQL** (реальная СУБД в Docker)
- 📊 Описательная статистика (mean, median, std)
- 🔍 SQL-запросы к CSV и PostgreSQL
- 📈 Графики через matplotlib → PNG
- 📝 Markdown-отчёты с инсайтами
- 🔍 **Критическая проверка** результатов (Reviewer)
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
docker compose up -d ollama postgres
docker compose exec ollama ollama pull qwen2.5:7b
docker compose up agent
```

Linux/macOS: `make run`

---

## Архитектура

```
┌──────────────────────────────────────────────┐
│            Windows Host (WSL2)               │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  ollama  │  │ postgres │  │  agent   │   │
│  │  :11434  │  │  :5432   │  │ non-root │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       └─────────────┴─────────────┘         │
│           Docker network: agent-net          │
│                                              │
│       Bind mounts: data/ memory/ reports/ logs/
└──────────────────────────────────────────────┘
```

**3 контейнера в одной Docker-сети `agent-net`:**
- `ollama` — LLM
- `postgres` — база данных `analytics` (порт 5433 наружу)
- `agent` — 3 агента (Planner + Analyst + Reviewer)

Подробнее — [`docs/architecture.md`](docs/architecture.md).

---

## Мультиагентный паттерн: Plan → Execute → Review

| Агент | Роль | Tools |
|-------|------|-------|
| **Planner** | Планирует 4-5 шагов | Нет |
| **Analyst** | Выполняет план | 10 tools |
| **Reviewer** | Проверяет, ставит оценку | Нет |

**Порядок:** `Planner → Analyst → Reviewer → TERMINATE`

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

## Инструменты (10 штук)

| Tool | Назначение |
|------|-----------|
| `list_tables` | Список таблиц в PostgreSQL |
| `describe_table` | Схема таблицы |
| `query_postgres` | SELECT к PostgreSQL |
| `read_csv` | Чтение CSV из `data/` |
| `analyze_data` | Статистика по колонке |
| `execute_sql` | SELECT к CSV как SQLite |
| `plot_chart` | График → PNG |
| `save_report` | Markdown-отчёт |
| `calculate` | Безопасная математика (AST) |
| `get_current_time` | Текущее время |

---

## PostgreSQL

- **БД:** `analytics` (порт `5433` наружу)
- **Таблицы:** `sales` (16 строк), `customers` (10 строк)
- **Подключение через pgAdmin:** `localhost:5433`, user `analyst`, password `analyst_secret`

---

## Память

- **Краткосрочная** — история текущего чата
- **Долгосрочная** — `memory/journal.md`
- **Семантическая** — `memory/SOUL.md`

Обоснование — [`MEMORY.md`](MEMORY.md).

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
├── agents/          Спеки агентов (spec.yaml)
├── data/            Входные CSV
├── sql/             init.sql для PostgreSQL
├── docs/            C4 + Sequence диаграммы
├── memory/          Память + SOUL.md
├── reports/         Артефакты (PNG, MD)
├── skills/          11 описаний навыков
├── logs/            Логи
├── multi_agent.py   Точка входа (3 агента)
├── tools.py         10 инструментов
├── eval.py          Оценка качества
├── Dockerfile
├── docker-compose.yml
└── run.ps1 / Makefile
```

---

## Результат работы

После запуска в `reports/` появляются:
- `chart_*.png` — график продаж
- `report_*.md` — отчёт с инсайтами

**Пример вывода:** продажи падают по кварталам (Q1=645000 → Q4=548250, **-15%**). Маркетинг коррелирует с продажами (East mkt=61500/rev=352750, West mkt=126000/rev=812000).

Агент **сам** вызывает цепочку:
`list_tables → describe_table → query_postgres → query_postgres → save_report` → Reviewer проверяет и ставит оценку.
