# """
# Authentication URLs for Fleet Manager API
# """
#
# from django.urls import path
# from rest_framework_simplejwt.views import TokenRefreshView
# from .views import (
#     CustomTokenObtainPairView, UserRegistrationView, UserProfileView,
#     ChangePasswordView, PasswordResetView, PasswordResetConfirmView,
#     UserListView, logout_view, current_user_view
# )
#
# app_name = 'auth'
#
# urlpatterns = [
#     # JWT Token endpoints
#     path('login/', CustomTokenObtainPairView.as_view(), name='login'),
#     path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
#     path('logout/', logout_view, name='logout'),
#
#     # User management
#     path('register/', UserRegistrationView.as_view(), name='register'),
#     path('profile/', UserProfileView.as_view(), name='profile'),
#     path('current-user/', current_user_view, name='current_user'),
#
#     # Password management
#     path('change-password/', ChangePasswordView.as_view(), name='change_password'),
#     path('reset-password/', PasswordResetView.as_view(), name='reset_password'),
#     path('reset-password/<str:uid>/<str:token>/', PasswordResetConfirmView.as_view(), name='reset_password_confirm'),
#
#     # Admin endpoints
#     path('users/', UserListView.as_view(), name='user_list'),
# ]