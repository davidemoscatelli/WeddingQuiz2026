import os
from django.core.asgi import get_asgi_application

# 1. Imposta le variabili d'ambiente PRIMA di tutto il resto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wedding_backend.settings')

# 2. Inizializza l'applicazione Django ASGI
django_asgi_app = get_asgi_application()

# 3. Importa il resto solo dopo che Django è stato inizializzato
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import quiz_engine.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            quiz_engine.routing.websocket_urlpatterns
        )
    ),
})