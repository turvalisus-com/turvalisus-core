# syntax=docker/dockerfile:1
FROM python:3.9.9

WORKDIR /turvalisus
COPY . .

RUN python3 -m pip install -r requirements.txt

RUN python3 -m jsmin src/wrapper.js > static/wrapper.min.js

ENTRYPOINT [ "python3", "src/main.py" ]