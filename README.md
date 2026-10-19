# Autoservice n1

Сайт тёплых заявок. Снаружи открыт только сайт через Nginx. Заявка пишется в PostgreSQL на этом сервере, база и backend в интернет сами не смотрят.

Проверено с внешних узлов: порт 80 отвечает страницей, порты backend (8080), pgAdmin (5050) и PostgreSQL (5432) снаружи не открываются. Registry на порту 5000 снаружи отвечает, но без логина отдаёт 401.

## Как устроен запрос

Браузер ходит на Nginx, порт 80. Nginx отдаёт запрос контейнеру frontend. Страницы — статический `frontend/dist`. Путь `/api/` frontend проксирует во внутренний backend (`backend:8080`). Backend пишет в PostgreSQL по имени `postgres` в сети `data`.

Nginx не входит в сети `app` и `data`, поэтому до backend и базы в обход frontend не доходит.

## Что доступно снаружи

| Куда | Порт | Снаружи без SSH |
|---|---|---|
| Сайт через Nginx | 80 | да, страница заявки и `/api/` |
| Backend напрямую | 8080 | нет, порт на хост не публикуется |
| pgAdmin | 5050 | нет, только `127.0.0.1` на сервере |
| PostgreSQL | 5432 | нет, порта на хосте нет |
| Registry | 5000 | да, HTTPS; без пароля каталог закрыт |

Публичный API нужен форме: `POST /api/leads` принимает заявку без входа. Список заявок, правка и админ-данные требуют JWT администратора. `GET /api/leads` без токена отвечает 401.

Поминутный сбор кликов и курсора остановлен. `POST /api/lead-metrics/` отвечает 410 и в таблицу больше не пишет.

## Сервисы

| Сервис | Образ | Доступ |
|---|---|---|
| Nginx | `nginx:stable-alpine` | порт 80 |
| Frontend | `nginx:stable-alpine` | только сеть `edge` и `app`, отдаёт `frontend/dist` |
| Backend | сборка `./backend` | сети `app` и `data`, порт на хост не публикуется |
| PostgreSQL 16 | `postgres:16-alpine` | только сеть `data` |
| pgAdmin | `dpage/pgadmin4:8.14` | `127.0.0.1:5050` |
| Registry | `registry:2` | порт 5000, HTTPS и `docker login` |
| Watchtower | `nickfedor/watchtower:1.22.3` | обновляет контейнеры с меткой `autoservice` и `enable=true` |

Сети:

- `edge` — Nginx и frontend
- `app` — frontend и backend, сеть `internal`
- `data` — backend, PostgreSQL, pgAdmin, сеть `internal`
- `admin` — только pgAdmin, чтобы с хоста открывался `127.0.0.1:5050`
- `registry_net` — реестр
- `ops` — Watchtower

Watchtower не обновляет PostgreSQL, pgAdmin и backend: у них метка обновления выключена.

## Сайт и админка

- `/` — форма заявки: контакт, бизнес, задача, способ связи.
- `/admin.html` — вход администратора, услуги, статистика.

Первый администратор создаётся на экране входа, пока в базе нет ни одного. После этого регистрация закрывается. Вход выдаёт JWT на 12 часов.

Во вкладке «Статистика» заявки сортируются по температуре. Три огонька — срочный лид, два — средний, один — холодный. Колонка «Почему» объясняет оценку. Температура считается в браузере (`frontend/src/lead-score.js`) и в базу не пишется. Учитываются срок, бюджет, роль, размер компании и объём задачи. Оттуда же берутся отдел и нужен ли персональный менеджер. Карточку можно открыть и связаться с человеком.

Услуги в админке можно добавить, изменить и удалить. Набор услуг и диапазон бюджета форма читает из `/api/admin-data/current`.

Тестовые заявки, если нужны в базе: `seed_test_leads.sql`. Файл сам ничего не записывает, его запускают вручную в psql.

## Запуск на сервере

Команды ниже выполняются в терминале на сервере.

```bash
cd /root/Autoservice_n1
cp .env.example .env
./registry/bootstrap.sh
docker compose up -d
docker compose ps
```

`bootstrap.sh` создаёт пароли в `.env`, htpasswd реестра и TLS-сертификат. Если `.env` уже есть, скрипт его не перезаписывает. Повторный выпуск сертификата: `./registry/bootstrap.sh --force`.

Сайт — это собранный `frontend/dist`, его контейнер читает с диска. После правки страниц:

```bash
cd /root/Autoservice_n1/frontend
npm install
npm run build
```

Контейнер пересоздавать не нужно. После правки Python пересоберите backend:

```bash
cd /root/Autoservice_n1
docker compose up -d --build backend
```

Схему таблиц backend создаёт при старте. `docker compose up` без `-d` держит процесс в терминале: Ctrl+C останавливает контейнеры.

## pgAdmin

С внешнего IP pgAdmin не открывается. С ноутбука поднимите SSH-туннель и оставьте это окно открытым:

```bash
ssh -i KEY -L 5050:127.0.0.1:5050 root@SERVER
```

В браузере ноутбука: `http://127.0.0.1:5050`.

Логин — `PGADMIN_DEFAULT_EMAIL` из `.env` (`admin@example.com`). Пароль — `PGADMIN_DEFAULT_PASSWORD`. Сервер Postgres уже прописан, пароль базы — `POSTGRES_PASSWORD`.

## Swagger

Документация FastAPI живёт внутри backend на порту 8080 и на сайт не публикуется. Адрес контейнера меняется после пересоздания:

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' autoservice-backend-1
ssh -i KEY -L 8080:BACKEND_IP:8080 root@SERVER
```

Затем в браузере ноутбука: `http://127.0.0.1:8080/docs`.

## Реестр

Push выполняется с ноутбука, в локальном терминале компьютера.

Сначала посмотрите `REGISTRY_HOST`, `REGISTRY_PORT`, `REGISTRY_USER` и `REGISTRY_PASSWORD` в `.env` на сервере. Затем на ноутбуке:

```bash
scp root@SERVER:/root/Autoservice_n1/registry/certs/ca.crt /tmp/ca.crt
sudo mkdir -p /etc/docker/certs.d/SERVER:5000
sudo cp /tmp/ca.crt /etc/docker/certs.d/SERVER:5000/ca.crt
docker login SERVER:5000
docker tag autoservice-backend:latest SERVER:5000/autoservice-backend:latest
docker push SERVER:5000/autoservice-backend:latest
```

`SERVER` — значение `REGISTRY_HOST`. Порт 5000 слушает все интерфейсы: без пароля реестр отвечает 401, с паролем из `.env` принимает push.

## Что не попадает в git

`.env`, ключи реестра (`registry/certs/ca.key`, `registry/certs/registry.key`), `registry/auth/htpasswd`, `frontend/node_modules` и `frontend/dist`. Пароли лежат только на сервере.
