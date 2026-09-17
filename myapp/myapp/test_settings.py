from .settings import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
# Las migraciones históricas usan SQL de PostgreSQL; estas pruebas verifican
# el comportamiento con el esquema de los modelos en SQLite.
MIGRATION_MODULES = {'producto': None}
