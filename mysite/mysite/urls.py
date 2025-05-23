from django.contrib import admin
from django.urls import path, include,re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve


urlpatterns = [
    path('admin/', admin.site.urls),
    path('lib/', include('library.urls')),
    path('', include('accounts.urls')),
    path('games/', include('games.urls')),
    path('forum/', include('forum.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)