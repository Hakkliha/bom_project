# serializers.py
from rest_framework import serializers
from .models import Item, BOM, BOMLine, WorkCenter, RoutingStep

class BOMLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOMLine
        fields = ('component','quantity')

class BOMTreeSerializer(serializers.Serializer):
    item_no    = serializers.CharField()
    description= serializers.CharField()
    cost       = serializers.FloatField()
    level      = serializers.IntegerField()
    children   = serializers.ListField()


class WorkCenterRoutingSerializer(serializers.Serializer):
    item_no = serializers.CharField()
    description = serializers.CharField()
    item_type = serializers.CharField()
    level = serializers.IntegerField()
    work_centers = serializers.DictField()
    total_time = serializers.IntegerField()