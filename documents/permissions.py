from rest_framework.permissions import BasePermission
from .models import CompanyMembership, Document


class IsCompanyMember(BasePermission):
    def has_permission(self, request, view):
        company_id = request.data.get("company_id") or request.query_params.get("company_id")
        if not company_id:
            return True
        if not request.user or not request.user.is_authenticated:
            return False  # 👈 evita que AnonymousUser rompa
        return CompanyMembership.objects.filter(company_id=company_id, user=request.user).exists()


    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Document):
            return CompanyMembership.objects.filter(company=obj.company, user=request.user).exists()
        return True
