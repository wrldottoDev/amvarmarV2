from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from .models import Warehouse, PieceWarehouse

class UserCreateForm(UserCreationForm):
    email = forms.EmailField(required=False)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    is_staff = forms.BooleanField(required=False, initial=True, help_text="Puede entrar al panel")
    is_active = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "is_staff", "is_active", "password1", "password2"]

class UserUpdateForm(UserChangeForm):
    password = None  # ocultar campo password hash
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "is_staff", "is_active"]

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ["cliente", "wr_number", "shipper", "carrier", "container_number",
                  "weight_lbs", "weight_kgs", "uploaded_file"]
        widgets = {"wr_number": forms.TextInput(attrs={"class": "form-control"})}

class PieceForm(forms.ModelForm):
    class Meta:
        model = PieceWarehouse
        fields = ["type_of", "quantity", "description"]

class QuickClientForm(forms.Form):
    first_name = forms.CharField(label="Nombre", max_length=30)
    last_name = forms.CharField(label="Apellido", max_length=30)
    email = forms.EmailField(label="Email", required=False)