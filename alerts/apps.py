from django.apps import AppConfig
from tasks import notify_user


class AlertsConfig(AppConfig):
    name = 'alerts'

    def ready(self):
        # importing model classes
        pass
