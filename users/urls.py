from django.urls import URLPattern, URLResolver, path

from .views import UserBulkView, UserDetailView, UserListView

urlpatterns: list[URLPattern | URLResolver] = [
    path("", UserListView.as_view(), name="user-list"),
    path("bulk/", UserBulkView.as_view(), name="user-bulk"),
    
    path("<str:code_param>/", UserDetailView.as_view(), name="user-detail"),
    
]