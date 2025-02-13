#!/bin/sh

docker-compose down && docker-compose up --build -d && docker logs backend -f
