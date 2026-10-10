#!/bin/sh
# Общий пароль на сайт для показа наружу: задан SITE_PASSWORD — браузер спросит логин fsp и этот пароль.
# Не задан — сайт открыт, как раньше.
set -e
if [ -n "${SITE_PASSWORD:-}" ]; then
    printf 'fsp:%s\n' "$(openssl passwd -apr1 "$SITE_PASSWORD")" > /etc/nginx/site.htpasswd
    printf 'auth_basic "FSP";\nauth_basic_user_file /etc/nginx/site.htpasswd;\n' > /etc/nginx/site-auth.conf
    echo "site-password: на сайт поставлен общий пароль"
else
    : > /etc/nginx/site-auth.conf
fi
