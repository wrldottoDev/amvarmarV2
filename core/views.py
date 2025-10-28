from django.db import transaction
from django.forms import inlineformset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import Http404, HttpResponse
from django.contrib.auth.models import User
from django.contrib import messages
from core.emails import send_credentials_email
from core.utils import generate_user, generate_password
from core.models import PieceItem, Warehouse, PieceWarehouse
from core.forms import WarehouseForm, PieceForm, QuickClientForm
from django.utils import timezone
from core.models import DispatchRequest, DispatchRequestItem
from core.forms import DispatchCreateForm, SelectWarehousesForm
from core.emails import send_dispatch_request_email_to_admin, send_dispatch_received_email_to_user
from django.contrib.admin.views.decorators import staff_member_required
from core.forms import DispatchUploadBOLForm
from core.emails import send_bol_email_to_user
from .forms import ApproveWithBOLForm, DispatchMethodForm, PieceItemForm, PieceItemFormSet, PieceWarehouseForm, PieceWarehouseFormSet
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
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
    if request.user.is_staff:
        return redirect("admin_panel")

    available = (
        Warehouse.objects
        .filter(cliente=request.user)
        .exclude(dispatch_items__dispatch__status__in=["PENDIENTE", "APROBADO"])
        .order_by("-created_at")
        .distinct()
    )

    if request.method == "POST":
        select_form = SelectWarehousesForm(request.POST, user=request.user)
        method_form = DispatchMethodForm(request.POST)

        if not (select_form.is_valid() and method_form.is_valid()):
            messages.error(request, "Revisa el formulario.")
            return render(request, "client_panel.html", {
                "username": request.user.get_full_name().strip() or request.user.username,
                "available": available,
                "select_form": select_form,
                "method_form": method_form,
            })

        selected = list(select_form.cleaned_data["warehouses"])
        method = method_form.cleaned_data["method"]

        # 1) Validar que llegó un invoice por cada warehouse seleccionado
        missing = []
        files_map = {}
        for w in selected:
            # Usamos el wr_number en el nombre del campo de archivo
            key = f"invoice-{w.wr_number}"
            f = request.FILES.get(key)
            if not f:
                missing.append(w.wr_number)
            else:
                files_map[w] = f

        if missing:
            messages.error(
                request,
                "Falta subir invoice para: " + ", ".join(missing)
            )
            return render(request, "client_panel.html", {
                "username": request.user.get_full_name().strip() or request.user.username,
                "available": available,
                "select_form": select_form,
                "method_form": method_form,
            })

        # 2) Crear una solicitud por cada warehouse (cada una con su invoice)
        created_ids = []
        for w in selected:
            disp = DispatchRequest.objects.create(
                user=request.user,
                method=method,
                invoice=files_map[w],  # invoice específico
                status="PENDIENTE",
            )
            DispatchRequestItem.objects.create(dispatch=disp, warehouse=w)

            # (Opcional) marcar estado del warehouse
            try:
                w.status = "EN_DESPACHO"
                w.save(update_fields=["status"])
            except Exception:
                pass

            created_ids.append(str(disp.id))

            # Notificar
            try:
                send_dispatch_request_email_to_admin(disp)
            except Exception:
                # no romper el flujo si el email falla
                pass
            if request.user.email:
                try:
                    send_dispatch_received_email_to_user(disp)
                except Exception:
                    pass

        messages.success(
            request,
            f"Se crearon {len(created_ids)} solicitudes: #{', #'.join(created_ids)}."
        )
        return redirect("index")

    else:
        select_form = SelectWarehousesForm(user=request.user)
        method_form = DispatchMethodForm()

    return render(request, "client_panel.html", {
        "username": request.user.get_full_name().strip() or request.user.username,
        "available": available,
        "select_form": select_form,
        "method_form": method_form,
    })

# PANEL ADMIN

@staff_member_required
def admin_panel(request):
    qs = Warehouse.objects.select_related("cliente").order_by("-created_at")

    client_id = request.GET.get("client") or ""
    q = (request.GET.get("q") or "").strip()
    per_page = request.GET.get("per_page") or "10"
    page = request.GET.get("page") or "1"

    if client_id:
        qs = qs.filter(cliente_id=client_id)
    if q:
        qs = qs.filter(
            Q(wr_number__icontains=q) |
            Q(shipper__icontains=q) |
            Q(carrier__icontains=q)
        )

    # tamaño de página seguro
    try:
        per_page_int = max(1, min(100, int(per_page)))
    except ValueError:
        per_page_int = 10

    paginator = Paginator(qs, per_page_int)

    # ⚠️ página segura (evita EmptyPage/PageNotAnInteger)
    try:
        page_number = int(page)
    except (TypeError, ValueError):
        page_number = 1
    if page_number < 1:
        page_number = 1
    if page_number > paginator.num_pages and paginator.num_pages > 0:
        page_number = paginator.num_pages

    # Si prefieres aún más simple: page_obj = paginator.get_page(page)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)

    clients = User.objects.filter(is_staff=False, is_active=True).order_by("username")

    ctx = {
        "warehouses": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "clients": clients,
        "client_id": client_id,
        "q": q,
        "per_page": str(per_page_int),
        "per_page_choices": [10, 20, 50, 100],
    }
    return render(request, "admin_panel.html", ctx)


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

# --- DETALLE ADMIN (sin filtrar por cliente)
@staff_member_required
def admin_warehouse_detail(request, wr_number):
    wh = get_object_or_404(Warehouse, wr_number=wr_number)
    return render(request, "admin/warehouse_detail.html", {"wh": wh})

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
def create_warehouse1(request):
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

@staff_member_required
def create_warehouse(request):
    if request.method == "POST":
        form = WarehouseForm(request.POST, request.FILES)
        formset = PieceWarehouseFormSet(request.POST, prefix="pieces")
        if form.is_valid() and formset.is_valid():
            wh = form.save()
            formset.instance = wh
            formset.save()  # aquí se crearán/sincronizarán ítems por la señal
            messages.success(request, f"Warehouse {wh.wr_number} creado. Completa los ítems individuales.")
            return redirect("edit_items_for_warehouse", wr_number=wh.wr_number)  # 👈 Paso B
    else:
        form = WarehouseForm()
        formset = PieceWarehouseFormSet(prefix="pieces")
    return render(request, "admin/create_warehouse.html", {"form": form, "formset": formset})


PieceItemFormSetFactory = inlineformset_factory(
    parent_model=PieceWarehouse,
    model=PieceItem,
    form=PieceItemForm,
    extra=0,
    can_delete=True
)

@staff_member_required
def edit_items_for_warehouse(request, wr_number):
    wh = get_object_or_404(Warehouse, wr_number=wr_number)
    pieces = wh.pieces.all().order_by('id')

    # Sincronizar por pieza (si se presionó ese botón)
    if request.method == "POST" and request.POST.get("sync_piece_id"):
        piece = get_object_or_404(PieceWarehouse, pk=request.POST["sync_piece_id"], warehouse=wh)
        desired = piece.quantity
        current = piece.items.count()
        if current < desired:
            for i in range(current + 1, desired + 1):
                PieceItem.objects.create(piece=piece, index=i)
        elif current > desired:
            for it in piece.items.order_by('-index')[:current - desired]:
                it.delete()
        messages.info(request, f"Ítems sincronizados para la pieza #{piece.pk}.")
        return redirect("edit_items_for_warehouse", wr_number=wr_number)

    bundles = []  # lista de (piece, formset)
    if request.method == "POST":
        all_valid = True
        for piece in pieces:
            prefix = f"items_{piece.pk}"
            fs = PieceItemFormSetFactory(request.POST, instance=piece, prefix=prefix)
            bundles.append((piece, fs))
            if not fs.is_valid():
                all_valid = False

        if all_valid:
            for _, fs in bundles:
                fs.save()
            messages.success(request, "Ítems guardados.")
            return redirect("admin_warehouse_detail", wr_number=wr_number)
        else:
            messages.error(request, "Revisa los errores en los ítems.")
    else:
        for piece in pieces:
            prefix = f"items_{piece.pk}"
            fs = PieceItemFormSetFactory(instance=piece, prefix=prefix)
            bundles.append((piece, fs))

    return render(request, "admin/edit_items_for_warehouse.html", {
        "wh": wh,
        "bundles": bundles,  # [(piece, formset), ...]
    })

@staff_member_required
def edit_warehouse(request, wr_number):
    wh = get_object_or_404(Warehouse, wr_number=wr_number)
    if request.method == "POST":
        form = WarehouseForm(request.POST, request.FILES, instance=wh)
        formset = PieceWarehouseFormSet(request.POST, instance=wh, prefix="pieces")
        if form.is_valid() and formset.is_valid():
            wh = form.save()
            formset.instance = wh
            formset.save()
            messages.success(request, f"Warehouse {wh.wr_number} actualizado.")
            return redirect("admin_warehouse_detail", wr_number=wh.wr_number)
        messages.error(request, "Corrige los errores del formulario.")
    else:
        form = WarehouseForm(instance=wh)
        formset = PieceWarehouseFormSet(instance=wh, prefix="pieces")

    return render(request, "admin/edit_warehouse.html", {
        "form": form,
        "formset": formset,
        "mode": "edit",
        "wh": wh,
    })


# CRUD de PieceWarehouse

@staff_member_required
def add_piece(request, wr_number):
    warehouse = get_object_or_404(Warehouse, wr_number=wr_number)
    if request.method == "POST":
        form = PieceWarehouseForm(request.POST)
        if form.is_valid():
            piece = form.save(commit=False)
            piece.warehouse = warehouse
            piece.save()
            messages.success(request, "Pieza agregada.")
            return redirect("admin_warehouse_detail", wr_number=warehouse.wr_number)
    else:
        form = PieceWarehouseForm()
    return render(request, "piece_form.html", {
        "form": form,
        "warehouse": warehouse,
        "title": "Agregar pieza",
    })

@staff_member_required
def edit_piece(request, pk):
    piece = get_object_or_404(PieceWarehouse, pk=pk)
    if request.method == "POST":
        piece_form = PieceWarehouseForm(request.POST, instance=piece)
        formset = PieceItemFormSet(request.POST, instance=piece, prefix="items")
        # Botón opcional para sincronizar
        if 'sync_items' in request.POST:
            desired = piece.quantity if piece_form.is_valid() else int(request.POST.get('quantity', piece.quantity))
            current = piece.items.count()
            # crea o borra para igualar
            if current < desired:
                for i in range(current + 1, desired + 1):
                    PieceItem.objects.create(piece=piece, index=i)
            elif current > desired:
                for it in piece.items.order_by('-index')[:current - desired]:
                    it.delete()
            messages.info(request, "Ítems sincronizados con la cantidad.")
            return redirect("edit_piece", pk=piece.pk)

        if piece_form.is_valid() and formset.is_valid():
            piece_form.save()
            formset.save()
            messages.success(request, "Pieza e ítems actualizados.")
            return redirect("admin_warehouse_detail", wr_number=piece.warehouse.wr_number)
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        piece_form = PieceWarehouseForm(instance=piece)
        formset = PieceItemFormSet(instance=piece, prefix="items")

    return render(request, "admin/edit_piece_with_items.html", {
        "piece_form": piece_form,
        "formset": formset,
        "piece": piece,
    })

@staff_member_required
def delete_piece(request, pk):
    piece = get_object_or_404(PieceWarehouse, pk=pk)
    wr_number = piece.warehouse.wr_number
    if request.method == "POST":
        piece.delete()
        messages.success(request, "Pieza eliminada.")
        return redirect("admin_warehouse_detail", wr_number=wr_number)
    # confirmación simple
    return render(request, "confirm_delete.html", {
        "title": "Eliminar pieza",
        "message": f"¿Eliminar la pieza '{piece.get_type_of_display()}' de {wr_number}?",
        "back_url": redirect("admin_warehouse_detail", wr_number=wr_number).url,
    })


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
            email=form.cleaned_data.get("email") or "",
            first_name=first,
            last_name=last,
            is_staff=False,
            is_active=True,
        )
        if user.email:
            send_credentials_email(user, password)
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


@staff_member_required
def dispatch_list(request):
    qs = DispatchRequest.objects.order_by("-created_at")
    return render(request, "dispatch_list.html", {"dispatches": qs})

@staff_member_required
def dispatch_detail(request, pk):
    disp = get_object_or_404(DispatchRequest, pk=pk)
    return render(request, "dispatch_detail.html", {"disp": disp})

@staff_member_required
def upload_bol(request, pk):
    disp = get_object_or_404(DispatchRequest, pk=pk)

    if request.method == "POST":
        form = ApproveWithBOLForm(request.POST, request.FILES, instance=disp)
        if form.is_valid():
            disp = form.save(commit=False)
            disp.bol_uploaded_at = timezone.now()
            disp.status = "APROBADO"   # o "COMPLETADO" si prefieres
            disp.save()

            try:
                send_bol_email_to_user(disp)
                messages.success(request, "B/L subido y enviado al cliente por correo.")
            except Exception as e:
                messages.warning(request, f"B/L subido, pero falló el envío de correo: {e}")

            return redirect("dispatch_detail", pk=disp.pk)
        messages.error(request, "Debes subir el archivo B/L (obligatorio).")
    else:
        form = ApproveWithBOLForm(instance=disp)

    return render(request, "upload_bol.html", {"form": form, "disp": disp})

@staff_member_required
def send_bol_to_user(request, pk):
    disp = get_object_or_404(DispatchRequest, pk=pk)
    if not disp.bill_of_lading:
        messages.error(request, "Primero debes subir el B/L.")
        return redirect("dispatch_detail", pk=pk)
    try:
        send_bol_email_to_user(disp)
        disp.status = "COMPLETADO"
        disp.save(update_fields=["status"])
        messages.success(request, "B/L enviado al cliente por correo.")
    except Exception as e:
        messages.error(request, f"No se pudo enviar el correo: {e}")
    return redirect("dispatch_detail", pk=pk)

@login_required(login_url='login')
def my_warehouses(request):
    qs = Warehouse.objects.filter(cliente=request.user).order_by("-created_at")
    return render(request, "my_warehouses.html", {"warehouses": qs})

@login_required(login_url='login')
def warehouse_detail(request, wr_number):
    wh = get_object_or_404(Warehouse, wr_number=wr_number, cliente=request.user)
    return render(request, "warehouse_detail.html", {"wh": wh})


@login_required(login_url='login')
def my_dispatches(request):
    """
    Lista solo las solicitudes del usuario que ya tienen B/L subido.
    """
    qs = (
        DispatchRequest.objects
        .filter(user=request.user, bill_of_lading__isnull=False)
        .order_by('-bol_uploaded_at', '-created_at')
        .prefetch_related('items__warehouse')
    )
    return render(request, "my_dispatches.html", {"dispatches": qs})

@login_required(login_url='login')
def my_dispatch_detail(request, pk):
    """
    Detalle de una solicitud específica del usuario; 
    asegura propiedad y muestra link al B/L + WRs incluidos.
    """
    disp = get_object_or_404(
        DispatchRequest.objects.prefetch_related('items__warehouse'),
        pk=pk, user=request.user
    )
    # (Opcional) podrías restringir que solo se vea si hay B/L:
    if not disp.bill_of_lading:
        raise Http404("Este despacho aún no tiene B/L disponible.")
    return render(request, "my_dispatch_detail.html", {"disp": disp})
