# run.ps1 — Запуск Analyst Swarm одной командой (Windows)
# Использование: .\run.ps1

Write-Host "=== Analyst Swarm — запуск ===" -ForegroundColor Cyan

# 1. Сборка образа агента
Write-Host "`n[1/4] Сборка образа агента..." -ForegroundColor Yellow
docker compose build agent
if ($LASTEXITCODE -ne 0) { Write-Host "Ошибка сборки" -ForegroundColor Red; exit 1 }

# 2. Запуск Ollama
Write-Host "`n[2/4] Запуск Ollama..." -ForegroundColor Yellow
docker compose up -d ollama

# 3. Проверка наличия модели
Write-Host "`n[3/4] Проверка модели qwen2.5:7b..." -ForegroundColor Yellow
$models = docker compose exec -T ollama ollama list 2>$null
if ($models -notmatch "qwen2.5:7b") {
    Write-Host "Модель не найдена. Скачиваю (это займёт 5-10 минут)..." -ForegroundColor Magenta
    docker compose exec ollama ollama pull qwen2.5:7b
} else {
    Write-Host "Модель уже загружена." -ForegroundColor Green
}

# 4. Запуск агента
Write-Host "`n[4/4] Запуск агента..." -ForegroundColor Yellow
docker compose up agent

Write-Host "`n=== Готово ===" -ForegroundColor Cyan
Write-Host "Результаты: reports/" -ForegroundColor Green
Write-Host "Логи:       logs/" -ForegroundColor Green
Write-Host "Память:     memory/journal.md" -ForegroundColor Green