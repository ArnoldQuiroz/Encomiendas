# envios/urls.py
from django.urls import path
from . import views
from . import views_auth

urlpatterns = [
    # 🎯 Landing pública (redirige al dashboard si está logueado)
    path('inicio/',                      views.landing_publica,   name='landing_publica'),

    # 🌐 Tracking público (sin login)
    path('track/',                       views.tracking_landing,  name='tracking_landing'),
    path('track/<str:codigo>/',          views.tracking_detalle,  name='tracking_detalle'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Encomiendas
    path('encomiendas/',                 views.encomienda_lista,          name='encomienda_lista'),
    path('encomiendas/nueva/',           views.encomienda_crear,          name='encomienda_crear'),
    path('encomiendas/<int:pk>/',         views.encomienda_detalle,        name='encomienda_detalle'),
    path('encomiendas/<int:pk>/editar/',  views.encomienda_editar,         name='encomienda_editar'),
    path('reportes/',                       views.reportes,                  name='reportes'),
    path('mapa/',                           views.mapa_envios,               name='mapa_envios'),
    path('heatmap/',                        views.mapa_heatmap,              name='mapa_heatmap'),
    path('backup/',                         views.backup_view,               name='backup'),
    path('backup/descargar/<str:formato>/', views.backup_descargar,          name='backup_descargar'),

    # 💳 Pagos y cupones
    path('encomiendas/<int:pk>/pagar/',     views.encomienda_marcar_pago,    name='encomienda_pagar'),
    path('cobros/',                         views.cobros_pendientes,         name='cobros_pendientes'),
    path('cupones/',                        views.cupones_lista,             name='cupones_lista'),

    # 📊 Status
    path('status/',                         views.status_page,               name='status_page'),
    path('encomiendas/<int:pk>/ticket/',    views.encomienda_ticket,         name='encomienda_ticket'),
    path('encomiendas/<int:pk>/etiqueta/',  views.encomienda_etiqueta,       name='encomienda_etiqueta'),
    path('favoritos/',                         views.favoritos_lista,               name='favoritos_lista'),
    path('actividad/',                         views.actividad_feed,                name='actividad_feed'),
    path('tareas/',                            views.tareas_lista,                  name='tareas_lista'),
    path('encomiendas/bulk/',                  views.encomienda_bulk_action,        name='encomienda_bulk'),
    path('encomiendas/<int:pk>/favorito/',     views.encomienda_favorito_toggle,    name='encomienda_favorito'),
    path('encomiendas/<int:pk>/duplicar/',  views.encomienda_duplicar,       name='encomienda_duplicar'),
    path('encomiendas/<int:pk>/comentar/',  views.encomienda_comentar,       name='encomienda_comentar'),
    path('comentarios/<int:pk>/eliminar/',  views.comentario_eliminar,       name='comentario_eliminar'),
    path('encomiendas/<int:pk>/estado/',    views.encomienda_cambiar_estado, name='encomienda_cambiar_estado'),

    # Autenticación
    path('login/',         views_auth.login_view,         name='login'),
    path('logout/',        views_auth.logout_view,        name='logout'),
    path('perfil/',        views_auth.perfil_view,        name='perfil'),
    path('configuracion/', views_auth.configuracion_view, name='configuracion'),
]