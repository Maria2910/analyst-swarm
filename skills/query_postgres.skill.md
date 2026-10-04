# Skill: query_postgres

## Description
SELECT-запросы к PostgreSQL (БД `analytics`).

## Input
{"query": "string"}

## Safety
- Только SELECT и WITH
- Чёрный список: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
  TRUNCATE, GRANT, REVOKE, COPY
- Лимит вывода: 100 строк

## Example
`SELECT region, SUM(sales) FROM sales GROUP BY region ORDER BY 2 DESC`.