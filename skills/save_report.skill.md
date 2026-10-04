# Skill: save_report

## Description
Сохранение Markdown-отчёта в `reports/`.

## Input
{"title": "string", "content": "string (markdown)"}

## Output
Путь к сохранённому файлу.

## Example
`save_report("Анализ продаж", "# Продажи\n\n...")` → `reports/report_*.md`.