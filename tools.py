"""Tools для мультиагентной системы Analyst Swarm.

Все tools безопасны: не выполняют произвольный код,
не имеют доступа к системе за пределами папки проекта.
"""

import ast
import csv
import operator
import os
import re
import sqlite3
from datetime import datetime
from typing import Any

import matplotlib
matplotlib.use("Agg")  # backend без GUI (для Docker)
import matplotlib.pyplot as plt


# ============================================================
# 1. Базовые tools
# ============================================================

def get_current_time() -> str:
    """Возвращает текущее время в формате YYYY-MM-DD HH:MM:SS."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def calculate(expression: str) -> str:
    """Безопасно вычисляет математическое выражение через AST.

    Поддерживает +, -, *, /, **, скобки, числа.
    Не выполняет произвольный Python-код (в отличие от eval).
    """
    try:
        node = ast.parse(expression, mode="eval").body
        result = _eval_node(node)
        return str(result)
    except Exception as e:
        return f"Ошибка вычисления: {e}"


def _eval_node(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _ALLOWED_OPS[type(node.op)](
            _eval_node(node.left), _eval_node(node.right)
        )
    if isinstance(node, ast.UnaryOp):
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"Неподдерживаемая операция: {ast.dump(node)}")


# ============================================================
# 2. Работа с данными
# ============================================================

DATA_DIR = "data"
REPORTS_DIR = "reports"


def read_csv(filename: str) -> str:
    """Читает CSV-файл из папки data/ и возвращает схему + первые 5 строк.

    Args:
        filename: имя файла, например "sales.csv"

    Returns:
        Текстовое описание: колонки, типы, первые строки.
    """
    # Защита от path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return "Ошибка: недопустимое имя файла."

    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        available = os.listdir(DATA_DIR) if os.path.exists(DATA_DIR) else []
        return f"Файл не найден. Доступные: {available}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return "Файл пуст."

        header = rows[0]
        data_rows = rows[1:]

        # Определяем типы по первой строке данных
        types = []
        if data_rows:
            for val in data_rows[0]:
                try:
                    int(val)
                    types.append("int")
                except ValueError:
                    try:
                        float(val)
                        types.append("float")
                    except ValueError:
                        types.append("str")

        lines = [
            f"Файл: {filename}",
            f"Строк: {len(data_rows)}",
            f"Колонок: {len(header)}",
            "",
            "Схема:",
        ]
        for col, typ in zip(header, types):
            lines.append(f"  - {col}: {typ}")

        lines.append("")
        lines.append("Первые 5 строк:")
        for row in data_rows[:5]:
            lines.append("  " + " | ".join(row))

        return "\n".join(lines)
    except Exception as e:
        return f"Ошибка чтения: {e}"


def analyze_data(filename: str, column: str) -> str:
    """Считает статистику по числовой колонке CSV-файла.

    Args:
        filename: имя файла в data/
        column: имя числовой колонки

    Returns:
        count, mean, median, min, max, std.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        return "Ошибка: недопустимое имя файла."

    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return f"Файл не найден: {filename}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            values = []
            for row in reader:
                if column in row:
                    try:
                        values.append(float(row[column]))
                    except ValueError:
                        pass

        if not values:
            return f"Колонка '{column}' не найдена или не числовая."

        values_sorted = sorted(values)
        n = len(values)
        mean = sum(values) / n
        median = (
            values_sorted[n // 2]
            if n % 2
            else (values_sorted[n // 2 - 1] + values_sorted[n // 2]) / 2
        )
        variance = sum((x - mean) ** 2 for x in values) / n
        std = variance ** 0.5

        return (
            f"Статистика по '{column}' в {filename}:\n"
            f"  count:  {n}\n"
            f"  mean:   {mean:.2f}\n"
            f"  median: {median:.2f}\n"
            f"  min:    {min(values):.2f}\n"
            f"  max:    {max(values):.2f}\n"
            f"  std:    {std:.2f}"
        )
    except Exception as e:
        return f"Ошибка анализа: {e}"


def execute_sql(query: str) -> str:
    """Выполняет SELECT-запрос к CSV-файлам, загруженным как SQLite-таблицы.

    Только SELECT. Все CSV из data/ автоматически загружаются
    как таблицы с именем = имя файла без расширения.

    Пример: SELECT region, SUM(sales) FROM sales GROUP BY region
    """
    # Жёсткая защита: только SELECT
    q = query.strip().lower()
    if not q.startswith("select"):
        return "Ошибка: разрешены только SELECT-запросы."
    for forbidden in ["insert", "update", "delete", "drop", "alter", "create"]:
        if re.search(rf"\b{forbidden}\b", q):
            return f"Ошибка: запрещённая операция '{forbidden}'."

    try:
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # Загружаем все CSV как таблицы
        if not os.path.exists(DATA_DIR):
            return "Папка data/ не найдена."

        loaded = []
        for fname in os.listdir(DATA_DIR):
            if not fname.endswith(".csv"):
                continue
            table_name = fname[:-4]  # без .csv
            path = os.path.join(DATA_DIR, fname)

            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            if not rows:
                continue
            header = rows[0]
            data = rows[1:]

            # Создаём таблицу (все колонки TEXT, SQLite сам преобразует)
            cols = ", ".join(f'"{c}" TEXT' for c in header)
            cursor.execute(f'CREATE TABLE "{table_name}" ({cols})')

            # Вставляем данные
            placeholders = ", ".join("?" * len(header))
            cursor.executemany(
                f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                data,
            )
            loaded.append(table_name)

        if not loaded:
            return "Нет загруженных CSV-файлов."

        # Выполняем запрос
        cursor.execute(query)
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description] if cursor.description else []

        # Ограничиваем вывод 100 строками
        truncated = len(rows) > 100
        rows = rows[:100]

        lines = [f"Таблицы: {loaded}", f"Колонки: {cols}", f"Строк: {len(rows)}"]
        if truncated:
            lines.append("(показаны первые 100)")
        lines.append("")
        for row in rows:
            lines.append(" | ".join(str(v) for v in row))

        conn.close()
        return "\n".join(lines)
    except Exception as e:
        return f"Ошибка SQL: {e}"


# ============================================================
# 3. Визуализация
# ============================================================

def plot_chart(filename: str, x_column: str, y_column: str,
               chart_type: str = "line", title: str = "") -> str:
    """Строит график и сохраняет PNG в reports/.

    Args:
        filename: CSV в data/
        x_column: колонка для оси X
        y_column: колонка для оси Y
        chart_type: line | bar | scatter
        title: заголовок графика

    Returns:
        Путь к сохранённому PNG или сообщение об ошибке.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        return "Ошибка: недопустимое имя файла."

    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return (
            f"Файл не найден: {filename}. "
            f"plot_chart работает ТОЛЬКО с CSV-файлами из папки data/. "
            f"Для данных из PostgreSQL сначала нужно выгрузить их в CSV. "
            f"Если данных в CSV нет — пропусти этот шаг."
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            data = list(reader)

        if not data:
            return "Файл пуст."

        x_vals = [row.get(x_column, "") for row in data]
        y_vals = []
        for row in data:
            try:
                y_vals.append(float(row[y_column]))
            except (ValueError, KeyError):
                y_vals.append(0.0)

        plt.figure(figsize=(10, 6))

        if chart_type == "bar":
            plt.bar(range(len(x_vals)), y_vals)
            plt.xticks(range(len(x_vals)), x_vals, rotation=45, ha="right")
        elif chart_type == "scatter":
            plt.scatter(range(len(x_vals)), y_vals)
        else:  # line
            plt.plot(range(len(x_vals)), y_vals, marker="o")
            plt.xticks(range(len(x_vals)), x_vals, rotation=45, ha="right")

        plt.title(title or f"{y_column} vs {x_column}")
        plt.xlabel(x_column)
        plt.ylabel(y_column)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        os.makedirs(REPORTS_DIR, exist_ok=True)
        out_path = os.path.join(
            REPORTS_DIR,
            f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )
        plt.savefig(out_path, dpi=100)
        plt.close()

        return f"График сохранён: {out_path}"
    except Exception as e:
        return f"Ошибка построения графика: {e}"


# ============================================================
# 4. Отчёты
# ============================================================

def save_report(title: str, content: str) -> str:
    """Сохраняет Markdown-отчёт в папку reports/.

    Args:
        title: заголовок отчёта
        content: Markdown-содержимое

    Returns:
        Путь к сохранённому файлу.
    """
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)

        # Чистим имя файла
        safe_title = re.sub(r"[^\w\s-]", "", title)[:50].strip().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{safe_title}_{timestamp}.md"
        path = os.path.join(REPORTS_DIR, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"_Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n")
            f.write(content)

        return f"Отчёт сохранён: {path}"
    except Exception as e:
        return f"Ошибка сохранения: {e}"


# ============================================================
# 5. Работа с PostgreSQL
# ============================================================

import psycopg2
import psycopg2.extras


def _pg_connect():
    """Создаёт подключение к PostgreSQL."""
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        user=os.environ.get("POSTGRES_USER", "analyst"),
        password=os.environ.get("POSTGRES_PASSWORD", "analyst_secret"),
        dbname=os.environ.get("POSTGRES_DB", "analytics"),
        connect_timeout=10,
    )


def list_tables() -> str:
    """Возвращает список таблиц в БД analytics с количеством строк."""
    try:
        conn = _pg_connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            conn.close()
            return "В БД нет таблиц."

        lines = [f"База данных: {os.environ.get('POSTGRES_DB', 'analytics')}", f"Таблиц: {len(tables)}", ""]
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            lines.append(f"  - {table}: {count} строк")

        conn.close()
        return "\n".join(lines)
    except Exception as e:
        return f"Ошибка БД: {e}"


def describe_table(table: str) -> str:
    """Возвращает схему таблицы: колонки, типы, ограничения."""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table):
        return "Ошибка: недопустимое имя таблицы."

    try:
        conn = _pg_connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        columns = cursor.fetchall()

        if not columns:
            conn.close()
            return f"Таблица '{table}' не найдена."

        lines = [f"Схема таблицы '{table}':", ""]
        for col, typ, nullable in columns:
            null_marker = "" if nullable == "NO" else " NULL"
            lines.append(f"  - {col}: {typ}{null_marker}")

        conn.close()
        return "\n".join(lines)
    except Exception as e:
        return f"Ошибка БД: {e}"


def query_postgres(query: str) -> str:
    """Выполняет SELECT-запрос к PostgreSQL. Только чтение.

    Пример: SELECT region, SUM(sales) FROM sales GROUP BY region ORDER BY 2 DESC
    """
    q = query.strip().lower()

    # Только SELECT
    if not q.startswith("select") and not q.startswith("with"):
        return "Ошибка: разрешены только SELECT-запросы."

    # Чёрный список
    for forbidden in ["insert", "update", "delete", "drop", "alter",
                      "create", "truncate", "grant", "revoke", "copy"]:
        if re.search(rf"\b{forbidden}\b", q):
            return f"Ошибка: запрещённая операция '{forbidden}'."

    try:
        conn = _pg_connect()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return "Запрос вернул 0 строк."

        columns = list(rows[0].keys())

        # Ограничение вывода
        truncated = len(rows) > 100
        rows = rows[:100]

        lines = [
            f"Колонки: {columns}",
            f"Строк: {len(rows)}" + (" (показаны первые 100)" if truncated else ""),
            "",
        ]
        for row in rows:
            lines.append(" | ".join(str(row[c]) for c in columns))

        conn.close()
        return "\n".join(lines)
    except Exception as e:
        return f"Ошибка SQL: {e}"

# ============================================================
# Регистрация в AutoGen
# ============================================================

def setup_tools(assistant, user_proxy):
    """Регистрирует все tools в AutoGen."""
    from autogen import register_function

    tools = [
        (get_current_time, "Получить текущее время."),
        (calculate, "Вычислить математическое выражение. Пример: '123 * 456'."),
        (read_csv, "Прочитать CSV из data/. Возвращает схему и первые строки."),
        (analyze_data, "Статистика по числовой колонке CSV (mean, median, std)."),
        (execute_sql, "SELECT-запрос к CSV как к SQLite. Пример: 'SELECT region, SUM(sales) FROM sales GROUP BY region'."),
        (plot_chart, "Построить график из CSV и сохранить в reports/. Типы: line, bar, scatter."),
        (save_report, "Сохранить Markdown-отчёт в reports/."),
        # --- PostgreSQL ---
        (list_tables, "Список таблиц в PostgreSQL БД analytics с количеством строк."),
        (describe_table, "Схема таблицы PostgreSQL: колонки и типы. Пример: 'sales'."),
        (query_postgres, "SELECT-запрос к PostgreSQL. Пример: 'SELECT region, SUM(sales) FROM sales GROUP BY region'."),
    ]

    for func, desc in tools:
        register_function(
            func,
            caller=assistant,
            executor=user_proxy,
            name=func.__name__,
            description=desc,
        )