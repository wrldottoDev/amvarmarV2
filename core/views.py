from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import Http404, HttpResponse
from django.contrib.auth.models import User
from django.contrib import messages
from core.utils import generate_user, generate_password
from core.models import Warehouse, PieceWarehouse
from core.forms import WarehouseForm, PieceForm, QuickClientForm

# AUTH VIEWS

def login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_panel" if request.user.is_staff else "index")

    if request.method == "POST":
        u = request.POST.get("username")
        p = request.POST.get("password")
        try:
            user = authenticate(request, username=u, password=p)
            if user:
                auth_login(request, user)
                return redirect("admin_panel" if user.is_staff else "index")
            messages.error(request, "Credenciales inválidas")
        except Exception as e:
            return HttpResponse("Vaya... algo salió mal: " + str(e))

    return render(request, "login.html")


def logout_view(request):
    auth_logout(request)
    return redirect("login")


@login_required(login_url='login')
def index(request):
    username = request.user.get_full_name().strip() or request.user.username
    return render(request, "client_panel.html", {"username": username})


# PANEL ADMIN

@login_required(login_url='login')
def admin_panel(request):
    if not request.user.is_staff:
        # Solo el personal (staff) puede acceder
        return redirect("index")

    warehouses = Warehouse.objects.all().order_by('-created_at')

    return render(request, 'admin_panel.html', {
        'warehouses': warehouses,
    })


# CRUD de Warehouses

@login_required(login_url='login')
def warehouse_detail(request, wr_number):

    if not request.user.is_staff:
        return redirect("index")

    warehouse = get_object_or_404(Warehouse, wr_number=wr_number)
    pieces = warehouse.pieces.all().order_by('type_of')

    # Formulario vacío para crear nueva pieza inline
    form = PieceForm()

    return render(request, 'warehouse_detail.html', {
        'warehouse': warehouse,
        'pieces': pieces,
        'form': form,
    })


@login_required(login_url='login')
def delete_warehouse(request, wr_number):
    if not request.user.is_staff:
        return redirect("index")

    warehouse = get_object_or_404(Warehouse, wr_number=wr_number)

    if request.method == "POST":
        warehouse.delete()
        messages.success(request, f"Warehouse {wr_number} eliminado correctamente.")
        return redirect('admin_panel')

    return render(request, 'confirm_delete.html', {'warehouse': warehouse})


@login_required(login_url='login')
def create_warehouse(request):
    """
    Crear un nuevo warehouse desde el panel.
    """
    if not request.user.is_staff:
        return redirect("index")

    if request.method == "POST":
        form = WarehouseForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Warehouse creado correctamente.")
            return redirect('admin_panel')
        else:
            messages.error(request, "Revisá los datos del formulario.")
    else:
        form = WarehouseForm()

    return render(request, 'warehouse_form.html', {'form': form})

@login_required(login_url='login')
def edit_warehouse(request, wr_number):
    """
    Editar un warehouse existente identificado por wr_number.
    """
    if not request.user.is_staff:
        return redirect("index")

    warehouse = get_object_or_404(Warehouse, wr_number=wr_number)

    if request.method == "POST":
        form = WarehouseForm(request.POST, request.FILES, instance=warehouse)
        if form.is_valid():
            form.save()
            messages.success(request, f"Warehouse {wr_number} actualizado.")
            return redirect('warehouse_detail', wr_number=wr_number)
        else:
            messages.error(request, "Revisá los datos del formulario.")
    else:
        form = WarehouseForm(instance=warehouse)

    return render(request, 'warehouse_form.html', {
        'form': form,
        'is_edit': True,
        'warehouse': warehouse,
    })


# CRUD de PieceWarehouse

@login_required(login_url='login')
def add_piece(request, wr_number):
    if not request.user.is_staff:
        return redirect("index")

    warehouse = get_object_or_404(Warehouse, wr_number=wr_number)

    if request.method == "POST":
        form = PieceForm(request.POST)
        if form.is_valid():
            piece = form.save(commit=False)
            piece.warehouse = warehouse   
            piece.save()
            messages.success(request, "Pieza agregada correctamente.")
            return redirect('warehouse_detail', wr_number=wr_number)
        # Si es inválido, re-renderiza mostrando errores:
        pieces = warehouse.pieces.all().order_by('type_of')
        return render(request, 'warehouse_detail.html', {
            'warehouse': warehouse,
            'pieces': pieces,
            'form': form,  # con errores
        })
    return redirect('warehouse_detail', wr_number=wr_number)


@login_required(login_url='login')
def edit_piece(request, pk):
    """
    Editar una pieza existente.
    """
    if not request.user.is_staff:
        return redirect("index")

    piece = get_object_or_404(PieceWarehouse, pk=pk)
    if request.method == "POST":
        form = PieceForm(request.POST, instance=piece)
        if form.is_valid():
            # Asegurarse de no permitir cambiar la pieza a otro warehouse
            obj = form.save(commit=False)
            obj.warehouse = piece.warehouse
            obj.save()
            messages.success(request, "Pieza actualizada.")
            return redirect('warehouse_detail', wr_number=piece.warehouse.wr_number)
        else:
            messages.error(request, "Revisá los datos.")
    else:
        form = PieceForm(instance=piece)

    return render(request, 'piece_form.html', {
        'form': form,
        'warehouse': piece.warehouse
    })


@login_required(login_url='login')
def delete_piece(request, pk):
    """
    Eliminar una pieza (con confirmación reutilizable).
    """
    if not request.user.is_staff:
        return redirect("index")

    piece = get_object_or_404(PieceWarehouse, pk=pk)
    wr_number = piece.warehouse.wr_number
    if request.method == "POST":
        piece.delete()
        messages.success(request, "Pieza eliminada.")
        return redirect('warehouse_detail', wr_number=wr_number)

    return render(request, 'confirm_delete.html', {'warehouse': piece.warehouse, 'piece': piece})


@login_required(login_url='login')
def clients_list(request):
    """
    Base de datos de clientes (usuarios que NO son staff).
    """
    if not request.user.is_staff:
        return redirect("index")

    q = request.GET.get("q", "").strip()
    clients = User.objects.filter(is_staff=False).order_by("id")
    if q:
        clients = clients.filter(username__icontains=q) | clients.filter(first_name__icontains=q) | clients.filter(last_name__icontains=q)

    return render(request, "panel/clients_list.html", {
        "clients": clients,
        "q": q,
    })


@login_required(login_url='login')
@transaction.atomic
def quick_create_client(request):
    """
    Crear cliente rápido: solo nombre y apellido.
    Genera username y password automáticamente.
    """
    if not request.user.is_staff:
        return redirect("index")

    if request.method == "POST":
        form = QuickClientForm(request.POST)
        if form.is_valid():
            first = form.cleaned_data["first_name"].strip()
            last = form.cleaned_data["last_name"].strip()

            # Generar username base con tu helper
            base_username = generate_user(first, last)  # p. ej. "ogonzalez7"
            username = base_username

            # Asegurar unicidad
            attempt = 0
            while User.objects.filter(username=username).exists():
                attempt += 1
                # añade un dígito o sufijo incremental
                username = f"{base_username}{attempt}"

            # Generar password
            password = generate_password()

            # Crear usuario cliente
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first,
                last_name=last,
                is_active=True,
                is_staff=False,   # Cliente, no staff
            )
            # Si incluyes email en el form:
            # user.email = form.cleaned_data.get("email", "")
            # user.save(update_fields=["email"])

            messages.success(
                request,
                f"Cliente creado: usuario '{username}'. Guarda esta contraseña (solo se muestra una vez): {password}"
            )
            # Redirige al listado (o a un detalle si luego lo agregas)
            return redirect("clients_list")
    else:
        form = QuickClientForm()

    return render(request, "panel/quick_client_form.html", {
        "form": form
    })
