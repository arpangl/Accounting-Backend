FROM devtools:latest

WORKDIR /app

RUN apt update && apt upgrade -y && apt install -y libnss3\
          libnspr4\
          libatk1.0-0\
          libatk-bridge2.0-0\
          libcups2\
          libdrm2\
          libxkbcommon0\
          libxcomposite1\
          libxdamage1\
          libxfixes3\
          libxrandr2\
          libgbm1\
          libgtk-3-0\
          libpango-1.0-0\
          libcairo2\
          libasound2\
          libatspi2.0-0

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run_service.py"]
