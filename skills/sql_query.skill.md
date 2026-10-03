# Skill: SQL Query Execution

## Description
Выполнение безопасных SQL-запросов к подключённым базам данных.
Пока не реализован в коде — запланирован на следующий этап развития.

## Input Schema
{"query": "string", "database": "string", "params": "array"}

## Output Schema
{"columns": "array", "rows": "array", "row_count": "int"}

## Safety
- Только SELECT
- Запрещены: INSERT, UPDATE, DELETE, DROP, ALTER
- Автоматический LIMIT 1000
- Timeout 30 секунд
- Максимум 1000 строк в ответе

## Examples
- Input: `{"query": "SELECT region, SUM(sales) FROM q4 GROUP BY region"}`
- Output: `{"columns": ["region", "sum"], "rows": [["North", 1500], ["South", 980]], "row_count": 2}`