# Skill: read_csv

## Description
Чтение CSV из папки `data/`. Возвращает схему и первые 5 строк.

## Input
{"filename": "string"}

## Safety
- Только файлы из `data/`
- Запрет на `..`, `/`, `\` (path traversal)

## Example
`read_csv("sales.csv")` → колонки, типы, примеры строк.