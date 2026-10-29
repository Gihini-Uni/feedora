from django.urls import path
from . import views

urlpatterns = [
    path('role-select/login/', views.role_select_login, name='role_select_login'),
    path('role-select/register/', views.role_select_register, name='role_select_register'),
    path('login/creator/', views.login_creator, name='login_creator'),
    path('login/respondent/', views.login_respondent, name='login_respondent'),
    path('register/creator/', views.register_creator, name='register_creator'),
    path('register/respondent/', views.register_respondent, name='register_respondent'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-code/', views.resend_code, name='resend_code'),
    path('logout/', views.logout_view, name='logout'),
    #placehoders for now until I build out the actual dashboard and respondent home
    path('dashboard/', views.dashboard, name='dashboard'),
    path('respondent-home/', views.respondent_home, name='respondent_home'),
    path('profile/creator/', views.creator_profile, name='creator_profile'),
    path('profile/respondent/', views.respondent_profile, name='respondent_profile'),
    path('profile/', views.my_profile, name='my_profile'),
    path('profile/respondent/progress/', views.respondent_progress, name='respondent_progress'),
]