from rest_framework.viewsets import ModelViewSet

from security.permissions import ROLE_MARKETING, ROLE_PLATFORM_ADMIN, RoleAwareViewSet

from .models import Branch, Product
from .serializers import BranchSerializer, ProductSerializer


class ProductViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }


class BranchViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }
