from django.urls import path
from . import views


urlpatterns = [
    path('add/', views.add_game, name='add_game'),
    path('add-developer/', views.add_developer, name='add_developer'),
    path('success/', views.game_success, name='game_success'),
    path('<int:pk>/', views.game_detail, name='game_detail'),
    path('<int:pk>/edit/', views.edit_game, name='edit_game'),
    path('<int:pk>/delete/', views.delete_game, name='delete_game'),

]