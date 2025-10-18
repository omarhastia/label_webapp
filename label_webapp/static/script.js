const $ = (sel) => document.querySelector(sel);
const barcodesDrop = $("#barcodesDrop");
const barcodesInput = $("#barcodesInput");
const templateDrop = $("#templateDrop");
const templateInput = $("#templateInput");
const runBtn = $("#runBtn");
const statusBox = $("#status");
const downloadLink = $("#downloadLink");


let barcodesFile = null;
let templateFile = null;


function enableRun() {
runBtn.disabled = !barcodesFile;
}


function bindDropzone(zone, input, onFile) {
zone.addEventListener("click", () => input.click());
zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag"); });
zone.addEventListener("dragleave", () => zone.classList.remove("drag"));
zone.addEventListener("drop", (e) => {
e.preventDefault(); zone.classList.remove("drag");
const f = e.dataTransfer.files[0]; if (f) { onFile(f); }
});
input.addEventListener("change", () => { const f = input.files[0]; if (f) onFile(f); });
}


bindDropzone(barcodesDrop, barcodesInput, (f) => {
if (!f.name.toLowerCase().endsWith(".pdf")) { alert("Barcodes must be a PDF."); return; }
barcodesFile = f; $("#barcodesInfo").textContent = `${f.name} (${(f.size/1024/1024).toFixed(2)} MB)`;
enableRun();
});


bindDropzone(templateDrop, templateInput, (f) => {
const ok = f.name.toLowerCase().endsWith(".pdf") || f.name.toLowerCase().endsWith(".docx");
if (!ok) { alert("Template must be PDF or DOCX."); return; }
templateFile = f; $("#templateInfo").textContent = `${f.name} (${(f.size/1024/1024).toFixed(2)} MB)`;
});


runBtn.addEventListener("click", async () => {
statusBox.classList.remove("hidden");
statusBox.textContent = "Processing… hold your horses.";
downloadLink.classList.add("hidden");


const fd = new FormData();
fd.append("barcodes", barcodesFile);
if (templateFile) fd.append("template", templateFile);
fd.append("rotate_deg", $("#rotate").value);
fd.append("left_x_in", $("#leftX").value);
fd.append("right_x_in", $("#rightX").value);
fd.append("row_centers_in", $("#rows").value);
fd.append("box_width_in", $("#boxW").value);
fd.append("box_height_in", $("#boxH").value);
fd.append("dpi_barcode", $("#dpiB").value);
fd.append("dpi_template", $("#dpiT").value);
fd.append("fill_order", $("#fillOrder").value);


try {
const resp = await fetch("/api/process", { method: "POST", body: fd });
if (!resp.ok) {
const err = await resp.json().catch(() => ({}));
statusBox.textContent = `Error: ${err.error || resp.statusText}\n${err.details || ""}`;
return;
}
const blob = await resp.blob();
const url = URL.createObjectURL(blob);
downloadLink.href = url;
downloadLink.classList.remove("hidden");
statusBox.textContent = "Done. If the labels are crooked, blame geometry.";
} catch (e) {
statusBox.textContent = `Client error: ${e}`;
}
});