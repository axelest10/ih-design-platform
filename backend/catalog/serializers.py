from rest_framework.serializers import ModelSerializer

from .models import Branch, Product


class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class BranchSerializer(ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"
