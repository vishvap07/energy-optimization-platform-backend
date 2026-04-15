#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Create a default superuser if it doesn't exist
# We use a custom python script inline to safely create the user
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser(email='admin@example.com', password='adminpassword123', first_name='System', last_name='Admin')
    print('Superuser created: admin@example.com / adminpassword123')
else:
    print('Superuser already exists.')
"
