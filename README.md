# certbot-dns-dnsmgr

Плагин-аутентификатор для [Certbot](https://certbot.eff.org/), работающий с DNS через [DNSmanager](https://www.ispsystem.com/dnsmanager) от ISPsystem.

Плагин автоматизирует прохождение проверки `dns-01`: создаёт TXT-запись через API DNSmanager, а после проверки удаляет её.

## Настройка DNSmanager

Пользователь, от имени которого работает API, должен видеть список доменов (зон) и уметь управлять их ресурсными записями. Плагин сам выбирает в DNSmanager самую длинную зону, подходящую под проверяемый домен, поэтому работают и зоны вида `example.com`, и `example.co.uk`.

## Установка

Плагин нужно ставить в то же Python-окружение, в котором установлен Certbot:

```bash
pip install certbot-dns-dnsmgr
```

Certbot, установленный через snap, не видит плагины из PyPI. В этом случае используйте Certbot, установленный через pip или пакетный менеджер, или Docker (см. ниже).

Проверить, что Certbot видит плагин:

```bash
certbot plugins
```

## Аргументы командной строки

Чтобы Certbot проходил DNS-проверку через DNSmanager, передайте ему следующие аргументы:

| Аргумент | Описание |
| -------- | -------- |
| `--authenticator dns-dnsmgr` | Выбрать этот плагин (обязательно). |
| `--dns-dnsmgr-credentials` | INI-файл с учётными данными API DNSmanager. Обязателен, если учётные данные не переданы в командной строке. |
| `--dns-dnsmgr-username` | Имя пользователя DNSmanager (вместо INI-файла). |
| `--dns-dnsmgr-password` | Пароль DNSmanager (вместо INI-файла). |
| `--dns-dnsmgr-endpoint` | URL API DNSmanager, например `https://dns.example.com:1500/dnsmgr` (вместо INI-файла). |
| `--dns-dnsmgr-insecure` | Не проверять TLS-сертификат API DNSmanager (для самоподписанных сертификатов). |
| `--dns-dnsmgr-propagation-seconds` | Сколько секунд ждать распространения DNS, прежде чем просить ACME-сервер проверить запись. По умолчанию 10. |

## Учётные данные

Пример файла `credentials.ini`:

```ini
dns_dnsmgr_username = admin
dns_dnsmgr_password = mysecretpassword
dns_dnsmgr_endpoint = https://dns.example.com:1500/dnsmgr
# Раскомментируйте, если у панели самоподписанный сертификат
# dns_dnsmgr_insecure = true
```

Если endpoint не заканчивается на `/dnsmgr`, суффикс добавляется автоматически.

Путь к файлу можно ввести интерактивно или передать аргументом `--dns-dnsmgr-credentials`. Certbot запоминает путь к файлу, чтобы использовать его при продлении, но содержимое файла не сохраняет.

Если файл доступен другим пользователям системы, Certbot выводит предупреждение «Unsafe permissions on credentials configuration file» с путём к файлу. Оно появляется при каждом использовании файла, в том числе при продлении. Убрать его можно только исправив права доступа, например командой `chmod 600`.

## Примеры

Получить один сертификат на `example.com` и `*.example.com` с ожиданием распространения DNS 90 секунд:

```bash
certbot certonly \
  --authenticator dns-dnsmgr \
  --dns-dnsmgr-credentials /etc/letsencrypt/.secrets/domain.tld.ini \
  --dns-dnsmgr-propagation-seconds 90 \
  --server https://acme-v02.api.letsencrypt.org/directory \
  --agree-tos \
  --rsa-key-size 4096 \
  -d 'example.com' \
  -d '*.example.com'
```

Получить сертификат, передав учётные данные прямо в командной строке. Для скриптов так проще, но менее безопасно, если скрипт не защищён:

```bash
certbot certonly \
  --authenticator dns-dnsmgr \
  --dns-dnsmgr-username admin \
  --dns-dnsmgr-password mysecretpassword \
  --dns-dnsmgr-endpoint https://dns.example.com:1500/dnsmgr \
  --dns-dnsmgr-propagation-seconds 900 \
  -d example.com
```

## Docker

Чтобы собрать Docker-образ с плагином, создайте в пустом каталоге такой `Dockerfile`:

```dockerfile
FROM certbot/certbot
RUN pip install certbot-dns-dnsmgr
```

Соберите образ:

```bash
docker build -t certbot/dns-dnsmgr .
```

После сборки запускайте так:

```bash
docker run --rm \
   -v /var/lib/letsencrypt:/var/lib/letsencrypt \
   -v /etc/letsencrypt:/etc/letsencrypt \
   --cap-drop=all \
   certbot/dns-dnsmgr certonly \
   --authenticator dns-dnsmgr \
   --dns-dnsmgr-propagation-seconds 900 \
   --dns-dnsmgr-credentials \
       /etc/letsencrypt/.secrets/domain.tld.ini \
   --no-self-upgrade \
   --keep-until-expiring --non-interactive --expand \
   --server https://acme-v02.api.letsencrypt.org/directory \
   -d example.com -d '*.example.com'
```

Каталог с секретами рекомендуется защитить:

```bash
chown root:root /etc/letsencrypt/.secrets
chmod 700 /etc/letsencrypt/.secrets
chmod 600 /etc/letsencrypt/.secrets/*.ini
```
