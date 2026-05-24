from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest
from django.core.exceptions import ValidationError as ModelValidationError
from django.db.models import OuterRef, Subquery, CharField

from .models import Part, ProductType, Brand, PartType, PartModelNumber
from .forms import PartForm
from .pdf_utils import generate_parts_pdf
from datetime import datetime


@login_required
def index(request):
    items = Part.objects.select_related("product_type", "brand", "part_type").all()

    product_type_id = request.GET.get("product_type", "")
    brand_id = request.GET.get("brand", "")
    part_type_id = request.GET.get("part_type", "")
    product_model = request.GET.get("product_model", "").strip()
    part_model = request.GET.get("part_model", "").strip()
    stock_status_filter = request.GET.get("stock_status", "").strip()

    if product_type_id:
        items = items.filter(product_type_id=product_type_id)
    if brand_id:
        items = items.filter(brand_id=brand_id)
    if part_type_id:
        items = items.filter(part_type_id=part_type_id)
    if product_model:
        items = items.filter(product_model__icontains=product_model)

    if part_model:
        items = items.filter(
            model_numbers__value__icontains=part_model
        ).distinct()
        matching = PartModelNumber.objects.filter(
            part=OuterRef("pk"), value__icontains=part_model
        ).values("value")[:1]
        items = items.annotate(
            searched_model_number=Subquery(matching, output_field=CharField())
        )
    else:
        first_mn = PartModelNumber.objects.filter(
            part=OuterRef("pk")
        ).values("value")[:1]
        items = items.annotate(
            searched_model_number=Subquery(first_mn, output_field=CharField())
        )

    if stock_status_filter:
        filtered_items = []
        for item in items:
            if item.stock_status == stock_status_filter:
                filtered_items.append(item)
        items = filtered_items

    product_types = ProductType.objects.all().order_by("name")
    brands = Brand.objects.all().order_by("name")

    all_parts = Part.objects.select_related("product_type", "brand", "part_type").all()
    out_of_stock_parts = []
    low_stock_parts = []

    for part in all_parts:
        total = part.total_new + part.total_used
        display_name = f"{part.part_type.name}-{part.product_type.name}-{part.brand.name}"
        part_display = {'pk': part.pk, 'part_display': display_name}

        if total == 0:
            out_of_stock_parts.append(part_display)
        elif total <= 2:
            low_stock_parts.append(part_display)

    event_notification = None
    if 'event_notification' in request.session:
        event_notification = request.session.pop('event_notification')

    context = {
        "items": items,
        "product_types": product_types,
        "brands": brands,
        "out_of_stock_parts": out_of_stock_parts,
        "low_stock_parts": low_stock_parts,
        "event_notification": event_notification,
    }
    return render(request, "dashboard/index.html", context=context)


@login_required
def get_part_types(request):
    product_type_id = request.GET.get("product_type_id", "").strip()
    part_types = []
    if not product_type_id or product_type_id == "all":
        part_types = list(
            PartType.objects.values("id", "name")
            .order_by("name")
        )
    else:
        part_types = list(
            PartType.objects.filter(product_type_id=product_type_id)
            .values("id", "name")
            .order_by("name")
        )
    return JsonResponse({"part_types": part_types})


def _resolve_fk_fields(post_data):
    errors = {}
    product_type = brand = part_type = None

    new_pt_name = post_data.get("new_product_type", "").strip()
    pt_id = post_data.get("product_type_select", "").strip()

    if new_pt_name:
        product_type, _ = ProductType.objects.get_or_create(name=new_pt_name)
    elif pt_id:
        try:
            product_type = ProductType.objects.get(pk=pt_id)
        except (ProductType.DoesNotExist, ValueError):
            errors["product_type"] = "Invalid product type selected."
    else:
        errors["product_type"] = "Product type is required."

    new_brand_name = post_data.get("new_brand", "").strip()
    brand_id = post_data.get("brand_select", "").strip()

    if new_brand_name:
        brand, _ = Brand.objects.get_or_create(name=new_brand_name)
    elif brand_id:
        try:
            brand = Brand.objects.get(pk=brand_id)
        except (Brand.DoesNotExist, ValueError):
            errors["brand"] = "Invalid brand selected."
    else:
        errors["brand"] = "Brand is required."

    new_ptype_name = post_data.get("new_part_type", "").strip()
    ptype_id = post_data.get("part_type_select", "").strip()

    if new_ptype_name:
        if product_type:
            part_type, _ = PartType.objects.get_or_create(
                name=new_ptype_name,
                product_type=product_type,
            )
        else:
            errors["part_type"] = (
                "Select or enter a product type before adding a new part type."
            )
    elif ptype_id:
        try:
            part_type = PartType.objects.get(pk=ptype_id)
        except (PartType.DoesNotExist, ValueError):
            errors["part_type"] = "Invalid part type selected."
    else:
        errors["part_type"] = "Part type is required."

    return product_type, brand, part_type, errors


def _save_model_numbers(part, model_numbers_raw):
    PartModelNumber.objects.filter(part=part).delete()
    values = [v.strip() for v in model_numbers_raw if v.strip()]
    for val in values:
        PartModelNumber.objects.create(part=part, value=val)


@login_required
def part(request):
    product_types = ProductType.objects.all().order_by("name")
    brands = Brand.objects.all().order_by("name")

    if request.method == "POST":
        product_type, brand, part_type, fk_errors = _resolve_fk_fields(request.POST)
        form = PartForm(request.POST, request.FILES)
        model_numbers_raw = request.POST.getlist("model_number")

        if not fk_errors and form.is_valid():
            part_instance = form.save(commit=False)
            part_instance.product_type = product_type
            part_instance.brand = brand
            part_instance.part_type = part_type

            try:
                part_instance.full_clean()
                part_instance.save()
                _save_model_numbers(part_instance, model_numbers_raw)

                part_name = f"{part_type.name}-{product_type.name}-{brand.name}"
                request.session['event_notification'] = {
                    'message': f"{part_name} has been added successfully!",
                    'type': 'success'
                }
                return redirect("dashboard-index")
            except ModelValidationError as exc:
                custom_shelf_msg = "A part with this Shelf Number, Row Number and Column Number already exists."
                if hasattr(exc, "message_dict"):
                    for field, msgs in exc.message_dict.items():
                        if field == "__all__":
                            cleaned = [
                                (
                                    custom_shelf_msg
                                    if "shelf" in msg.lower()
                                    and "column" in msg.lower()
                                    and "row" in msg.lower()
                                    else msg
                                )
                                for msg in msgs
                            ]
                            fk_errors["non_field_errors"] = cleaned
                        else:
                            fk_errors[field] = msgs
                else:
                    msgs = list(exc.messages)
                    fk_errors["non_field_errors"] = [
                        (
                            custom_shelf_msg
                            if "shelf" in msg.lower()
                            and "column" in msg.lower()
                            and "row" in msg.lower()
                            else msg
                        )
                        for msg in msgs
                    ]
        elif not fk_errors and not form.is_valid():
            part_instance = Part(
                product_type=product_type,
                brand=brand,
                part_type=part_type,
                image=form.cleaned_data.get("image"),
                total_new=form.cleaned_data.get("total_new", 0),
                total_used=form.cleaned_data.get("total_used", 0),
                size_kg=form.cleaned_data.get("size_kg"),
                shelf_number=form.cleaned_data.get("shelf_number"),
                column_number=form.cleaned_data.get("column_number"),
                row_number=form.cleaned_data.get("row_number"),
                notes=form.cleaned_data.get("notes"),
            )

            custom_shelf_msg = "A part with this Shelf Number, Row Number and Column Number already exists."
            all_errors = []
            seen_shelf_error = False

            for err in form.non_field_errors():
                err_str = str(err)
                if (
                    "shelf" in err_str.lower()
                    and "column" in err_str.lower()
                    and "row" in err_str.lower()
                ):
                    all_errors.append(custom_shelf_msg)
                    seen_shelf_error = True
                else:
                    all_errors.append(err_str)

            try:
                part_instance.full_clean()
            except ModelValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, msgs in exc.message_dict.items():
                        if field == "__all__":
                            for msg in msgs:
                                if (
                                    "shelf" in msg.lower()
                                    and "column" in msg.lower()
                                    and "row" in msg.lower()
                                ):
                                    if not seen_shelf_error:
                                        all_errors.append(custom_shelf_msg)
                                        seen_shelf_error = True
                                else:
                                    all_errors.append(msg)
                        else:
                            fk_errors[field] = msgs
                else:
                    for msg in exc.messages:
                        if (
                            "shelf" in msg.lower()
                            and "column" in msg.lower()
                            and "row" in msg.lower()
                        ):
                            if not seen_shelf_error:
                                all_errors.append(custom_shelf_msg)
                                seen_shelf_error = True
                        else:
                            all_errors.append(msg)

            fk_errors["non_field_errors"] = all_errors

        selected_pt_id = request.POST.get("product_type_select", "").strip()
        selected_part_types = []
        if selected_pt_id and selected_pt_id != "__new__":
            selected_part_types = list(
                PartType.objects.filter(product_type_id=selected_pt_id)
                .values("id", "name")
                .order_by("name")
            )

        context = {
            "form": form,
            "product_types": product_types,
            "brands": brands,
            "fk_errors": fk_errors,
            "posted": request.POST,
            "selected_part_types": selected_part_types,
            "posted_model_numbers": model_numbers_raw,
        }
        return render(request, "dashboard/add_part.html", context=context)

    context = {
        "form": PartForm(),
        "product_types": product_types,
        "brands": brands,
        "fk_errors": {},
        "posted": {},
        "selected_part_types": [],
        "posted_model_numbers": [],
    }
    return render(request, "dashboard/add_part.html", context=context)


@login_required
def edit_part(request, pk):
    item = get_object_or_404(
        Part.objects.select_related("product_type", "brand", "part_type"), pk=pk
    )

    product_types = ProductType.objects.all().order_by("name")
    brands = Brand.objects.all().order_by("name")
    part_types_for_product = PartType.objects.filter(
        product_type=item.product_type
    ).order_by("name")

    if request.method == "POST":
        posted = request.POST.copy()

        posted["product_type_select"] = str(item.product_type_id)
        posted.pop("new_product_type", None)

        product_type, brand, part_type, fk_errors = _resolve_fk_fields(posted)
        form = PartForm(request.POST, request.FILES, instance=item)
        model_numbers_raw = request.POST.getlist("model_number")

        if not fk_errors and form.is_valid():
            part_instance = form.save(commit=False)
            part_instance.product_type = item.product_type
            part_instance.brand = brand
            part_instance.part_type = part_type

            try:
                part_instance.full_clean()
                part_instance.save()
                _save_model_numbers(part_instance, model_numbers_raw)

                return redirect("dashboard-index")

            except ModelValidationError as exc:
                custom_shelf_msg = "A part with this Shelf Number, Row Number and Column Number already exists."
                if hasattr(exc, "message_dict"):
                    for field, msgs in exc.message_dict.items():
                        if field == "__all__":
                            cleaned = [
                                (
                                    custom_shelf_msg
                                    if "shelf" in msg.lower()
                                    and "column" in msg.lower()
                                    and "row" in msg.lower()
                                    else msg
                                )
                                for msg in msgs
                            ]
                            fk_errors["non_field_errors"] = cleaned
                        else:
                            fk_errors[field] = msgs
                else:
                    msgs = list(exc.messages)
                    fk_errors["non_field_errors"] = [
                        (
                            custom_shelf_msg
                            if "shelf" in msg.lower()
                            and "column" in msg.lower()
                            and "row" in msg.lower()
                            else msg
                        )
                        for msg in msgs
                    ]
        elif not fk_errors and not form.is_valid():
            part_instance = Part(
                product_type=item.product_type,
                brand=brand,
                part_type=part_type,
                image=form.cleaned_data.get("image"),
                total_new=form.cleaned_data.get("total_new", 0),
                total_used=form.cleaned_data.get("total_used", 0),
                size_kg=form.cleaned_data.get("size_kg"),
                shelf_number=form.cleaned_data.get("shelf_number"),
                column_number=form.cleaned_data.get("column_number"),
                row_number=form.cleaned_data.get("row_number"),
                notes=form.cleaned_data.get("notes"),
            )

            custom_shelf_msg = "A part with this Shelf Number, Row Number and Column Number already exists."
            all_errors = []
            seen_shelf_error = False

            for err in form.non_field_errors():
                err_str = str(err)
                if (
                    "shelf" in err_str.lower()
                    and "column" in err_str.lower()
                    and "row" in err_str.lower()
                ):
                    all_errors.append(custom_shelf_msg)
                    seen_shelf_error = True
                else:
                    all_errors.append(err_str)

            try:
                part_instance.full_clean()
            except ModelValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, msgs in exc.message_dict.items():
                        if field == "__all__":
                            for msg in msgs:
                                if (
                                    "shelf" in msg.lower()
                                    and "column" in msg.lower()
                                    and "row" in msg.lower()
                                ):
                                    if not seen_shelf_error:
                                        all_errors.append(custom_shelf_msg)
                                        seen_shelf_error = True
                                else:
                                    all_errors.append(msg)
                        else:
                            fk_errors[field] = msgs
                else:
                    for msg in exc.messages:
                        if (
                            "shelf" in msg.lower()
                            and "column" in msg.lower()
                            and "row" in msg.lower()
                        ):
                            if not seen_shelf_error:
                                all_errors.append(custom_shelf_msg)
                                seen_shelf_error = True
                        else:
                            all_errors.append(msg)

            fk_errors["non_field_errors"] = all_errors

        return render(
            request,
            "dashboard/edit_part.html",
            {
                "form": PartForm(
                    request.POST,
                    request.FILES,
                    instance=item,
                    initial={"product_model": item.product_model or ""},
                ),
                "item": item,
                "product_types": product_types,
                "brands": brands,
                "part_types_for_product": part_types_for_product,
                "fk_errors": fk_errors,
                "posted": posted,
                "posted_model_numbers": model_numbers_raw,
            },
        )

    return render(
        request,
        "dashboard/edit_part.html",
        {
            "form": PartForm(
                instance=item, initial={"product_model": item.product_model or ""}
            ),
            "item": item,
            "product_types": product_types,
            "brands": brands,
            "part_types_for_product": part_types_for_product,
            "fk_errors": {},
            "posted": {},
            "posted_model_numbers": [],
        },
    )


@login_required
def export_pdf(request):
    if request.method != "POST":
        return redirect("dashboard-index")

    part_ids = request.POST.getlist("part_id")

    if not part_ids:
        return redirect("dashboard-index")

    parts = (
        Part.objects.filter(id__in=part_ids)
        .select_related("product_type", "brand", "part_type")
        .prefetch_related("model_numbers")
        .order_by("id")
    )

    if not parts.exists():
        return HttpResponseBadRequest("No valid parts found for the given IDs.")

    buffer = generate_parts_pdf(parts)
    filename = f"parts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def adjust_stock(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    field = request.POST.get("field", "")
    delta_raw = request.POST.get("delta", "")

    if field not in ("total_new", "total_used"):
        return JsonResponse({"error": "Invalid field"}, status=400)

    try:
        delta = int(delta_raw)
        if delta not in (1, -1):
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid delta"}, status=400)

    part = get_object_or_404(Part, pk=pk)
    current = getattr(part, field)
    new_value = max(0, current + delta)

    part_name = f"{part.part_type.name}-{part.product_type.name}-{part.brand.name}"
    stock_type = "new" if field == "total_new" else "used"
    if delta == 1:
        message = f"A {stock_type} part has been added to {part_name}"
        notif_type = 'add'
    else:
        message = f"A {stock_type} part has been removed from {part_name}"
        notif_type = 'remove'

    request.session['event_notification'] = {
        'message': message,
        'type': notif_type
    }

    Part.objects.filter(pk=pk).update(**{field: new_value})

    return JsonResponse({"value": new_value, "field": field, "pk": pk})
