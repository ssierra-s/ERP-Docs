from django.urls import path
from .views import (
    CompanyCreateView, CompanyMembershipCreateView, EntityRefCreateView,
    PresignUploadView, DocumentCreateView, DocumentDownloadView,
    DocumentApproveView, DocumentRejectView,DocumentDirectUploadView,
    
)

urlpatterns = [
    path("companies/", CompanyCreateView.as_view()),
    path("companies/members/", CompanyMembershipCreateView.as_view()),
    path("entities/", EntityRefCreateView.as_view()),
    path("documents/presign-upload/", PresignUploadView.as_view()),
    path("documents/", DocumentCreateView.as_view()),
    path("documents/<uuid:document_id>/download", DocumentDownloadView.as_view()),
    path("documents/<uuid:document_id>/approve", DocumentApproveView.as_view()),
    path("documents/<uuid:document_id>/reject", DocumentRejectView.as_view()),
    path("documents/direct-upload", DocumentDirectUploadView.as_view()),
]
