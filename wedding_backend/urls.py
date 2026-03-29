from django.contrib import admin
from django.urls import path
from quiz_engine import views # Importiamo la nostra vista

urlpatterns = [
    path('admin/', admin.site.urls), # Questo è l'admin classico (per inserire le canzoni prima del matrimonio)
    path('regia/', views.telecomando, name='telecomando'), # Questo è il tuo telecomando da smartphone!
]