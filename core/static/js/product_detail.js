document.addEventListener("DOMContentLoaded", () => {

    const weightSelector = document.getElementById("weightSelector");
    const dropdown = document.getElementById("weightDropdown");
    const weightSelect = document.getElementById("selectedWeight");
    const weightText = document.getElementById("selectedWeightText");

    const qtyInput = document.getElementById("quantityInput");
    const priceBox = document.getElementById("livePrice");

    const basePrice = parseFloat(document.getElementById("basePrice").value);
    const discountPrice = parseFloat(document.getElementById("discountPrice").value);
    const unit = document.getElementById("productUnit").value.toLowerCase();
    const offerActive = document.getElementById("isOfferActive").value === "True";

    function convertWeight(value) {
        const w = value.toUpperCase().trim();

        // KG / G
        if (unit === "kg") {
            if (w.endsWith("KG")) return parseFloat(w);
            if (w.endsWith("G")) return parseFloat(w) / 1000;
        }

        // Litre / ML
        if (unit === "litre") {
            if (w.endsWith("L")) return parseFloat(w);
            if (w.endsWith("ML")) return parseFloat(w) / 1000;
        }

        // Piece
        if (unit === "piece") return parseInt(w);

        // Pack
        if (unit === "pack") return 1;

        // Dozen
        if (unit === "dozen") return parseInt(w) * 12;

        return 1;
    }

    function updatePrice() {
        const selectedWeight = weightText.innerText.trim();
        const qty = parseInt(qtyInput.value);

        const multiplier = convertWeight(selectedWeight);
        const pricePerUnit = offerActive ? discountPrice : basePrice;

        const total = pricePerUnit * multiplier * qty;

        priceBox.innerText = "₹" + total.toFixed(2);
    }

    // Toggle dropdown
    weightSelector.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.classList.toggle("d-none");
    });

    // Select option
    dropdown.querySelectorAll("li").forEach(li => {
        li.addEventListener("click", function (e) {
            e.stopPropagation();
            const val = this.getAttribute("data-value");

            weightText.textContent = val;
            weightSelect.value = val;

            dropdown.classList.add("d-none");
            updatePrice();
        });
    });

    // Close dropdown on outside click
    document.addEventListener("click", () => {
        dropdown.classList.add("d-none");
    });

    qtyInput.addEventListener("input", updatePrice);

    updatePrice();
});
