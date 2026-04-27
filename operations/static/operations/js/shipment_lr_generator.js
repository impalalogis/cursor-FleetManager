document.addEventListener("DOMContentLoaded", function () {
    const lrBtn = document.getElementById("generate-lr-btn");
    const lrInput = document.getElementById("id_lr_no");

    const invoiceBtn = document.getElementById("generate-invoice-no-btn");
    const invoiceInput = document.getElementById("id_invoice_no");

    function getShipmentIdFromUrl() {
        const pathParts = window.location.pathname.split("/").filter(Boolean);
        for (const part of pathParts) {
            if (/^\d+$/.test(part)) {
                return part;
            }
        }
        return "";
    }

    async function generateValue(btn, input, responseKey) {
        if (!btn || !input) return;

        const previewUrl = btn.getAttribute("data-preview-url");
        const shipmentId = getShipmentIdFromUrl();

        let url = previewUrl;
        if (shipmentId) {
            url += `?shipment_id=${shipmentId}`;
        }

        try {
            const response = await fetch(url, {
                method: "GET",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            if (!response.ok) {
                alert(`Failed to generate ${responseKey}.`);
                return;
            }

            const data = await response.json();
            if (data[responseKey]) {
                input.value = data[responseKey];
            } else {
                alert(`Could not generate ${responseKey}.`);
            }
        } catch (error) {
            console.error(error);
            alert(`Error while generating ${responseKey}.`);
        }
    }

    if (lrBtn && lrInput) {
        lrBtn.addEventListener("click", function () {
            generateValue(lrBtn, lrInput, "lr_no");
        });
    }

    if (invoiceBtn && invoiceInput) {
        invoiceBtn.addEventListener("click", function () {
            generateValue(invoiceBtn, invoiceInput, "invoice_no");
        });
    }
});