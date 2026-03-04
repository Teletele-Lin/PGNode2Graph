from django.urls import path
from . import views

app_name = 'visualizer'

urlpatterns = [
    path('', views.index, name='index'),
    path('generate/', views.generate_graph, name='generate_graph'),
    path('history/', views.view_history, name='view_history'),
    path('history/<uuid:viz_id>/', views.view_history, name='view_detail'),
    path('history/<uuid:viz_id>/dot/', views.get_dot_source, name='get_dot_source'),
    path('history/<uuid:viz_id>/delete/', views.delete_visualization, name='delete_visualization'),
    path('history/<uuid:viz_id>/svg/', views.open_svg, name='open_svg'),
]
