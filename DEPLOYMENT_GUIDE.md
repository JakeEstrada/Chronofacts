# Timeline Application Deployment Guide

## Overview
This guide covers deploying your Flask timeline application to various cloud platforms. The app uses:
- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **File Storage**: Local uploads (will need cloud storage)
- **Frontend**: HTML/CSS/JavaScript

## Prerequisites
- Python 3.8+
- PostgreSQL database
- Git repository
- Cloud provider account (AWS, Google Cloud, DigitalOcean, etc.)

---

## Option 1: Heroku Deployment (Easiest)

### Step 1: Prepare Your App
```bash
# Create requirements.txt
pip freeze > requirements.txt

# Create Procfile
echo "web: gunicorn app:app" > Procfile

# Create runtime.txt
echo "python-3.10.12" > runtime.txt
```

### Step 2: Set Up Heroku
```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login to Heroku
heroku login

# Create Heroku app
heroku create your-timeline-app

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:mini
```

### Step 3: Configure Environment Variables
```bash
# Set secret key
heroku config:set SECRET_KEY="your-super-secret-key-here"

# Set database URL (auto-configured by Heroku)
heroku config:get DATABASE_URL
```

### Step 4: Update Database Connection
Update `db.py` to use Heroku's DATABASE_URL:
```python
import os
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    if 'DATABASE_URL' in os.environ:
        # Heroku production
        url = urlparse(os.environ['DATABASE_URL'])
        return psycopg2.connect(
            host=url.hostname,
            database=url.path[1:],
            user=url.username,
            password=url.password,
            port=url.port
        )
    else:
        # Local development
        return psycopg2.connect(
            host="localhost",
            database="timeline_db",
            user="timeline_user",
            password="your_password"
        )
```

### Step 5: Deploy
```bash
# Add all files to git
git add .
git commit -m "Prepare for Heroku deployment"

# Deploy to Heroku
git push heroku main

# Run database migrations
heroku run python -c "from app import app; from db import get_db_connection; conn = get_db_connection(); conn.execute(open('init_db.sql').read()); conn.commit()"
```

---

## Option 2: AWS Deployment (More Control)

### Step 1: Set Up AWS Services
1. **EC2 Instance** (for Flask app)
2. **RDS PostgreSQL** (for database)
3. **S3 Bucket** (for file storage)
4. **CloudFront** (optional, for CDN)

### Step 2: Configure EC2 Instance
```bash
# Connect to your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx -y

# Install PostgreSQL client
sudo apt install postgresql-client -y
```

### Step 3: Set Up Application
```bash
# Clone your repository
git clone https://github.com/yourusername/chronoFacts.git
cd chronoFacts

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install gunicorn
pip install gunicorn
```

### Step 4: Configure Database
```bash
# Connect to RDS PostgreSQL
psql -h your-rds-endpoint -U your-username -d your-database

# Run the schema
\i init_db.sql
```

### Step 5: Configure File Storage
Update `app.py` to use S3 for file storage:
```python
import boto3
from botocore.exceptions import ClientError

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)

def upload_to_s3(file_path, s3_key):
    """Upload file to S3"""
    try:
        s3_client.upload_file(file_path, 'your-bucket-name', s3_key)
        return f"https://your-bucket-name.s3.amazonaws.com/{s3_key}"
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        return None
```

### Step 6: Set Up Gunicorn Service
Create `/etc/systemd/system/timeline.service`:
```ini
[Unit]
Description=Timeline Flask App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/chronoFacts
Environment="PATH=/home/ubuntu/chronoFacts/venv/bin"
ExecStart=/home/ubuntu/chronoFacts/venv/bin/gunicorn --workers 3 --bind unix:timeline.sock -m 007 app:app

[Install]
WantedBy=multi-user.target
```

### Step 7: Configure Nginx
Create `/etc/nginx/sites-available/timeline`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/chronoFacts/timeline.sock;
    }

    location /uploads/ {
        alias /home/ubuntu/chronoFacts/uploads/;
    }
}
```

### Step 8: Start Services
```bash
# Enable and start the service
sudo systemctl enable timeline
sudo systemctl start timeline

# Configure nginx
sudo ln -s /etc/nginx/sites-available/timeline /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

---

## Option 3: DigitalOcean App Platform (Simplified)

### Step 1: Prepare App Spec
Create `.do/app.yaml`:
```yaml
name: timeline-app
services:
- name: web
  source_dir: /
  github:
    repo: yourusername/chronoFacts
    branch: main
  run_command: gunicorn --worker-tmp-dir /dev/shm app:app
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: SECRET_KEY
    value: your-secret-key
databases:
- engine: PG
  name: timeline-db
  version: "12"
```

### Step 2: Deploy
```bash
# Install doctl
snap install doctl

# Authenticate
doctl auth init

# Deploy
doctl apps create --spec .do/app.yaml
```

---

## Option 4: Google Cloud Run (Serverless)

### Step 1: Create Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 app:app
```

### Step 2: Deploy to Cloud Run
```bash
# Build and deploy
gcloud run deploy timeline-app \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## File Storage Migration

### For Any Cloud Deployment:
1. **Upload files to cloud storage** (S3, Google Cloud Storage, etc.)
2. **Update database URLs** to point to cloud storage
3. **Update app to serve from cloud storage**

```python
# Example: Update file URLs in database
import psycopg2

def migrate_file_urls():
    conn = psycopg2.connect("your-database-url")
    cur = conn.cursor()
    
    # Update file_urls to point to cloud storage
    cur.execute("""
        UPDATE media 
        SET file_url = REPLACE(file_url, '/uploads/', 'https://your-bucket.s3.amazonaws.com/uploads/')
        WHERE file_url LIKE '/uploads/%'
    """)
    
    conn.commit()
    cur.close()
    conn.close()
```

---

## Environment Variables Checklist

Set these in your cloud platform:
```bash
SECRET_KEY=your-super-secret-key
DATABASE_URL=your-database-connection-string
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
FLASK_ENV=production
```

---

## Post-Deployment Checklist

- [ ] Database connection working
- [ ] File uploads working
- [ ] User authentication working
- [ ] Video playback working
- [ ] SSL certificate configured
- [ ] Domain name configured
- [ ] Monitoring/logging set up
- [ ] Backup strategy configured

---

## Troubleshooting

### Common Issues:
1. **Database connection errors**: Check DATABASE_URL and network access
2. **File upload failures**: Verify cloud storage permissions
3. **Video playback issues**: Check CORS headers and file permissions
4. **Memory issues**: Increase worker count or instance size

### Debug Commands:
```bash
# Check logs
heroku logs --tail
gcloud logging read "resource.type=cloud_run_revision"

# Test database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check file permissions
ls -la uploads/
```

---

## Cost Estimates

### Heroku:
- **Hobby Dyno**: $7/month
- **PostgreSQL Mini**: $5/month
- **Total**: ~$12/month

### AWS:
- **EC2 t3.micro**: $8.47/month
- **RDS t3.micro**: $12.41/month
- **S3**: ~$0.50/month (for small usage)
- **Total**: ~$21/month

### DigitalOcean:
- **App Platform**: $5/month
- **Managed Database**: $15/month
- **Total**: ~$20/month

---

## Security Considerations

1. **Use environment variables** for secrets
2. **Enable HTTPS** everywhere
3. **Set up proper CORS** headers
4. **Implement rate limiting**
5. **Regular security updates**
6. **Database backups**
7. **File access controls**

---

## Next Steps

1. Choose your preferred deployment option
2. Set up your cloud account
3. Follow the step-by-step guide
4. Test thoroughly before going live
5. Set up monitoring and alerts
6. Plan for scaling as your app grows

Need help with a specific platform? Let me know which one you'd like to use! 