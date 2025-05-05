from django.urls import path
from simulation.views import simulate_base_case_from_complexity, simulate_base_case_template_view, simulate_all_top_level_base_case, simulate_top_level_by_complexity, simulate_base_case_test, simulate_all_top_level_costing_sw_case

urlpatterns = [
    path('base-case/all/', simulate_all_top_level_base_case, name='simulate_all_base_api'),
    path('sw-case/all/', simulate_all_top_level_costing_sw_case, name='simulate_all_costing_sw_base_api'),  # <-- new endpoint for costing software simulation
    path('base-case/<str:complexity>/', simulate_base_case_from_complexity, name='simulate_base_api'),
    path('base-case/view/<str:complexity>/', simulate_base_case_template_view, name='simulate_base_view'),
    path('base-case/top-level-by-complexity/<str:complexity>/', simulate_top_level_by_complexity, name='simulate_by_complexity'),
    path('base-case-test/', simulate_base_case_test, name='simulate_base_case_test'),  # <-- new test endpoint

]
