from rest_framework import serializers


class AnalyticsDateRangeSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date is not None and end_date is not None:
            if start_date > end_date:
                raise serializers.ValidationError({"end_date": "End date must not be before start date."})
        
        return attrs
