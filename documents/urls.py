from django.urls import path
from . import views

urlpatterns = [
    path('documents/', views.DocumentCreateView.as_view(), name='create_document'),
    path('documents/<uuid:document_id>/download', views.DocumentDownloadView.as_view(), name='download_document'),
    path('documents/<uuid:document_id>/approve', views.DocumentApproveView.as_view(), name='approve_document'),
    path('documents/<uuid:document_id>/reject', views.DocumentRejectView.as_view(), name='reject_document'),
]
