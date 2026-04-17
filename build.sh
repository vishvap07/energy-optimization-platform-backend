#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Create a default superuser if it doesn't exist
# We use a custom python script inline to safely create the user
echo "Checking superuser status..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
email = 'admin@example.com'
if not User.objects.filter(email=email).exists():
    print(f'Creating superuser: {email}')
    User.objects.create_superuser(email=email, password='adminpassword123', first_name='System', last_name='Admin')
    print('Superuser created successfully.')
else:
    print(f'Superuser {email} already exists.')
"
echo "Build script completed."
