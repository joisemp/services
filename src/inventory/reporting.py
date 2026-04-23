from datetime import datetime, time
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font


PRODUCT_HEADERS = [
    'Product Name',
    'Product Code',
    'Variant',
    'Warehouse',
    'Category',
    'Brand',
    'Unit',
    'Available Quantity',
    'Is Low Stock',
    'Is Deleted',
    'Updated At',
]

STOCK_MOVEMENT_HEADERS = [
    'Timestamp',
    'Warehouse',
    'Product',
    'Variant',
    'Movement Type',
    'Quantity',
    'Reference Code',
    'Notes',
    'Recorded By',
    'Corrected Movement Ref',
]


def _aware_datetime(date_value, is_end=False):
    if date_value is None:
        return None

    boundary_time = time.max if is_end else time.min
    naive_dt = datetime.combine(date_value, boundary_time)

    if timezone.is_naive(naive_dt):
        return timezone.make_aware(naive_dt, timezone.get_current_timezone())
    return naive_dt


def _append_product_row(sheet, *, product, variant, low_stock_threshold):
    if variant is not None:
        available_quantity = variant.universal_available_quantity
        unit = variant.unit
        brand_name = variant.brand.name if variant.brand else ''
        variant_name = variant.name
    else:
        available_quantity = product.universal_available_quantity
        unit = product.unit
        brand_name = product.brand.name if product.brand else ''
        variant_name = ''

    sheet.append(
        [
            product.name,
            product.product_code,
            variant_name,
            product.warehouse.name if product.warehouse else '',
            product.category.name if product.category else '',
            brand_name,
            unit,
            available_quantity,
            'Yes' if available_quantity <= low_stock_threshold else 'No',
            'Yes' if product.is_deleted else 'No',
            timezone.localtime(product.updated_at).strftime('%Y-%m-%d %H:%M:%S') if product.updated_at else '',
        ]
    )


def build_products_workbook(*, products, low_stock_threshold):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Products Report'

    sheet.append(PRODUCT_HEADERS)
    for header_cell in sheet[1]:
        header_cell.font = Font(bold=True)

    for product in products:
        if product.type == 'MULTI_VARIANT':
            variants = list(product.variants.all())
            if variants:
                for variant in variants:
                    _append_product_row(
                        sheet,
                        product=product,
                        variant=variant,
                        low_stock_threshold=low_stock_threshold,
                    )
                continue

        _append_product_row(
            sheet,
            product=product,
            variant=None,
            low_stock_threshold=low_stock_threshold,
        )

    return _workbook_to_buffer(workbook)


def build_stock_movements_workbook(*, movements):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Stock Movements Report'

    sheet.append(STOCK_MOVEMENT_HEADERS)
    for header_cell in sheet[1]:
        header_cell.font = Font(bold=True)

    for movement in movements:
        recorded_by = ''
        if movement.recorded_by:
            recorded_by = movement.recorded_by.email or movement.recorded_by.phone_number or str(movement.recorded_by)

        corrected_reference = ''
        if movement.corrects_movement and movement.corrects_movement.batch:
            corrected_reference = movement.corrects_movement.batch.reference_code

        sheet.append(
            [
                timezone.localtime(movement.created_at).strftime('%Y-%m-%d %H:%M:%S') if movement.created_at else '',
                movement.warehouse.name if movement.warehouse else '',
                movement.product.name if movement.product else '',
                movement.variant.name if movement.variant else '',
                movement.get_movement_type_display(),
                movement.quantity,
                movement.batch.reference_code if movement.batch else '',
                movement.notes,
                recorded_by,
                corrected_reference,
            ]
        )

    return _workbook_to_buffer(workbook)


def _workbook_to_buffer(workbook):
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def resolve_date_range(*, date_from, date_to):
    return _aware_datetime(date_from, is_end=False), _aware_datetime(date_to, is_end=True)
