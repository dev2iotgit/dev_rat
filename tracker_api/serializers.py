from rest_framework import serializers
from .models import Employee, Device, AppSession, IdleSession, SecurityEvent, DailySummary, InstalledApp

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'

class AppSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppSession
        fields = '__all__'

class IdleSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdleSession
        fields = '__all__'

class SecurityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityEvent
        fields = '__all__'

class DailySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySummary
        fields = '__all__'

class InstalledAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstalledApp
        fields = '__all__'

