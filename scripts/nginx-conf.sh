#!/bin/bash

# Получаем абсолютный путь к домашней директории текущего юзера
USER_HOME=$HOME
CURRENT_DIR=$(pwd)

echo "🚀 Настраиваем Nginx для проекта Biostatistics..."

# 1. Генерируем реальный конфиг из шаблона, подставляя правильный путь
export USER_HOME
envsubst '${USER_HOME}' < deploy/biostatistics.conf.template > deploy/biostatistics.conf

# 2. Копируем конфиг в системную папку Nginx
echo "⚙️ Копируем конфигурацию в /etc/nginx/conf.d/..."
sudo cp deploy/biostatistics.conf /etc/nginx/conf.d/biostatistics.conf

# 3. Выдаем права на домашние директории, чтобы Nginx мог читать статику
echo "🔑 Настраиваем права доступа к папкам..."
chmod +x $USER_HOME
chmod +x $USER_HOME/Документы
chmod +x $USER_HOME/Документы/projects
chmod +x $USER_HOME/Документы/projects/biostatistics
chmod +x $USER_HOME/Документы/projects/biostatistics/biostatistics_backend

# 4. Включаем рубильники в SELinux (актуально для Fedora/RHEL)
if command -v setsebool &> /dev/null; then
    echo "🛡️ Настраиваем SELinux..."
    sudo setsebool -P httpd_enable_homedirs 1
    sudo setsebool -P httpd_can_network_connect 1
    sudo chcon -Rt httpd_sys_content_t "$CURRENT_DIR/biostatistics_backend/static/" 2>/dev/null || true
fi

# 5. Проверяем и перезапускаем Nginx
echo "🔄 Перезапускаем Nginx..."
sudo nginx -t && sudo systemctl restart nginx

echo "✅ Всё готово! Проект доступен по адресу http://127.0.0.1/"