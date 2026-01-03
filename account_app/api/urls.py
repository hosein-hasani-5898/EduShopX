from django.urls import path
from account_app.api import views
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)
from account_app.api.views import MyTokenObtainPairView

app_name = "account"
urlpatterns = [
    path('account/register/student/', views.StudentRegisterView.as_view(), name='student_register'),
    path('account/register/teacher/', views.TeacherRegisterView.as_view(), name='teacher_register'),
    path("auth/logout/", views.logout_view, name="logout"),
    path('auth/login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
]

