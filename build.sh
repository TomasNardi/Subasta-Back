set -o errexit

pip install -r requirements.txt


# test
python manage.py collectstatic --noinput
python manage.py migrate --noinput
