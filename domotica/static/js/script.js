let currentDevices = {};
let currentRole = null;

function fetchState() {
  fetch("/api/state")
    .then((r) => r.json())
    .then((data) => {
      currentDevices = data.devices;
      currentRole = data.role;
      document.getElementById("username").textContent = data.user;
      document.getElementById("role").textContent = data.role;

      renderDevices(data.devices);
      renderSensors(data.sensors);
      renderEvents(data.events);
    })
    .catch((err) => console.error("Error al obtener estado:", err));
}

function renderDevices(devices) {
  const container = document.getElementById("devices");
  container.innerHTML = "";
  Object.keys(devices).forEach((name) => {
    const state = devices[name];
    const card = document.createElement("div");
    card.className = "device-card " + (state ? "on" : "off");

    const title = document.createElement("div");
    title.className = "device-name";
    title.textContent = name;

    const st = document.createElement("div");
    st.className = "device-state";
    st.textContent = state ? "ENCENDIDO" : "APAGADO";

    const btnToggle = document.createElement("button");
    btnToggle.className =
      "btn-toggle " + (state ? "btn-toggle-on" : "btn-toggle-off");
    btnToggle.textContent = state ? "Apagar" : "Encender";
    btnToggle.onclick = () => toggleDevice(name, !state);

    card.appendChild(title);
    card.appendChild(st);
    card.appendChild(btnToggle);

    // 🔴 Botón Eliminar SOLO para admin
    if (currentRole === "admin") {
      const btnDelete = document.createElement("button");
      btnDelete.className = "btn-delete";
      btnDelete.textContent = "Eliminar";
      btnDelete.onclick = () => deleteDevice(name);
      card.appendChild(btnDelete);
    }

    container.appendChild(card);
  });
}


function renderSensors(sensors) {
  document.getElementById("sensor-temperatura").textContent = sensors.temperatura;
  document.getElementById("sensor-movimiento").textContent = sensors.movimiento ? "Detectado" : "No";
  document.getElementById("sensor-puerta").textContent = sensors.puerta_abierta ? "Abierta" : "Cerrada";
  document.getElementById("sensor-humo").textContent = sensors.humo ? "Humo detectado" : "Normal";
}

function renderEvents(events) {
  const tbody = document.getElementById("events-body");
  tbody.innerHTML = "";
  events.forEach((ev) => {
    const tr = document.createElement("tr");
    const td1 = document.createElement("td");
    const td2 = document.createElement("td");
    const td3 = document.createElement("td");
    const td4 = document.createElement("td");
    const td5 = document.createElement("td");

    td1.textContent = ev.timestamp;
    td2.textContent = ev.user;
    td3.textContent = ev.action;
    td4.textContent = ev.device || "";
    td5.textContent = ev.extra || "";

    tr.appendChild(td1);
    tr.appendChild(td2);
    tr.appendChild(td3);
    tr.appendChild(td4);
    tr.appendChild(td5);
    tbody.appendChild(tr);
  });
}

function toggleDevice(device, state) {
  fetch("/api/toggle", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ device, state }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        alert("Error: " + data.error);
      } else {
        fetchState();
      }
    })
    .catch((err) => console.error("Error al cambiar dispositivo:", err));
}

function setMode(mode) {
  fetch("/api/mode", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ mode }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        alert("Error: " + data.error);
      } else {
        fetchState();
      }
    })
    .catch((err) => console.error("Error al cambiar modo:", err));
}

function refreshEvents() {
  fetch("/api/events?limit=50")
    .then((r) => r.json())
    .then((data) => {
      renderEvents(data.events);
    })
    .catch((err) => console.error("Error al actualizar eventos:", err));
}

function addDevice() {
  const nameInput = document.getElementById("new-device-name");
  const name = nameInput.value.trim();
  if (!name) {
    alert("Ingresá un nombre de dispositivo");
    return;
  }
  fetch("/api/admin/add_device", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        alert("Error: " + data.error);
      } else {
        nameInput.value = "";
        fetchState();
      }
    })
    .catch((err) => console.error("Error al agregar dispositivo:", err));
}

function deleteDevice(name) {
  const seguro = confirm(
    `¿Seguro que querés eliminar el dispositivo "${name}"?`
  );
  if (!seguro) return;

  fetch("/api/admin/delete_device", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        alert("Error: " + data.error);
      } else {
        fetchState(); // recargar lista de dispositivos
      }
    })
    .catch((err) => console.error("Error al eliminar dispositivo:", err));
}


// Actualizar estado cada 2 segundos (dashboard "en tiempo real")
setInterval(fetchState, 2000);
window.onload = fetchState;
