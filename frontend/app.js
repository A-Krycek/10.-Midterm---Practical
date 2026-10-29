// Manejo de la aplicación Frontend para el acortador de URLs en AWS

(function () {
  // Elementos del DOM
  const form = document.getElementById("shorten-form");
  const urlInput = document.getElementById("url-input");
  const submitBtn = document.getElementById("submit-btn");
  const btnText = document.getElementById("btn-text");
  const btnSpinner = document.getElementById("btn-spinner");

  const alertBox = document.getElementById("alert-box");
  const resultBox = document.getElementById("result-box");
  const shortUrlLink = document.getElementById("short-url-link");
  const copyBtn = document.getElementById("copy-btn");
  const copyText = document.getElementById("copy-text");
  const copyIcon = document.getElementById("copy-icon");
  const resultUuid = document.getElementById("result-uuid");
  const resultOriginal = document.getElementById("result-original");
  const resultCreated = document.getElementById("result-created");

  const statusDot = document.getElementById("status-dot");
  const currentApiDisplay = document.getElementById("current-api-display");
  const toggleConfigBtn = document.getElementById("toggle-config-btn");
  const configPanel = document.getElementById("config-panel");
  const customApiInput = document.getElementById("custom-api-input");
  const saveConfigBtn = document.getElementById("save-config-btn");
  const resetConfigBtn = document.getElementById("reset-config-btn");

  const inspectForm = document.getElementById("inspect-form");
  const inspectCodeInput = document.getElementById("inspect-code-input");
  const jsonViewer = document.getElementById("json-viewer");

  const historySection = document.getElementById("history-section");
  const historyList = document.getElementById("history-list");
  const clearHistoryBtn = document.getElementById("clear-history-btn");

  // Obtener URL de API configurada
  function getApiBaseUrl() {
    const saved = localStorage.getItem("AWS_SHORTENER_API_URL");
    if (saved) return saved.trim().replace(/\/$/, "");
    if (typeof APP_CONFIG !== "undefined" && APP_CONFIG.API_BASE_URL) {
      return APP_CONFIG.API_BASE_URL.trim().replace(/\/$/, "");
    }
    return "http://localhost:8000";
  }

  function setApiBaseUrl(url) {
    const cleanUrl = url.trim().replace(/\/$/, "");
    localStorage.setItem("AWS_SHORTENER_API_URL", cleanUrl);
    updateApiDisplay();
    checkApiHealth();
  }

  function resetApiBaseUrl() {
    localStorage.removeItem("AWS_SHORTENER_API_URL");
    updateApiDisplay();
    checkApiHealth();
  }

  function updateApiDisplay() {
    const current = getApiBaseUrl();
    currentApiDisplay.textContent = current;
    customApiInput.value = current;
  }

  // Verificar estado del backend en EC2
  async function checkApiHealth() {
    const baseUrl = getApiBaseUrl();
    statusDot.className = "status-dot";
    try {
      const response = await fetch(`${baseUrl}/health`, { method: "GET", mode: "cors" });
      if (response.ok) {
        statusDot.className = "status-dot online";
        statusDot.title = "Backend EC2 Conectado";
      } else {
        statusDot.className = "status-dot";
        statusDot.title = "Respuesta no satisfactoria del backend";
      }
    } catch (e) {
      statusDot.className = "status-dot";
      statusDot.title = "No se puede conectar con el backend EC2";
    }
  }

  // Manejo de alertas
  function showAlert(message, type = "error") {
    alertBox.textContent = message;
    alertBox.className = `alert alert-${type}`;
    alertBox.style.display = "block";
    alertBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function hideAlert() {
    alertBox.style.display = "none";
    alertBox.textContent = "";
  }

  // Validación básica de URL
  function isValidHttpUrl(string) {
    try {
      const parsed = new URL(string);
      return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch (_) {
      return false;
    }
  }

  // Estado de carga del formulario
  function setLoading(isLoading) {
    if (isLoading) {
      submitBtn.disabled = true;
      btnSpinner.style.display = "inline-block";
      btnText.textContent = "Procesando...";
    } else {
      submitBtn.disabled = false;
      btnSpinner.style.display = "none";
      btnText.textContent = "Acortar URL";
    }
  }

  // Guardar en historial local
  function saveToHistory(item) {
    let history = [];
    try {
      history = JSON.parse(localStorage.getItem("AWS_SHORTENER_HISTORY") || "[]");
    } catch (e) {
      history = [];
    }
    history.unshift(item);
    if (history.length > 8) history = history.slice(0, 8);
    localStorage.setItem("AWS_SHORTENER_HISTORY", JSON.stringify(history));
    renderHistory();
  }

  function renderHistory() {
    let history = [];
    try {
      history = JSON.parse(localStorage.getItem("AWS_SHORTENER_HISTORY") || "[]");
    } catch (e) {
      history = [];
    }

    if (history.length === 0) {
      historySection.style.display = "none";
      return;
    }

    historySection.style.display = "block";
    historyList.innerHTML = "";

    history.forEach((entry) => {
      const itemEl = document.createElement("div");
      itemEl.className = "history-item";
      itemEl.innerHTML = `
        <div class="history-info">
          <a class="history-short" href="${entry.short_url}" target="_blank" rel="noopener noreferrer">${entry.short_url}</a>
          <span class="history-orig" title="${entry.original_url}">Destino: ${entry.original_url}</span>
        </div>
        <button class="btn-secondary" style="padding: 0.3rem 0.6rem; font-size: 0.75rem;" onclick="navigator.clipboard.writeText('${entry.short_url}')">Copiar</button>
      `;
      historyList.appendChild(itemEl);
    });
  }

  // Evento submit: Acortar enlace (POST /shorten)
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();

    const originalUrl = urlInput.value.trim();

    if (!isValidHttpUrl(originalUrl)) {
      showAlert("Por favor ingresa una URL válida que comience con http:// o https://");
      return;
    }

    setLoading(true);
    const apiUrl = `${getApiBaseUrl()}/shorten`;

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({ original_url: originalUrl })
      });

      if (!response.ok) {
        let errorMsg = `Error en el servidor (HTTP ${response.status})`;
        try {
          const errData = await response.json();
          if (errData && errData.detail) {
            errorMsg = Array.isArray(errData.detail)
              ? errData.detail.map((d) => d.msg || d).join(", ")
              : errData.detail;
          }
        } catch (_) {}
        throw new Error(errorMsg);
      }

      const data = await response.json();

      // Mostrar resultados
      shortUrlLink.href = data.short_url;
      shortUrlLink.textContent = data.short_url;
      resultUuid.textContent = data.short_code;
      resultOriginal.textContent = data.original_url;
      resultCreated.textContent = new Date().toLocaleString();

      resultBox.style.display = "block";
      resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });

      // Guardar en historial
      saveToHistory(data);

      // Sugerir UUID en el formulario de inspección
      inspectCodeInput.value = data.short_code;

    } catch (err) {
      console.error("Error al acortar:", err);
      showAlert(
        `No fue posible comunicarse con el backend: ${err.message}. Verifica que el Security Group de EC2 permita tráfico en el puerto y que CORS esté habilitado.`
      );
    } finally {
      setLoading(false);
    }
  });

  // Copiar al portapapeles
  copyBtn.addEventListener("click", async () => {
    const textToCopy = shortUrlLink.textContent;
    if (!textToCopy) return;

    try {
      await navigator.clipboard.writeText(textToCopy);
      copyText.textContent = "¡Copiado!";
      copyIcon.textContent = "✅";
      copyBtn.classList.add("copied");

      setTimeout(() => {
        copyText.textContent = "Copiar";
        copyIcon.textContent = "📋";
        copyBtn.classList.remove("copied");
      }, 2000);
    } catch (e) {
      // Fallback
      const tempInput = document.createElement("input");
      tempInput.value = textToCopy;
      document.body.appendChild(tempInput);
      tempInput.select();
      document.execCommand("copy");
      document.body.removeChild(tempInput);

      copyText.textContent = "¡Copiado!";
      setTimeout(() => {
        copyText.textContent = "Copiar";
      }, 2000);
    }
  });

  // Evento submit: Consultar enlace (GET /urls/{short_code})
  inspectForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const shortCode = inspectCodeInput.value.trim();
    if (!shortCode) return;

    jsonViewer.style.display = "block";
    jsonViewer.textContent = "Consultando registro en DynamoDB...";

    const apiUrl = `${getApiBaseUrl()}/urls/${encodeURIComponent(shortCode)}`;

    try {
      const response = await fetch(apiUrl);
      if (response.status === 404) {
        jsonViewer.textContent = `HTTP 404 Not Found: El enlace con UUID '${shortCode}' no existe en DynamoDB.`;
        return;
      }
      if (!response.ok) {
        jsonViewer.textContent = `Error HTTP ${response.status}: No se pudo consultar la información.`;
        return;
      }

      const data = await response.json();
      jsonViewer.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      jsonViewer.textContent = `Error de red: ${err.message}. Comprueba que el backend esté accesible.`;
    }
  });

  // Limpiar historial
  clearHistoryBtn.addEventListener("click", () => {
    localStorage.removeItem("AWS_SHORTENER_HISTORY");
    renderHistory();
  });

  // Toggle panel configuración
  toggleConfigBtn.addEventListener("click", () => {
    configPanel.classList.toggle("active");
  });

  saveConfigBtn.addEventListener("click", () => {
    const newUrl = customApiInput.value;
    if (newUrl) {
      setApiBaseUrl(newUrl);
      configPanel.classList.remove("active");
      showAlert("Dirección de la API actualizada.", "success");
      setTimeout(hideAlert, 3000);
    }
  });

  resetConfigBtn.addEventListener("click", () => {
    resetApiBaseUrl();
    configPanel.classList.remove("active");
    showAlert("Dirección de la API restablecida a la configuración por defecto.", "success");
    setTimeout(hideAlert, 3000);
  });

  // Inicialización
  updateApiDisplay();
  checkApiHealth();
  renderHistory();
})();
