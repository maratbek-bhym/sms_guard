import os
import sys

from django.apps import AppConfig


class ChecksConfig(AppConfig):
    name = "apps.checks"
    label = "checks"
    verbose_name = "Проверки"

    def ready(self):
        """Прогрев: модели грузятся один раз при старте сервера, а не на первом запросе пользователя.
        Не выполняется для test/migrate/shell и т.п., а также в родительском процессе autoreload."""
        argv = sys.argv
        is_manage = os.path.basename(argv[0]) == "manage.py"
        serving = (not is_manage) or (len(argv) > 1 and argv[1] == "runserver"
                                      and (os.environ.get("RUN_MAIN") == "true" or "--noreload" in argv))
        if serving and os.environ.get("ML_PRELOAD", "1") == "1":
            from ml.predictor import Predictor
            Predictor.get()   # при ошибке загрузки не падает: Predictor сохраняет errors, интерфейс покажет сообщение
