# Master Server

[![GitHub License](https://img.shields.io/github/license/OpenTTD/master-server)](https://github.com/OpenTTD/master-server/blob/main/LICENSE)
[![GitHub Tag](https://img.shields.io/github/v/tag/OpenTTD/master-server?include_prereleases&label=stable)](https://github.com/OpenTTD/master-server/releases)
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/OpenTTD/master-server/latest/main)](https://github.com/OpenTTD/master-server/commits/main)

[![GitHub Workflow Status (Testing)](https://img.shields.io/github/workflow/status/OpenTTD/master-server/Testing/main?label=main)](https://github.com/OpenTTD/master-server/actions?query=workflow%3ATesting)
[![GitHub Workflow Status (Publish Image)](https://img.shields.io/github/workflow/status/OpenTTD/master-server/Publish%20image?label=publish)](https://github.com/OpenTTD/master-server/actions?query=workflow%3A%22Publish+image%22)
[![GitHub Workflow Status (Deployments)](https://img.shields.io/github/workflow/status/OpenTTD/master-server/Deployment?label=deployment)](https://github.com/OpenTTD/master-server/actions?query=workflow%3A%22Deployment%22)

[![GitHub deployments (Staging)](https://img.shields.io/github/deployments/OpenTTD/master-server/staging?label=staging)](https://github.com/OpenTTD/master-server/deployments)
[![GitHub deployments (Production)](https://img.shields.io/github/deployments/OpenTTD/master-server/production?label=production)](https://github.com/OpenTTD/master-server/deployments)

This repository contains two components to have a functional Master Server for the OpenTTD clients.

1) a `master_server` component, which runs the actual Master Server and communicates with the OpenTTD clients.
2) a `web_api` component, which allows HTTP access to the current online servers known by the Master Server.

These are in a single repository, as they share the same database access.

## Development

The `master_server` and `web_api` are written in Python 3.8, and makes strong use of asyncio and aiohttp.

Both make use of the AWS DynamoDB database to store the known servers.

### Running a local server

#### Dependencies

- Python3.8 or higher.
- Docker

#### Preparing your venv

To start it, you are advised to first create a virtualenv:

```bash
python3 -m venv .env
.env/bin/pip install -r requirements.txt
```

#### Preparing docker

You need to run a local AWS DynamoDB to experiment with.
AWS supplies a version via Docker (you can also run it via Java; this is left as an exercise to the reader):

```bash
docker run --rm -p 8000:8000 amazon/dynamodb-local
```

This will start an empty AWS DynamoDB server on port 8000.

#### Starting master_server

You can start the `master_server` by running:

```bash
AWS_ACCESS_KEY_ID=1 AWS_SECRET_ACCESS_KEY=1 .env/bin/python -m master_server --app master_server --web-port 8081 --db dynamodb --dynamodb-host http://127.0.0.1:8000
```

This will start the server on port 3978 (default) for you to work with locally.
The webserver on port 8081 is just to monitor the health of the server.
You can change your `/etc/hosts` or `C:\Windows\System32\drivers\etc` to map `master.openttd.org` to `127.0.0.1` and `::1` for local testing.

#### Starting web_api

You can start the `web_api` by running:

```bash
AWS_ACCESS_KEY_ID=1 AWS_SECRET_ACCESS_KEY=1 .env/bin/python -m master_server --app web_api --web-port 8080 --db dynamodb --dynamodb-host http://127.0.0.1:8000
```

This will start the HTTP server on port 8080 for you to work with locally.
It does require some servers to be in the database to be useful, so make sure to start a master_server locally and run a (dedicated) server to add an entry.

### Running via docker

```bash
docker build -t openttd/master-server:local .
docker run --rm --name ms-dynamodb -p 8000:8000 amazon/dynamodb-local
docker run --rm --link ms-dynamodb -p 127.0.0.1:3978:3978/udp -p 127.0.0.1:8081:80 -e AWS_ACCESS_KEY_ID=1 -e AWS_SECRET_ACCESS_KEY=1 openttd/master-server:local --app master_server --bind 0.0.0.0 --db dynamodb --dynamodb-host http://ms-dynamodb:8000
docker run --rm --link ms-dynamodb -p 127.0.0.1:8080:80 -e AWS_ACCESS_KEY_ID=1 -e AWS_SECRET_ACCESS_KEY=1 openttd/master-server:local --app web_api --bind 0.0.0.0 --db dynamodb --dynamodb-host http://ms-dynamodb:8000
```

This will start an empty AWS DynamoDB, the Master Server listing on UDP 3978 and the Web API on HTTP port 8080.
