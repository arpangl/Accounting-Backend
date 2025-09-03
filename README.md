# Einvoice-Accounting-Backend
A accounting backend which will crawl the e-invoice platform and help you record your cost.

## How to use
**setup the environment variables listed in docker-compose.yaml before you run**

If not provided, some function may not work as usual.


### Normal Installation
```bash
git pull https://github.com/arpangl/einvoice-accounting-backend.git
```

install the requirements

```bash
pip install -r requirements.txt
```

```bash
python run_service.py
```


### Docker
Note: devtools is a self-built toolchain for developing, you can use python3.10-slim:latest as alternative

```bash
docker compose up -d --build
```

Using docker is recommended, there could have some errors occurred during parsing e-invoice procedure, docker compose can help restarting.