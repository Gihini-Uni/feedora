# ── Replace your entire surveys/urls.py with this ──────────────────────────

from django.urls import path
from . import views

urlpatterns = [
    # Creator side
    path('',                          views.my_surveys,         name='my_surveys'),
    path('new/',                      views.survey_type_select, name='survey_type_select'),
    path('new/<str:survey_type>/',    views.create_survey,      name='create_survey'),
    path('<uuid:uid>/dashboard/',     views.survey_dashboard,   name='survey_dashboard'),
    path('<uuid:uid>/export/',        views.export_csv,         name='export_csv'),

    # Preview (builder preview — no login needed, reads sessionStorage)
    path('preview/',                  views.survey_preview,     name='survey_preview'),

    # Respondent side — all public, no login required
    path('access/',                   views.access_survey,      name='access_survey'),
    path('respond/<uuid:uid>/',       views.respond_survey,     name='respond_survey'),
    path('respond/<uuid:uid>/submit/',views.submit_response,    name='submit_response'),

    path('<uuid:uid>/features/', views.add_features, name='add_features'),
    path('<uuid:uid>/edit/', views.edit_survey, name='edit_survey'),
    path('<uuid:uid>/delete/', views.delete_survey, name='delete_survey'),
    path('ab-comparison/', views.ab_comparison, name='ab_comparison'),
]