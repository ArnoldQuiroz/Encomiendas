from django.urls import path
from . import views

urlpatterns = [
    path('clientes/',                views.cliente_lista,         name='cliente_lista'),
    path('clientes/nuevo/',          views.cliente_crear,         name='cliente_crear'),
    path('clientes/exportar/',       views.cliente_exportar_csv,  name='cliente_exportar'),
    path('clientes/importar/',       views.cliente_importar_csv,  name='cliente_importar'),
    path('clientes/<int:pk>/',        views.cliente_detalle,       name='cliente_detalle'),
    path('clientes/<int:pk>/editar/', views.cliente_editar,        name='cliente_editar'),
]
