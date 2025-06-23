# Deployment Scripts

Этот каталог содержит скрипты для деплоя и тестирования приложения в Google Cloud Run.

## Скрипты

### 🧪 `test_before_deploy.sh`
**Рекомендуется запускать перед каждым деплоем!**

Комплексная проверка готовности приложения к деплою:

```bash
./scripts/test_before_deploy.sh
```

**Что проверяет:**
1. ✅ Импорты Python модулей
2. ✅ Создание FastAPI приложения  
3. ✅ Исправление ошибок импорта
4. ✅ Сборка Docker образа
5. ✅ Запуск Docker контейнера
6. ✅ Наличие необходимых зависимостей
7. ✅ Структура проекта

**Результат:** 
- Зеленые галочки ✅ = готово к деплою
- Красные крестики ❌ = есть проблемы, деплой не рекомендуется

### 🚀 `build_and_deploy.sh`
Сборка и деплой в Cloud Run:

```bash
./scripts/build_and_deploy.sh
```

**Что делает:**
- Собирает Docker образ
- Отправляет в Artifact Registry
- Деплоит в Cloud Run
- Сохраняет переменные окружения

### 📋 `check_logs.sh`
Просмотр логов Cloud Run:

```bash
./scripts/check_logs.sh
```

### ⚙️ `set_env_vars.sh`
Настройка переменных окружения:

```bash
./scripts/set_env_vars.sh
```

### 🔗 `set_webhook.py`
Настройка Telegram webhook:

```bash
python scripts/set_webhook.py
```

## Workflow для деплоя

1. **Тестирование:** `./scripts/test_before_deploy.sh`
2. **Деплой:** `./scripts/build_and_deploy.sh`  
3. **Проверка:** `./scripts/check_logs.sh`

## Требования

- Docker Desktop
- Google Cloud CLI (gcloud)
- Python 3.11+
- Доступ к проекту `ales-f75a1` 