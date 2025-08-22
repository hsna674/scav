source venv/bin/activate

# main scavenger hunt application
gunicorn hunt.wsgi -b $HOST:$PORT -w 1

# pre scavenger hunt application
gunicorn waiting:app -b $HOST:$PORT -w 1