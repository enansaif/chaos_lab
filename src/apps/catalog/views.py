import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from apps.catalog.models import Product
from apps.catalog.serializers import ProductSerializer


def _cache_key(prefix: str, **params) -> str:
    raw = json.dumps(params, sort_keys=True, default=str)
    digest = hashlib.md5(raw.encode()).hexdigest()
    return f"catalog:{prefix}:{digest}"


class ProductListView(ListAPIView):
    serializer_class = ProductSerializer
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        queryset = Product.objects.all()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    def list(self, request, *args, **kwargs):
        if settings.CACHE_ENABLED:
            page = request.query_params.get("page", "1")
            category = request.query_params.get("category", "")
            cache_key = _cache_key("products_list", page=page, category=category)
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        response = super().list(request, *args, **kwargs)

        if settings.CACHE_ENABLED:
            cache.set(cache_key, response.data, timeout=settings.CACHE_TTL_SECONDS)

        return response


class ProductDetailView(RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    authentication_classes = []
    permission_classes = []

    def retrieve(self, request, *args, **kwargs):
        cache_key = None
        if settings.CACHE_ENABLED:
            pk = kwargs.get("pk")
            cache_key = _cache_key("product_detail", pk=pk)
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        response = super().retrieve(request, *args, **kwargs)

        if settings.CACHE_ENABLED:
            cache.set(cache_key, response.data, timeout=settings.CACHE_TTL_SECONDS)

        return response
