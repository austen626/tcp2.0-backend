from django.contrib import admin
from django.urls import path, include

urlpatterns = [
	path('admin/', admin.site.urls),
	path('accounts/', include('accounts.urls')),
	path('exp/', include('expediated.urls')),
	path('sales/', include('sales.urls'))
]