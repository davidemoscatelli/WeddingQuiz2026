from django.contrib import admin
from django.urls import path
from quiz_engine import views
from django.contrib.auth import views as auth_views # Importiamo la nostra vista

urlpatterns = [
    path('admin/', admin.site.urls), # Questo è l'admin classico (per inserire le canzoni prima del matrimonio)
    path('regia/', views.telecomando, name='telecomando'), # Questo è il tuo telecomando da smartphone!
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]