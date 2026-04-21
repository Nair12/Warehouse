from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from users.views import role_redirect_view


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('/redirect-by-role/')
    return redirect('/login/')

urlpatterns = [
    path('', home_redirect),
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='/login/'),
        name='logout'
    ),
    path('products/', include(('products.urls', 'products'), namespace='products')),
    path('redirect-by-role/', role_redirect_view, name='redirect_by_role'),
    path('trading/', include('trading.urls')),
    path('warehouses/', include(('warehouses.urls', 'warehouses'), namespace='warehouses')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)