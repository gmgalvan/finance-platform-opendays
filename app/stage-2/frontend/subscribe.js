const form = document.querySelector("#signup-form");
const steps = [...document.querySelectorAll("[data-step]")];
const indicators = [...document.querySelectorAll("[data-step-indicator]")];
const topicsError = document.querySelector("#topics-error");
const termsError = document.querySelector("#terms-error");

function showStep(stepNumber) {
  steps.forEach((step) => {
    step.hidden = Number(step.dataset.step) !== stepNumber;
  });

  indicators.forEach((indicator) => {
    const indicatorStep = Number(indicator.dataset.stepIndicator);
    indicator.classList.toggle("current", indicatorStep === stepNumber);
    indicator.classList.toggle("complete", indicatorStep < stepNumber);
  });

  const heading = document.querySelector(`[data-step="${stepNumber}"] h2`);
  heading.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function validateAccount() {
  const fields = [...form.querySelectorAll('[data-step="1"] input')];
  let isValid = true;

  fields.forEach((field) => {
    const fieldValid = field.checkValidity();
    field.setAttribute("aria-invalid", String(!fieldValid));
    if (!fieldValid) {
      field.reportValidity();
      isValid = false;
    }
  });

  return isValid;
}

function selectedTopics() {
  return [...form.querySelectorAll('input[name="topics"]:checked')].map((input) => input.value);
}

function populateReview() {
  const data = new FormData(form);
  document.querySelector('[data-review="name"]').textContent = data.get("name");
  document.querySelector('[data-review="email"]').textContent = data.get("email");
  document.querySelector('[data-review="topics"]').textContent = selectedTopics().join(", ");
}

document.querySelectorAll("[data-next]").forEach((button) => {
  button.addEventListener("click", () => {
    const nextStep = Number(button.dataset.next);

    if (nextStep === 2 && !validateAccount()) {
      return;
    }

    if (nextStep === 3) {
      const topics = selectedTopics();
      topicsError.hidden = topics.length > 0;
      if (topics.length === 0) {
        topicsError.focus();
        return;
      }
      populateReview();
    }

    showStep(nextStep);
  });
});

document.querySelectorAll("[data-back]").forEach((button) => {
  button.addEventListener("click", () => showStep(Number(button.dataset.back)));
});

document.querySelector(".password-toggle").addEventListener("click", (event) => {
  const button = event.currentTarget;
  const password = form.elements.password;
  const shouldShow = password.type === "password";

  password.type = shouldShow ? "text" : "password";
  button.textContent = shouldShow ? "Ocultar" : "Ver";
  button.setAttribute("aria-label", shouldShow ? "Ocultar contraseña" : "Mostrar contraseña");
  button.setAttribute("aria-pressed", String(shouldShow));
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!form.elements.terms.checked) {
    termsError.hidden = false;
    form.elements.terms.focus();
    return;
  }

  termsError.hidden = true;
  const data = new FormData(form);
  const payload = {
    name: data.get("name").trim(),
    email: data.get("email").trim(),
    password: data.get("password"),
    topics: selectedTopics(),
    newsletter: data.get("newsletter") === "on",
  };

  const submitButton = form.querySelector(".submit-button");
  const originalLabel = submitButton.textContent;
  submitButton.disabled = true;
  submitButton.textContent = "Creando cuenta…";

  try {
    const response = await window.tracedFetch("Suscribirse", "/api/subscriptions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "No fue posible crear la cuenta");
    }

    sessionStorage.setItem("finance-demo-user", JSON.stringify(result.user));
    form.hidden = true;
    document.querySelector(".stepper").hidden = true;
    document.querySelector("[data-success-name]").textContent = result.user.name.split(" ")[0];
    document.querySelector("#success-state").hidden = false;
    document.querySelector("#success-title").focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (error) {
    termsError.hidden = false;
    termsError.textContent = `${error.message}. Inicia la aplicación con “make stage-2-up”.`;
    termsError.focus();
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = originalLabel;
  }
});
