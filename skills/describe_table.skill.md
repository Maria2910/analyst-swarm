# Skill: describe_table

## Description
Схема таблицы PostgreSQL: колонки и типы.

## Input
{"table": "string"}

## Safety
- Имя таблицы по regex `^[a-zA-Z_][a-zA-Z0-9_]*$`
- Только таблицы из схемы `public`

## Example
`describe_table("sales")` → id, region, quarter, sales, ...