from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
import os, tempfile, traceback
from labels import process_labels, LabelOptions

app = Flask(__name__, static_url_path="", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB limit

ALLOWED_PDF = {".pdf"}
ALLOWED_DOCX = {".docx"}


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.post("/api/process")
def process():
    try:
        if "barcodes" not in request.files:
            return jsonify({"error": "Missing barcodes PDF"}), 400

        barcodes_file = request.files["barcodes"]
        template_file = request.files.get("template")

        # create a temp directory to process files
        with tempfile.TemporaryDirectory() as td:
            bc_name = secure_filename(barcodes_file.filename or "barcodes.pdf")
            bc_path = os.path.join(td, bc_name)
            barcodes_file.save(bc_path)

            template_path = None
            if template_file and template_file.filename:
                tpl_name = secure_filename(template_file.filename)
                template_path = os.path.join(td, tpl_name)
                template_file.save(template_path)

            # user options
            opts = LabelOptions(
                rotate_deg=float(request.form.get("rotate_deg", 90)),
                left_x_in=float(request.form.get("left_x_in", 5.1)),
                right_x_in=float(request.form.get("right_x_in", 10.1)),
                row_centers_in=[
                    float(x)
                    for x in (
                        request.form.get("row_centers_in") or "7.4,5.4,3.4,1.4"
                    ).split(",")
                ],
                box_width_in=float(request.form.get("box_width_in", 1.75)),
                box_height_in=float(request.form.get("box_height_in", 2.50)),
                dpi_barcode=int(request.form.get("dpi_barcode", 300)),
                dpi_template=int(request.form.get("dpi_template", 300)),
                fill_order=(request.form.get("fill_order") or "zigzag")
                .strip()
                .lower(),
            )

            # process the file
            out_path = os.path.join(td, "labels_ready_ol8250_OVERLAY.pdf")
            process_labels(
                input_pdf=bc_path,
                output_pdf=out_path,
                template_docx_or_pdf=template_path,
                options=opts,
            )

            # send the result
            return send_file(out_path, as_attachment=True, download_name="labels_ready.pdf")

    except Exception:
        traceback.print_exc()
        return jsonify(
            {"error": "Processing failed.", "details": traceback.format_exc()}
        ), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
