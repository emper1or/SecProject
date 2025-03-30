from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_book, name='add_book'),
    path('add-author/', views.add_author, name='add_author'),
    path('success/', views.success, name='success'),
    path('<int:pk>/', views.book_detail, name='book_detail'),
    path('<int:pk>/edit/', views.edit_book, name='edit_book'),
    path('<int:pk>/delete/', views.delete_book, name='delete_book'),
    path('search/', views.book_search, name='book_search'),
    path('autocomplete/', views.autocomplete, name='autocomplete'),
    path('detail/<str:book_id>/', views.book_detail, name='book_detail'),
    path('author/<str:author_name>/', views.author_detail, name='author_detail'),
]