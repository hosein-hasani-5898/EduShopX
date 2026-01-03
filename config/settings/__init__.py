import os

DJANGO_ENV = os.getenv("DJANGO_ENV", "development")

if DJANGO_ENV == "production":
    from .prod_settings import *
else:
    from .dev_settings import *




