#
# So this ugly container is a workaround for me being unable to share a
# fuse mounted volume in memory without using host's FS as a mediator
#

FROM python:3.8-buster

RUN apt-get update && apt-get install -y nginx-full supervisor pkg-config gcc fuse3 libfuse3-dev musl-dev && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app /var/log/supervisor
WORKDIR /app

COPY dockerfiles/supervisor.nginx.conf /etc/supervisor/conf.d/nginx.conf
COPY dockerfiles/supervisor.python.conf /etc/supervisor/conf.d/python.conf

COPY dockerfiles/nginx.site.conf /etc/nginx/sites-enabled/nginx-webdav.conf
COPY dockerfiles/nginx.conf /etc/nginx/nginx.conf

COPY src/requirements.txt /app

RUN pip install -r /app/requirements.txt
RUN pip install supervisor-stdout

COPY src/ /app

CMD ["/usr/bin/supervisord","-n"]
