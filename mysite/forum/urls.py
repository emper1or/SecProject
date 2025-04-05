from django.urls import path
from . import views

urlpatterns = [
    path('', views.forum_home, name='forum_home'),
    path('category/<int:category_id>/', views.category_topics, name='category_topics'),
    path('category/<int:category_id>/create/', views.create_topic, name='create_topic'),
    path('topic/<int:topic_id>/', views.topic_messages, name='topic_messages'),
    path('topic/<int:topic_id>/add/', views.add_message, name='add_message'),
    path('message/<int:message_id>/vote/', views.vote_message, name='vote_message'),
]