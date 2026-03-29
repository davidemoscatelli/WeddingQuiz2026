import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import quiz_engine.routing # Lo creeremo tra un attimo

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wedding_backend.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            quiz_engine.routing.websocket_urlpatterns
        )
    ),
})