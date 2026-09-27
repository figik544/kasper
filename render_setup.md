# Инструкция по развертыванию на Render

## Подготовка репозитория

1. Создайте новый репозиторий на GitHub
2. Инициализируйте локальный репозиторий:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <ваш_URL_репозитория_GitHub>
   git branch -M main
   git push -u origin main
   ```

## Настройка на Render

1. Войдите в свою учетную запись Render
2. Нажмите "New +" и выберите "Web Service"
3. Выберите "Build and deploy from a Git repository"
4. Введите URL вашего GitHub репозитория
5. Выберите "Docker" как среду
6. Укажите ветку "main"
7. Установите Health Check Path: `/`
8. В разделе Environment Variables добавьте:
   - `DISCORD_BOT_TOKEN`: ваш токен Discord бота
   - `DATABASE_URL`: URL для базы данных (если используется)
9. Нажмите "Create Web Service"

## Важные замечания

- Discord бот будет работать постоянно на Render
- Убедитесь, что токен бота надежно защищен
- Render может спать, если сервис неактивен (для бесплатного тарифа)
- Для предотвращения сна можно использовать сервисы ping'а

## Переменные окружения

Вам нужно будет настроить следующие переменные окружения на Render:

- `DISCORD_BOT_TOKEN`: Токен вашего Discord бота (можно найти в Discord Developer Portal)
- `DATABASE_URL`: URL базы данных (если используется внешняя база данных)

## Dockerfile

Проект уже содержит Dockerfile, который будет использоваться Render для сборки и запуска приложения.

## render.yaml

Файл render.yaml содержит конфигурацию для Render, включая настройки сервиса и переменные окружения.