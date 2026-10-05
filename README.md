# Autoservice n1

Контур сайта для тёплых клиентов: форма заявки снаружи, запись только внутри сервера.

Снаружи открыты два входа: Nginx (сайт, порт 80) и локальный Docker Registry (push образов, порт 5000). PostgreSQL и backend наружу порты не публикуют. База доступна только из внутренней сети Docker.

## Сервисы

| Сервис | Образ | Доступ |
|---|---|---|
| Nginx | `nginx:stable-alpine` | порт 80 |
| PostgreSQL 16 | `postgres:16-alpine` | только сеть `data` |
| pgAdmin | `dpage/pgadmin4:8.14` | `127.0.0.1:5050` на сервере |
| Registry | `registry:2` | порт 5000, HTTPS и `docker login` |
| Watchtower | `nickfedor/watchtower:1.22.3` | обновляет контейнеры с меткой `autoservice` |
| backend | — | закомментирован в `docker-compose.yml` |

Сети:

- `edge` — Nginx и будущий frontend
- `app` — только frontend и backend
- `data` — backend, PostgreSQL, pgAdmin; сеть `internal`, в интернет не ходит
- `admin` — только pgAdmin, чтобы открыть `localhost:5050`
- `registry_net` — реестр
- `ops` — Watchtower

Nginx не входит в `app` и `data`. Запрос к API в обход frontend не доходит до backend.

## Запуск на сервере

Команды ниже выполняются в терминале на сервере (терминал Cursor, подключённый к этой машине).

```bash
cd /root/Autoservice_n1
cp .env.example .env
./registry/bootstrap.sh
docker compose up -d
docker compose ps
```

`bootstrap.sh` создаёт пароли в `.env`, htpasswd реестра и TLS-сертификат. Если `.env` уже есть, скрипт его не перезаписывает. Повторный выпуск сертификата: `./registry/bootstrap.sh --force`.

Проверка, что контейнеры живы:

```bash
docker compose ps
```

## pgAdmin

С внешнего IP pgAdmin не открывается. С ноутбука поднимите SSH-туннель и оставьте это окно открытым:

```bash
ssh -L 5050:127.0.0.1:5050 root@SERVER
```

В браузере ноутбука: `http://127.0.0.1:5050`.

Логин — `PGADMIN_DEFAULT_EMAIL` из `.env` (по умолчанию `admin@example.com`). Пароль — `PGADMIN_DEFAULT_PASSWORD`. Сервер Postgres уже прописан, пароль базы — `POSTGRES_PASSWORD`.

## Реестр

Push выполняется с ноутбука, в локальном терминале компьютера, не в терминале Cursor на сервере.

Сначала посмотрите `REGISTRY_HOST`, `REGISTRY_PORT`, `REGISTRY_USER` и `REGISTRY_PASSWORD` в `.env` на сервере. Затем на ноутбуке:

```bash
scp root@SERVER:/root/Autoservice_n1/registry/certs/ca.crt /tmp/ca.crt
sudo mkdir -p /etc/docker/certs.d/SERVER:5000
sudo cp /tmp/ca.crt /etc/docker/certs.d/SERVER:5000/ca.crt
docker login SERVER:5000
docker tag autoservice-backend:latest SERVER:5000/autoservice-backend:latest
docker push SERVER:5000/autoservice-backend:latest
```

`SERVER` — значение `REGISTRY_HOST`. Если `docker login` зависает, в панели хостинга откройте входящий TCP 5000.

Watchtower подхватывает новые образы контейнеров с меткой `com.centurylinklabs.watchtower.enable=true` в scope `autoservice`. PostgreSQL и pgAdmin он не обновляет.

## Что не попадает в git

`.env`, ключи реестра (`registry/certs/ca.key`, `registry/certs/registry.key`) и `registry/auth/htpasswd`. Пароли лежат только на сервере.
