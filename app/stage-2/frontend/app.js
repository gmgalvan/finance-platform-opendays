const chartData = {
  "1S": {
    value: "+$820.10",
    change: "+0.45% durante la última semana",
    line: "M20 168 C95 150,135 178,205 142 S330 160,390 118 S520 130,585 82 S645 72,680 62",
    pointY: 62,
  },
  "1M": {
    value: "+$4,318.20",
    change: "+2.40% durante el último mes",
    line: "M20 180 C80 165,115 188,170 152 S265 132,320 145 S405 105,455 118 S545 75,595 92 S650 55,680 42",
    pointY: 42,
  },
  "3M": {
    value: "+$7,904.80",
    change: "+4.49% durante los últimos tres meses",
    line: "M20 188 C65 120,115 170,160 135 S245 182,300 126 S395 96,450 108 S535 55,600 76 S645 35,680 48",
    pointY: 48,
  },
  "1A": {
    value: "+$18,642.30",
    change: "+11.26% durante el último año",
    line: "M20 196 C75 185,105 156,155 172 S235 118,292 142 S380 85,430 108 S510 48,565 70 S635 28,680 32",
    pointY: 32,
  },
};

const savedUser = sessionStorage.getItem("finance-demo-user");

if (savedUser) {
  const user = JSON.parse(savedUser);
  document.querySelectorAll("[data-user-full-name]").forEach((element) => {
    element.textContent = user.name;
  });
  document.querySelectorAll("[data-user-first-name]").forEach((element) => {
    element.textContent = user.name.split(" ")[0];
  });

  fetch(`/api/dashboard?email=${encodeURIComponent(user.email)}`)
    .then((response) => (response.ok ? response.json() : Promise.reject(new Error("API no disponible"))))
    .then((result) => {
      sessionStorage.setItem("finance-demo-user", JSON.stringify(result.user));
    })
    .catch(() => {
      // El prototipo visual todavía puede abrirse con el servidor estático.
    });
}

const chartLine = document.querySelector("#chart-line");
const chartArea = document.querySelector("#chart-area");
const chartPoint = document.querySelector("#chart-point");
const chartValue = document.querySelector("#chart-value");
const chartChange = document.querySelector("#chart-change");

document.querySelectorAll("[data-period]").forEach((button) => {
  button.addEventListener("click", () => {
    const period = button.dataset.period;
    const data = chartData[period];

    document.querySelectorAll("[data-period]").forEach((item) => item.classList.remove("selected"));
    button.classList.add("selected");
    chartLine.setAttribute("d", data.line);
    chartArea.setAttribute("d", `${data.line} L680 205 L20 205 Z`);
    chartPoint.setAttribute("cy", data.pointY);
    chartValue.textContent = data.value;
    chartChange.textContent = data.change;
  });
});

document.querySelectorAll(".star").forEach((button) => {
  button.addEventListener("click", () => {
    const isActive = button.getAttribute("aria-pressed") === "true";
    const instrument = button.closest("tr").querySelector("th strong").textContent;

    button.setAttribute("aria-pressed", String(!isActive));
    button.classList.toggle("active", !isActive);
    button.textContent = isActive ? "☆" : "★";
    button.setAttribute("aria-label", `${isActive ? "Agregar" : "Quitar"} ${instrument} ${isActive ? "a" : "de"} favoritos`);
  });
});

document.querySelectorAll("[data-open-dialog]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(`#${button.dataset.openDialog}`).showModal();
  });
});

document.querySelectorAll("dialog").forEach((dialog) => {
  dialog.querySelector(".dialog-close").addEventListener("click", () => dialog.close());

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });
});
