from django import forms
from .models import Shift

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = [
            'name', 'start_time', 'end_time', 
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
        ]
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Day Shift'}),
        }
