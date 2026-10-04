# Skill: analyze_data

## Description
Описательная статистика по числовой колонке CSV.

## Input
{"filename": "string", "column": "string"}

## Output
count, mean, median, min, max, std.

## Example
`analyze_data("sales.csv", "sales")` → `mean=148890, std=43312`.