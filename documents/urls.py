from django.urls import path

from documents import views

app_name = "documents"

urlpatterns = [
    path("", views.DocumentListView.as_view(), name="document_list"),
    path("upload/", views.DocumentCreateView.as_view(), name="document_upload"),
    path("<int:pk>/delete/", views.delete_document, name="document_delete"),
]
