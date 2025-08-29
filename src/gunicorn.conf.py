# Gunicorn configuration file
import os

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Timeout settings
timeout = 120
keepalive = 5
graceful_timeout = 60

# Restart settings
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Security
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True

# Process naming
proc_name = 'gunicorn_issueHub'

# Development vs Production
if os.environ.get('ENVIRONMENT') == 'development':
    reload = True
    loglevel = "debug"
else:
    reload = False
    loglevel = "info"
