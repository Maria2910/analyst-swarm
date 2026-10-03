# Skill: Safe Calculate

## Description
Безопасное вычисление математических выражений через AST-парсер.
Не выполняет произвольный Python-код.

## Supported Operations
`+`, `-`, `*`, `/`, `**`, унарный минус, скобки.

## Input Schema
{"expression": "string"}

## Output Schema
{"result": "string"}

## Examples
- Input: `"123 * 456"` → Output: `"56088"`
- Input: `"(2 + 3) ** 2"` → Output: `"25"`

## Safety
- Используется `ast.parse`, а не `eval()`
- Разрешены только арифметические операции
- Запрещены вызовы функций, импорты, атрибуты
- Максимальная длина выражения: 1000 символов