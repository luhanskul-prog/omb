document.addEventListener("DOMContentLoaded", function () {

    const memberType = document.getElementById("id_member_type");
    const lookupNumber = document.getElementById("id_lookup_number");
    const personDetails = document.getElementById("id_person_details");

    if (!memberType || !lookupNumber || !personDetails) {
        return;
    }

    // Create LOAD DETAILS button
    const button = document.createElement("button");

    button.type = "button";
    button.textContent = "LOAD DETAILS";
    button.style.marginLeft = "10px";
    button.style.padding = "8px 16px";
    button.style.backgroundColor = "#0d6efd";
    button.style.color = "white";
    button.style.border = "0";
    button.style.borderRadius = "5px";
    button.style.cursor = "pointer";
    button.style.fontWeight = "bold";

    lookupNumber.parentNode.appendChild(button);

    function loadDetails() {

        const type = memberType.value;
        const number = lookupNumber.value.trim();

        if (!type) {
            personDetails.value = "Please select Student or Staff.";
            return;
        }

        if (!number) {
            personDetails.value =
                "Please enter an admission number or employee number.";
            return;
        }

        personDetails.value = "Loading...";

        fetch(
            "/library/admin/member-lookup/?member_type="
            + encodeURIComponent(type)
            + "&number="
            + encodeURIComponent(number)
        )
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {

            if (data.success) {

                personDetails.value = data.details;
                personDetails.style.color = "#198754";

            } else {

                personDetails.value = data.message;
                personDetails.style.color = "#dc3545";

            }

        })
        .catch(function (error) {

            console.error(error);

            personDetails.value =
                "Could not load details. Please check the number.";

            personDetails.style.color = "#dc3545";
        });
    }

    button.addEventListener("click", loadDetails);

    lookupNumber.addEventListener("keydown", function (event) {

        if (event.key === "Enter") {
            event.preventDefault();
            loadDetails();
        }

    });

});