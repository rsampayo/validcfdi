web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
worker: python efos_scheduler.py 