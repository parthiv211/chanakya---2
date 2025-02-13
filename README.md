# Chanakya

## Development

### Backend
- Install python 3.10.8
- Install all the requirements in `requirements.txt`
- Install all the requirements in `requirements-dev.txt`
- Fill the `env template` file and change its name to `.env`
- Run using VSCode debugger (F5) (Config file: `.vscode/launch.json`)
- OR run using `uvicorn main:app --reload`

### Frontend
- Install node 14.21.1
- Install packages from `package.json`
- Add a .env file with each config in a line like `URL=http://localhost:8000`
- Run using `yarn dev`

---
## Deployment

### DB Setup
- Change urls in `alembic template.ini` and rename it to `alembic.ini`
- Run migration specifing the env `alembic -n local revision --autogenerate -m "Version1.0"`
- Apply the migration `alembic -n local upgrade head`

### Server Setup
- Follow NGINX.md for nginx setup
- Run `./deploy.sh` to build and run both the docker containers

---

## Notes

<!-- - Run `pre-commit install` and `pre-commit run --all-files` -->

### Loadtesting
- `locust -f tests/locustfile.py`

### Cleanup backend imports
- `isort .`
- `autoflake --remove-all-unused-imports --in-place -r *`

### Format code
`autopep8 . -r --in-place`


### Uncommit a commited file
- `git rm -r --cached .`
- remove the file
- `git add .`
- `git commit -am "Removed file from commit"`


### Manually build, tag and run a docker container
```
docker stop chanakya-backend
docker rm chanakya-backend
docker build -t chanakya-backend .
docker run --name chanakya-backend -p 8000:8000 -d chanakya-backend
```

### Config sample to deploy using supervisor:
```
[program:fashav]
command=/home/ubuntu/miniconda3/envs/fashav/bin/uvicorn main:app --port 8000 --host 0.0.0.0
directory=/home/ubuntu/fashav-backend
autostart=true
autorestart=true
startretries=3
stderr_logfile=/var/log/fashav/error.log
stdout_logfile=/var/log/fashav/output.log
user=ubuntu
```