from django.urls import path
from .views import bom_tree, tree_view, bom_routing_table, routing_table_view

urlpatterns = [
    path('api/bom/<str:complexity>/', bom_tree),
    path('', tree_view, name='tree_view'),
    path('api/bom-routing/<str:complexity>/', bom_routing_table, name='bom_routing_table'),
    path('bom-routing/', routing_table_view, name='routing_table_view'),
]