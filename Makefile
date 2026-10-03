# Makefile — Запуск Analyst Swarm (Linux/macOS)
# Использование: make run

.PHONY: run build ollama pull agent eval clean logs

run: build ollama pull agent
	@echo "=== Готово ==="
	@echo "Результаты: reports/"
	@echo "Логи:       logs/"

build:
	@echo "[1/4] Сборка образа агента..."
	docker compose build agent

ollama:
	@echo "[2/4] Запуск Ollama..."
	docker compose up -d ollama

pull:
	@echo "[3/4] Проверка модели..."
	@docker compose exec -T ollama ollama list | grep -q qwen2.5:7b \
		&& echo "Модель уже загружена" \
		|| (echo "Скачиваю модель..." && docker compose exec ollama ollama pull qwen2.5:7b)

agent:
	@echo "[4/4] Запуск агента..."
	docker compose up agent

eval:
	docker compose run --rm agent python eval.py

logs:
	@ls -la logs/ reports/

clean:
	docker compose down
	rm -rf logs/*.log reports/*.png reports/*.md 2>/dev/null || true