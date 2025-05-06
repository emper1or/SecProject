from django.urls import path, re_path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('validate_username/', views.validate_username, name='validate_username'),
    path('validate_email/', views.validate_email, name='validate_email'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('verify/', views.verify, name='verify'),
    path('resend-code/', views.resend_code, name='resend_code'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('change_password/', views.change_password, name='change_password'),
    path('delete-avatar/', views.delete_avatar, name='delete_avatar'),
]