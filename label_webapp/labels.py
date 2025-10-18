import io, os, tempfile
from dataclasses import dataclass
from typing import List, Optional

import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.utils import ImageReader

# Optional: docx2pdf for DOCX. If unavailable, template must be PDF or omitted.
try:
    from docx2pdf import convert as docx2pdf_convert
except Exception:
    docx2pdf_convert = None

INCH = 72.0

@dataclass
class LabelOptions:
    rotate_deg: float = 90
    left_x_in: float = 5.1
    right_x_in: float = 10.1
    row_centers_in: List[float] = None
    box_width_in: float = 1.75
    box_height_in: float = 2.50
    dpi_barcode: int = 300
    dpi_template: int = 300
    fill_order: str = "zigzag"  # or "left_first"

    def __post_init__(self):
        if self.row_centers_in is None:
            self.row_centers_in = [7.4, 5.4, 3.4, 1.4]


def _paginate(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def _build_slots(opts: LabelOptions):
    left = [(opts.left_x_in * INCH, r * INCH) for r in opts.row_centers_in]
    right = [(opts.right_x_in * INCH, r * INCH) for r in opts.row_centers_in]

    if opts.fill_order == "left_first":
        return left + right

    out = []
    for i in range(len(opts.row_centers_in)):
        out.append(left[i])
        out.append(right[i])
    return out


def _image_reader_from_pdf_page(pdf_path: str, page_index: int, dpi: int) -> ImageReader:
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    zoom = dpi / 72.0
    pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return ImageReader(io.BytesIO(pm.tobytes("png")))


def _image_reader_from_pdf_first_page(pdf_path: str, dpi: int) -> ImageReader:
    return _image_reader_from_pdf_page(pdf_path, 0, dpi)


def _image_reader_from_docx_first_page(docx_path: str, dpi: int) -> Optional[ImageReader]:
    if not docx2pdf_convert:
        raise RuntimeError("DOCX templates require docx2pdf on this system.")
    with tempfile.TemporaryDirectory() as td:
        out_pdf = os.path.join(td, "template.pdf")
        docx2pdf_convert(docx_path, out_pdf)
        return _image_reader_from_pdf_first_page(out_pdf, dpi)


def _load_template_image(template_path: Optional[str], dpi_template: int) -> Optional[ImageReader]:
    if not template_path:
        return None
    ext = os.path.splitext(template_path)[1].lower()
    if ext == ".pdf":
        return _image_reader_from_pdf_first_page(template_path, dpi_template)
    if ext == ".docx":
        return _image_reader_from_docx_first_page(template_path, dpi_template)
    raise ValueError("Template must be a .pdf or .docx file")


def process_labels(input_pdf: str, output_pdf: str, template_docx_or_pdf: Optional[str], options: LabelOptions) -> None:
    # Load barcodes as images
    doc = fitz.open(input_pdf)
    zoom = options.dpi_barcode / 72.0
    mat = fitz.Matrix(zoom, zoom)
    images = [ImageReader(io.BytesIO(doc.load_page(i).get_pixmap(matrix=mat, alpha=False).tobytes("png")))
              for i in range(doc.page_count)]
    pages = _paginate(images, 8)

    page_w, page_h = landscape(letter)
    template_ir = _load_template_image(template_docx_or_pdf, options.dpi_template)

    c = canvas.Canvas(output_pdf, pagesize=(page_w, page_h))

    # hairline frame to force exact page size recognition by some printers
    c.saveState(); c.setStrokeGray(0.97); c.setLineWidth(0.1)
    c.rect(0.5, 0.5, page_w - 1, page_h - 1, stroke=1, fill=0)
    c.restoreState()

    slots = _build_slots(options)
    box_w = options.box_width_in * INCH
    box_h = options.box_height_in * INCH

    for batch in pages:
        if template_ir:
            c.drawImage(template_ir, 0, 0, width=page_w, height=page_h,
                        preserveAspectRatio=False, mask='auto')
        for img, (cx, cy) in zip(batch, slots):
            iw_px, ih_px = img.getSize()
            scale = min(box_w / iw_px, box_h / ih_px)
            dw = iw_px * scale
            dh = ih_px * scale

            c.saveState()
            c.translate(cx, cy)
            c.rotate(options.rotate_deg)
            c.drawImage(img, -dw/2, -dh/2, width=dw, height=dh,
                        preserveAspectRatio=False, mask='auto')
            c.restoreState()
        c.showPage()

    c.save()
