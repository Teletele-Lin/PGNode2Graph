# PGNode2Graph

A visualization project for PostgreSQL parse trees, query trees, and plan trees. Based on the Python Django framework, suitable for deployment on servers for multi-user sharing and collaboration.

## Features

- Visualize PostgreSQL parse trees, query trees, and plan trees
- Web-based interface built with Django
- Graphviz integration for graph rendering
- Multi-user support with session management
- History tracking for previous visualizations
- Responsive design with SVG graphs

## HOW IT WORKS
Serialized parse trees, query trees, and plan trees from PostgreSQL are converted into DOT source code, rendered as SVG images via Graphviz, with interactive functionality added to the SVGs using the `jquery.graphviz.svg`.

## HOW TO USE
- Get the serialized data
For PostgreSQL Developers: Two Common Methods to Obtain Serialized Tree Structure Data
1. Using Debug Parameters and Log Files
The most straightforward approach involves enabling PostgreSQL's built-in debug parameters, which output serialized tree structures directly to the server logs.
    ```sql
    -- Enable debug output for different tree types
    SET debug_print_parse = ON;        -- Outputs raw parse tree
    SET debug_print_rewritten = ON;    -- Outputs rewritten query tree
    SET debug_print_plan = ON;         -- Outputs execution plan tree

    -- Ensure messages are logged
    SET client_min_messages = LOG;
    ```

2. Using GDB Debugger with nodeToString()
For developers working with PostgreSQL source code or extensions, direct access via GDB (GNU Debugger) provides programmatic access to serialized trees.

    Prerequisites:
    - PostgreSQL compiled with debug symbols (`--enable-debug`)
    - GDB installed on the system
    - Understanding of PostgreSQL's internal data structures

    GDB Session Example:
    ```bash
    # 1. Start GDB with PostgreSQL backend process

    # 2. Set breakpoint at strategic locations
    (gdb) break pg_plan_query
    (gdb) break standard_planner

    # 3. When breakpoint hits, examine and serialize trees
    (gdb) print nodeToString(parseTree)
    (gdb) print nodeToString(queryTree)
    (gdb) print nodeToString(planTree)
    ```

- Paste the serialized data
![homepage](docs/imgs/homepage.png)
- Visualization
![details](docs/imgs/details.png)

## Prerequisites

- Python 3.8+
- Django 6.0+
- Graphviz (system dependency)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd node2graph
```

### 2. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install graphviz
```

## Configuration

### Environment Variables

Create a `.env` file or set system environment variables:

```bash
# Production secret key (MUST be changed in production)
export DJANGO_SECRET_KEY='your-strong-secret-key-here-minimum-50-characters'

# Allowed hosts (comma-separated)
export DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1'
```

Generate a strong secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Database Setup

The project uses SQLite by default. To use PostgreSQL or other databases, update `node2graph/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_database_name',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Quick Start

### 1. Apply Database Migrations

```bash
python manage.py migrate
```

### 2. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 3. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 4. Run Development Server

```bash
python manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000) in your browser.

## Deployment

### Development Environment

For development and testing:
```bash
python manage.py runserver 0.0.0.0:8000
```

### Production Deployment with Gunicorn

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run with Gunicorn:
```bash
gunicorn --workers 3 --bind 0.0.0.0:8000 node2graph.wsgi:application
```

### Production Deployment with Gunicorn + Nginx

1. **Gunicorn Configuration**:
```bash
gunicorn --workers 4 --bind unix:/tmp/gunicorn.sock node2graph.wsgi:application
```

2. **Nginx Configuration** (`/etc/nginx/sites-available/node2graph`):
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location /static/ {
        alias /path/to/node2graph/staticfiles/;
    }

    location / {
        proxy_pass http://unix:/tmp/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Enable the site**:
```bash
sudo ln -s /etc/nginx/sites-available/node2graph /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Docker Deployment (Example)

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8000", "node2graph.wsgi:application"]
```

Build and run:
```bash
docker build -t node2graph .
docker run -p 8000:8000 -e DJANGO_SECRET_KEY=your-secret-key node2graph
```

## Security Configuration

### Production Settings

Ensure these settings in `node2graph/settings.py` for production:

```python
# Set DEBUG to False
DEBUG = False

# Configure ALLOWED_HOSTS
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')

# SSL/HTTPS settings (if using SSL)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
```

### Environment Variables for Production

```bash
# Required
export DJANGO_SECRET_KEY='very-long-random-secret-key'
export DJANGO_ALLOWED_HOSTS='your-domain.com,www.your-domain.com'

# Optional database configuration
export DATABASE_URL='postgres://username:password@localhost/dbname'
```

## Usage

### Accessing the Application

1. Open your browser and navigate to `http://your-server:8000`
2. The main interface allows you to:
   - Enter PostgreSQL query plans
   - Visualize parse trees
   - View query execution plans
   - Browse visualization history

### API Endpoints

- `/` - Home page with visualization interface
- `/visualizer/history/` - View visualization history
- `/admin/` - Django admin interface (if superuser created)

## Maintenance

### Database Backups

**SQLite Backup:**
```bash
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d)
```

**Export Data:**
```bash
python manage.py dumpdata --indent 2 > backup_$(date +%Y%m%d).json
```

### Cleaning Old Data

Clean visualizations older than 30 days:
```bash
python manage.py shell -c "
from visualizer.models import Visualization
from django.utils import timezone
from datetime import timedelta

old_date = timezone.now() - timedelta(days=30)
old_viz = Visualization.objects.filter(created_at__lt=old_date)
count = old_viz.count()
for viz in old_viz:
    if viz.graph_image:
        viz.graph_image.delete()
    viz.delete()
print(f'Deleted {count} old records')
"
```

### Logs

Application logs are stored in `deletion.log`. View logs:
```bash
tail -f deletion.log
```

## Troubleshooting

### Common Issues

1. **Static files not loading**:
   - Ensure `collectstatic` was run
   - Check Nginx/Apache static file configuration
   - Verify file permissions

2. **Database errors**:
   - Check database file permissions for SQLite
   - Verify database connection settings for other databases

3. **ALLOWED_HOSTS errors**:
   - Set `DJANGO_ALLOWED_HOSTS` environment variable
   - Include your domain or IP address

4. **Graphviz not found**:
   - Install Graphviz system package
   - Verify Graphviz is in PATH

### Debug Mode

For debugging, enable DEBUG mode temporarily:
```bash
export DJANGO_DEBUG=True
python manage.py runserver
```

## Project Structure

```
node2graph/
├── node2graph/          # Django project settings
│   ├── settings.py      # Configuration
│   ├── urls.py          # URL routing
│   └── wsgi.py          # WSGI application
├── visualizer/          # Main application
│   ├── models.py        # Data models
│   ├── views.py         # View logic
│   ├── urls.py          # App URLs
│   └── templates/       # HTML templates
├── static/              # Static assets
├── requirements.txt     # Python dependencies
├── manage.py            # Django management
└── README.md           # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Dependencies

- Django 6.0+
- Django Extensions 4.1+
- Graphviz 0.21+
- Pillow 12.0.0+
- Pydot 4.0.1+

Full list in `requirements.txt`

## Quick Links

- **DOT**: [pgNodeGraph](https://github.com/shenyuflying/pgNodeGraph)
- **Responsive Graph**: [jquery.graphviz.svg](https://github.com/mountainstorm/jquery.graphviz.svg)
- **Viz.js Library**: [viz-js](https://github.com/mdaines/viz-js)
- **Graphviz Online**: [GraphvizOnline](https://github.com/dreampuf/GraphvizOnline)

## Support

For issues and feature requests, please use the GitHub issue tracker.

