# Skill: plot_chart

## Description
График из CSV-данных, сохранение в `reports/*.png`.

## Input
{"filename": "string", "x_column": "string", "y_column": "string",
 "chart_type": "line|bar|scatter", "title": "string"}

## Output
Путь к PNG-файлу.

## Ограничение
Работает ТОЛЬКО с CSV из `data/`. Не работает с результатами SQL-запросов.