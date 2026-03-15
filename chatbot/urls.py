from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('health/', views.health_check, name='health_check'),
    path('debug-db/', views.debug_db, name='debug_db'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('register/', views.register_user, name='register'),
]
