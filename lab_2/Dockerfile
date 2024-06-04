FROM ubuntu:22.04

RUN apt update && \
    apt upgrade -y && \
    apt install -y python3 && \
    apt install -y iputils-ping

WORKDIR /app
COPY . .

ENTRYPOINT ["python3", "-u", "mtu_finder.py"]