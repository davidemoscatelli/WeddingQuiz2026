from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Cambia .as_async() in .as_asgi()
    re_path(r'ws/quiz/$', consumers.QuizConsumer.as_asgi()),
]