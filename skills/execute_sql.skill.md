# Skill: execute_sql

## Description
SELECT-запросы к CSV как к таблицам SQLite (in-memory).

## Input
{"query": "string"}

## Safety
- Только SELECT
- Чёрный список: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE
- Лимит вывода: 100 строк

## Example
`SELECT region, SUM(sales) FROM sales GROUP BY region`.