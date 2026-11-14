from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnalyzeThrottle(UserRateThrottle):
    scope = "analyze"      # 30/min (settings.REST_FRAMEWORK)


class AuthThrottle(AnonRateThrottle):
    scope = "auth"         # 10/min с IP — защита выдачи токена от перебора
