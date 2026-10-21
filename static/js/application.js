document.addEventListener("DOMContentLoaded", () => {
    const logoutDialog = document.querySelector("#logout-confirmation");
    const logoutConfirmButton = logoutDialog?.querySelector("[data-confirm-logout]");
    const logoutCancelButton = logoutDialog?.querySelector("[data-cancel-logout]");
    let logoutFormToSubmit = null;

    document.querySelectorAll(".logout-form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!logoutDialog) return;
            event.preventDefault();
            logoutFormToSubmit = form;
            logoutDialog.showModal();
            logoutCancelButton?.focus();
        });
    });

    logoutCancelButton?.addEventListener("click", () => {
        logoutDialog.close();
        logoutFormToSubmit = null;
    });

    logoutConfirmButton?.addEventListener("click", () => {
        const form = logoutFormToSubmit;
        logoutDialog.close();
        logoutFormToSubmit = null;
        if (form) HTMLFormElement.prototype.submit.call(form);
    });

    document.querySelectorAll('input[type="password"]').forEach((input) => {
        const control = document.createElement("div");
        control.className = "password-control";
        const button = document.createElement("button");
        button.type = "button";
        button.className = "toggle-password";
        button.textContent = "Afficher";
        button.setAttribute("aria-label", "Afficher le mot de passe");
        button.setAttribute("aria-pressed", "false");
        input.parentNode.insertBefore(control, input);
        control.append(input, button);
        button.addEventListener("click", () => {
            const afficher = input.type === "password";
            input.type = afficher ? "text" : "password";
            button.textContent = afficher ? "Masquer" : "Afficher";
            button.setAttribute("aria-label", `${afficher ? "Masquer" : "Afficher"} le mot de passe`);
            button.setAttribute("aria-pressed", String(afficher));
            input.focus();
        });
    });

    const drawer = document.querySelector("#mobile-more-panel");
    const openButton = document.querySelector("[data-open-more]");
    const scrim = document.querySelector(".drawer-scrim");
    const closeButtons = document.querySelectorAll("[data-close-more]");

    if (drawer && openButton && scrim) {
        const closeDrawer = (restoreFocus = false) => {
            drawer.dataset.open = "false";
            drawer.setAttribute("aria-hidden", "true");
            drawer.inert = true;
            openButton.setAttribute("aria-expanded", "false");
            scrim.dataset.visible = "false";
            document.body.classList.remove("drawer-open");
            if (restoreFocus) openButton.focus();
        };

        const openDrawer = () => {
            drawer.dataset.open = "true";
            drawer.setAttribute("aria-hidden", "false");
            drawer.inert = false;
            openButton.setAttribute("aria-expanded", "true");
            scrim.dataset.visible = "true";
            document.body.classList.add("drawer-open");
            drawer.querySelector(".drawer-close")?.focus();
        };

        openButton.addEventListener("click", () => {
            if (drawer.dataset.open === "true") closeDrawer(true);
            else openDrawer();
        });
        closeButtons.forEach((button) => {
            button.addEventListener("click", () => closeDrawer(button !== scrim));
        });
        drawer.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => closeDrawer());
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && drawer.dataset.open === "true") {
                closeDrawer(true);
            }
            if (event.key === "Tab" && drawer.dataset.open === "true") {
                const focusable = [...drawer.querySelectorAll("a, button")];
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                if (event.shiftKey && document.activeElement === first) {
                    event.preventDefault();
                    last.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault();
                    first.focus();
                }
            }
        });
    }

    const clientSelect = document.querySelector(
        'select[name="client"][data-biens-url]'
    );
    const bienSelect = document.querySelector('select[name="bien"]');

    if (clientSelect && bienSelect) {
        let requeteActive = 0;
        const bienInitial = bienSelect.value;

        const chargerBiens = async (conserverSelection = false) => {
            const requete = ++requeteActive;
            const clientId = clientSelect.value;
            bienSelect.disabled = true;
            bienSelect.replaceChildren(
                new Option(
                    clientId ? "Chargement des biens…" : "Choisissez d’abord un client",
                    ""
                )
            );

            if (!clientId) return;

            try {
                const url = new URL(clientSelect.dataset.biensUrl, window.location.origin);
                url.searchParams.set("client", clientId);
                const response = await fetch(url, {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                if (!response.ok) throw new Error("Chargement indisponible");

                const resultat = await response.json();
                if (requete !== requeteActive) return;

                const biens = resultat.biens || [];
                bienSelect.replaceChildren(
                    new Option(
                        biens.length ? "Sélectionnez un bien" : "Aucun bien disponible pour ce client",
                        ""
                    )
                );
                biens.forEach((bien) => {
                    const option = new Option(bien.label, String(bien.id));
                    if (conserverSelection && String(bienInitial) === option.value) {
                        option.selected = true;
                    }
                    bienSelect.add(option);
                });
                bienSelect.disabled = biens.length === 0;
            } catch {
                if (requete !== requeteActive) return;
                bienSelect.replaceChildren(new Option("Impossible de charger les biens", ""));
            }
        };

        clientSelect.addEventListener("change", () => chargerBiens());
        chargerBiens(true);
    }

    const typeSelect = document.querySelector('select[name="type"]');
    const capitalField = document.querySelector('input[name="capital_verse"]');
    if (!typeSelect || !capitalField) return;

    const capitalRow = capitalField.closest(".form-field");
    const actualiserChamps = () => {
        const acompte = typeSelect.value === "acompte";
        capitalRow.hidden = !acompte;
        capitalField.required = acompte;
    };
    typeSelect.addEventListener("change", actualiserChamps);
    actualiserChamps();
});