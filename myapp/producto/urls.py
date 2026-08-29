from django.urls import path
from . import views

urlpatterns=[
    path('', views.index, name='producto'),
    path('<int:producto_id>/', views.detalle, name='detalle_producto'),

]
