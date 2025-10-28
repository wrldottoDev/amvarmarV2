from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from .models import DispatchRequest, PieceItem, Warehouse, PieceWarehouse
from django.forms import inlineformset_factory, BaseInlineFormSet

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

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = [
            "wr_number", "cliente", "shipper", "carrier", "container_number",
            "uploaded_file", "weight_lbs", "weight_kgs", "status"
        ]
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned = super().clean()
        # Si no viene weight_lbs, asegúrate de que weight_kgs venga (o viceversa)
        lbs = cleaned.get("weight_lbs")
        kgs = cleaned.get("weight_kgs")
        if not lbs and not kgs:
            raise forms.ValidationError("Debes indicar el peso en lbs o en kgs.")
        return cleaned


class PieceWarehouseForm(forms.ModelForm):
    class Meta:
        model = PieceWarehouse
        fields = ["type_of", "quantity", "description"]
        widgets = {
            "type_of": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
        }


class BasePieceFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        valid_forms = 0
        for form in self.forms:
            if getattr(form, "cleaned_data", None) and not form.cleaned_data.get("DELETE", False):
                # cuenta formularios con type_of y quantity presentes
                if form.cleaned_data.get("type_of") and form.cleaned_data.get("quantity"):
                    valid_forms += 1
        if valid_forms < 1:
            raise forms.ValidationError("Agrega al menos una pieza (tipo de carga).")


PieceWarehouseFormSet = forms.inlineformset_factory(
    parent_model=Warehouse,
    model=PieceWarehouse,
    form=PieceWarehouseForm,
    formset=BasePieceFormSet,
    fields=["type_of", "quantity", "description"],
    extra=1,          # muestra 1 fila por defecto
    can_delete=True,  # permite borrar filas en edición
    validate_min=True,
    min_num=1,
)

class QuickClientForm(forms.Form):
    first_name = forms.CharField(label="Nombre", max_length=30)
    last_name = forms.CharField(label="Apellido", max_length=30)
    email = forms.EmailField(label="Email", required=False)


class DispatchCreateForm(forms.ModelForm):
    # checkboxes de warehouses van por separado
    class Meta:
        model = DispatchRequest
        fields = ["method", "invoice"]
        widgets = {
            "method": forms.Select(attrs={"class": "form-select"}),
        }

class DispatchMethodForm(forms.ModelForm):
    class Meta:
        model = DispatchRequest
        fields = ["method"]
        widgets = {
            "method": forms.Select(attrs={"class": "form-select"}),
        }

class SelectWarehousesForm(forms.Form):
    warehouses = forms.ModelMultipleChoiceField(
        queryset=Warehouse.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Warehouses"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        qs = Warehouse.objects.filter(cliente=user)
        # Excluir los que ya estén en solicitudes abiertas
        qs = qs.exclude(dispatch_items__dispatch__status__in=["PENDIENTE", "APROBADO"])
        self.fields["warehouses"].queryset = qs.order_by("-created_at").distinct()


class ApproveWithBOLForm(forms.ModelForm):
    class Meta:
        model = DispatchRequest
        fields = ["bill_of_lading"]  # SOLO el archivo

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Obligar a subir archivo
        self.fields["bill_of_lading"].required = True
        self.fields["bill_of_lading"].widget.attrs.update({"class": "form-control"})

class DispatchUploadBOLForm(forms.ModelForm):
    class Meta:
        model = DispatchRequest
        fields = ["bill_of_lading"]


class PieceItemForm(forms.ModelForm):
    class Meta:
        model = PieceItem
        fields = [
            'index',
            'weight_lbs', 'weight_kgs',
            'length_cm', 'width_cm', 'height_cm',
            'notes'
        ]
        widgets = {
            'index': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'weight_lbs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'weight_kgs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'length_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'width_cm':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }

class BasePieceItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # Validar que haya exactamente 'quantity' formularios válidos (no marcados con DELETE)
        parent = getattr(self, 'instance', None)
        if not parent:
            return
        desired = parent.quantity
        count_valid = 0
        indexes = set()
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            # si todos los campos vienen vacíos, Django lo considera vacío si extra; nosotros contamos los con index
            idx = form.cleaned_data.get('index')
            if idx:
                count_valid += 1
                if idx in indexes:
                    form.add_error('index', 'Índice duplicado en el grupo.')
                indexes.add(idx)
        if count_valid != desired:
            raise forms.ValidationError(
                f"Debes tener exactamente {desired} ítems (actualmente {count_valid})."
            )

PieceItemFormSet = inlineformset_factory(
    parent_model=PieceWarehouse,
    model=PieceItem,
    form=PieceItemForm,
    formset=BasePieceItemFormSet,
    extra=0,          # no agregues extras automáticos; manejamos con botón
    can_delete=True
)