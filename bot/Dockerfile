FROM ubuntu:focal

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Recife

RUN apt-get update -y \
  && apt-get install python3=3.8.2-0ubuntu2 python3-pip git -y --no-install-recommends \
  && apt-get install -y libpq-dev build-essential python3-dev unixodbc-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install the SQL Server ODBC driver
RUN apt-get update -y && \
  apt-get install -y curl && \
  curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
  curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
  apt-get update -y && \
  ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
  apt-get remove -y curl && \
  apt-get clean

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir
RUN playwright install chromium
RUN playwright install-deps

COPY . .

CMD ["python3", "-u", "main.py"]
