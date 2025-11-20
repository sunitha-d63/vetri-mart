document.addEventListener("DOMContentLoaded", () => {

    const qtyInputs = document.querySelectorAll(".quantity");

    qtyInputs.forEach(input => {
        input.addEventListener("change", function () {

            let qty = parseInt(this.value);
            if (qty < 1) qty = 1;
            this.value = qty;

            const card = this.closest(".cart-row");

            const unitPrice = parseFloat(card.querySelector(".unit-price").value);
            const weightMult = parseFloat(card.querySelector(".weight-mult").value);

            const rowId = this.dataset.id;  // guest index OR cart item ID

            const priceElement = document.getElementById(`price-${rowId}`);

            const finalPrice = (unitPrice * weightMult * qty);
            priceElement.innerText = finalPrice.toFixed(2);

            updateTotals();

            // -------------------------------------------
            // UPDATE SERVER FOR LOGGED-IN USERS
            // -------------------------------------------
            if (!card.closest(".col-lg-8").classList.contains("guest-cart")) {
                fetch(`/update-cart-qty/${rowId}/${qty}/`)
                    .then(response => response.json())
                    .then(data => {
                        console.log("Updated cart", data);
                    });
            }

        });
    });

    function updateTotals() {
        let subtotal = 0;

        document.querySelectorAll(".cart-price span").forEach(price => {
            subtotal += parseFloat(price.innerText);
        });

        const tax = subtotal * 0.05;
        const total = subtotal + tax;

        document.getElementById("subtotal").innerText = subtotal.toFixed(2);
        document.getElementById("tax").innerText = tax.toFixed(2);
        document.getElementById("total").innerText = total.toFixed(2);
    }

});
