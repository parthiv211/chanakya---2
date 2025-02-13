# Deploy with Docker & Route Backend/Frontend through Nginx and add SSL to the domain

## Prerequisites
- Git clone repo
- Add .env files
- Add these two A Records:
    - api.tigc -> server ip
    - tigc -> server ip
- An AMI with docker installed

## Install Requirements
- sudo apt update && sudo apt upgrade
- sudo apt install nginx certbot python3-certbot-nginx
- sudo ufw enable && sudo ufw allow https && sudo ufw allow 'Nginx HTTP' && sudo ufw allow 22

## Start Server
- docker-compose up --build -d

## Configure Nginx and add https
- sudo nano /etc/nginx/conf.d/tigc.techtact.conf
```
server {
    server_name tigc.techtact.co;
    location / {
        proxy_pass http://0.0.0.0:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
server {
    server_name api.tigc.techtact.co;
    location / {
        proxy_pass http://0.0.0.0:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
- sudo systemctl restart nginx
- sudo certbot --nginx
- crontab -e
```
0 12 * * * /usr/bin/certbot renew --quiet
```

## Test

- curl -IL http://tigc.techtact.co
- curl -IL https://tigc.techtact.co
- cat /etc/nginx/conf.d/tigc.techtact.conf
```
server {
    server_name tigc.techtact.co;
    location / {
        proxy_pass http://0.0.0.0:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/tigc.techtact.co/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/tigc.techtact.co/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}
server {
    server_name api.tigc.techtact.co;
    location / {
        proxy_pass http://0.0.0.0:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/tigc.techtact.co/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/tigc.techtact.co/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}
server {
    if ($host = tigc.techtact.co) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    server_name tigc.techtact.co;
    listen 80;
    return 404; # managed by Certbot
}
server {
    if ($host = api.tigc.techtact.co) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    server_name api.tigc.techtact.co;
    listen 80;
    return 404; # managed by Certbot
```