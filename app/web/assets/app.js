"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const form = byId("statement-form");
  const fileInput = byId("statement-file");
  const dropZone = byId("drop-zone");
  const year = byId("tax-year");
  const panel = byId("result-panel");
  const generate = byId("generate-button");
  const example = byId("load-example");
  const download = byId("download-button");
  const reset = byId("start-over");
  const maxBytes = 10 * 1024 * 1024;
  let selectedFile = null;
  let pdfUrl = null;
  let busy = false;
  let loadingExample = false;
  let selectionVersion = 0;
  let timer = null;

  const sizeLabel = (bytes) =>
    bytes >= 1024 * 1024
      ? `${(bytes / (1024 * 1024)).toFixed(1)} MiB`
      : `${Math.max(1, Math.ceil(bytes / 1024))} KiB`;

  function discardOutput() {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    pdfUrl = null;
    download.removeAttribute("href");
    download.hidden = true;
    reset.hidden = true;
    byId("error-box").hidden = true;
    byId("sign-in-link").hidden = true;
    byId("processing-time").hidden = true;
  }

  function showState(state, title, description, badge) {
    panel.dataset.state = state;
    byId("result-title").textContent = title;
    byId("result-description").textContent = description;
    byId("result-badge").textContent = badge;
  }

  function showError(message, status) {
    discardOutput();
    showState(
      "error",
      "Let’s try that again.",
      "Your report has not been saved. Check the details below.",
      "Needs attention",
    );
    byId("error-description").textContent = message;
    byId("error-box").hidden = false;
    byId("sign-in-link").hidden = status !== 401;
    panel.scrollIntoView({ block: "nearest" });
  }

  function updateForm() {
    generate.disabled = busy || !selectedFile || !year.value;
    fileInput.disabled = busy;
    year.disabled = busy;
    example.disabled =
      busy ||
      loadingExample ||
      !Array.from(year.options).some((option) => option.value === "2025");
    byId("remove-file").disabled = busy;
    form.classList.toggle("is-processing", busy);
    form.setAttribute("aria-busy", String(busy));
    byId("generate-label").textContent = busy
      ? "Generating your statement…"
      : "Generate tax statement";
    byId("generate-icon").textContent = busy ? "" : "↗";
    byId("paper-year").textContent = selectedFile ? year.value : "—";
  }

  function selectFile(file) {
    if (busy || !file) return;
    selectionVersion += 1;
    discardOutput();
    selectedFile = null;
    fileInput.value = "";
    byId("selected-file").hidden = true;
    if (!/\.xml$/i.test(file.name)) {
      showError(
        "Choose an IBKR Flex XML export. PDF, CSV and other file formats are not supported.",
      );
    } else if (file.size === 0) {
      showError(
        "This file is empty. Export your full calendar-year Flex report and try again.",
      );
    } else if (file.size > maxBytes) {
      showError(
        "This file exceeds the 10 MiB upload limit. Choose a smaller Flex XML report.",
      );
    } else {
      selectedFile = file;
      byId("file-name").textContent = file.name;
      byId("file-size").textContent =
        `${sizeLabel(file.size)} · Ready to upload`;
      byId("selected-file").hidden = false;
      showState(
        "ready",
        "Your report is lined up.",
        "Confirm the tax year, then generate your statement.",
        "Ready to generate",
      );
    }
    updateForm();
  }

  function clearWorkspace() {
    if (busy) return;
    selectionVersion += 1;
    selectedFile = null;
    fileInput.value = "";
    byId("selected-file").hidden = true;
    discardOutput();
    showState(
      "empty",
      "Ready when you are.",
      "Your broker data, in a Swiss tax-statement format. Upload a supported export to get started.",
      "Awaiting report",
    );
    updateForm();
  }

  fileInput.addEventListener("change", () => selectFile(fileInput.files[0]));
  byId("remove-file").addEventListener("click", clearWorkspace);
  reset.addEventListener("click", () => {
    clearWorkspace();
    fileInput.focus();
  });
  year.addEventListener("change", () => {
    selectionVersion += 1;
    discardOutput();
    if (selectedFile)
      showState(
        "ready",
        "Your report is lined up.",
        "Confirm the tax year, then generate your statement.",
        "Ready to generate",
      );
    updateForm();
  });
  ["dragenter", "dragover"].forEach((eventName) =>
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (!busy) dropZone.classList.add("drag-over");
    }),
  );
  ["dragleave", "drop"].forEach((eventName) =>
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("drag-over");
    }),
  );
  dropZone.addEventListener("drop", (event) => {
    if (busy) return;
    if (event.dataTransfer.files.length !== 1) {
      showError("Choose one Flex XML report at a time.");
      return;
    }
    selectFile(event.dataTransfer.files[0]);
  });
  // Avoid navigating away and opening a financial file dropped outside the target.
  window.addEventListener("dragover", (event) => event.preventDefault());
  window.addEventListener("drop", (event) => event.preventDefault());

  example.addEventListener("click", async () => {
    if (busy || loadingExample) return;
    loadingExample = true;
    const requestVersion = selectionVersion;
    updateForm();
    try {
      const response = await fetch("/assets/ibkr-synthetic-2025.xml", {
        cache: "no-store",
        redirect: "error",
      });
      if (!response.ok) throw new Error("example unavailable");
      const content = await response.blob();
      if (busy || selectionVersion !== requestVersion) return;
      year.value = "2025";
      selectFile(
        new File([content], "ibkr-synthetic-2025.xml", {
          type: "application/xml",
        }),
      );
      byId("result-description").textContent =
        "Fictional account, tax year 2025. Generate it to explore the complete workflow.";
    } catch {
      if (!busy && selectionVersion === requestVersion)
        showError(
          "The example could not be loaded. Try again or choose your own Flex XML export.",
        );
    } finally {
      loadingExample = false;
      updateForm();
    }
  });

  async function responseError(response) {
    if (response.status === 401)
      return "Your sign-in session has expired. Sign in again, then retry your upload.";
    if (response.status === 403)
      return "This account does not have access. Sign in with an authorized account.";
    const fallback = {
      413: "The upload is too large. Use an XML file no larger than 10 MiB.",
      429: "Too many requests. Wait a moment before trying again.",
      502: "The service is starting or temporarily unavailable. Wait a moment and retry.",
      503: "The service is busy or reference data is unavailable. Wait a moment and retry.",
      504: "Processing took too long. Wait a moment and retry your report.",
    };
    try {
      const body = await response.json();
      if (typeof body.detail === "string") return body.detail;
      if (Array.isArray(body.detail))
        return "Check the selected tax year and choose a valid Flex XML file.";
    } catch {
      /* Azure may return an HTML error instead of the API's JSON. */
    }
    return (
      fallback[response.status] ||
      "The report could not be processed. Check your export and try again."
    );
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy || !selectedFile || !year.value) return;
    discardOutput();
    const submittedYear = year.value;
    const data = new FormData();
    data.append("statement", selectedFile, selectedFile.name);
    data.append("tax_year", submittedYear);
    busy = true;
    updateForm();
    showState(
      "processing",
      "Putting it all together.",
      "Please keep this page open while your report is validated and your PDF is generated.",
      "Processing",
    );
    panel.scrollIntoView({ block: "nearest" });
    const started = Date.now();
    const elapsed = byId("processing-time");
    elapsed.hidden = false;
    elapsed.textContent =
      "Elapsed: 0 seconds · this can take up to two minutes";
    timer = window.setInterval(() => {
      elapsed.textContent = `Elapsed: ${Math.floor((Date.now() - started) / 1000)} seconds · this can take up to two minutes`;
    }, 1000);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 180000);
    try {
      const response = await fetch("/v1/statements", {
        method: "POST",
        body: data,
        cache: "no-store",
        credentials: "same-origin",
        redirect: "error",
        signal: controller.signal,
      });
      if (!response.ok) {
        showError(await responseError(response), response.status);
        return;
      }
      if (
        !response.headers
          .get("Content-Type")
          ?.toLowerCase()
          .startsWith("application/pdf")
      ) {
        showError(
          "The service returned an unexpected response. Your session may have expired; sign in and try again.",
          401,
        );
        return;
      }
      const pdf = await response.blob();
      if (pdf.size === 0) throw new Error("empty PDF");
      pdfUrl = URL.createObjectURL(pdf);
      download.href = pdfUrl;
      download.download = `steuerauszug-${submittedYear}.pdf`;
      download.hidden = false;
      reset.hidden = false;
      elapsed.hidden = true;
      showState(
        "success",
        "Your statement is ready.",
        `Tax year ${submittedYear} · ${sizeLabel(pdf.size)}. Download and review your PDF.`,
        "Ready to download",
      );
    } catch (error) {
      showError(
        error.name === "AbortError"
          ? "The connection timed out. Processing may still be finishing. Wait a moment before retrying."
          : "We couldn’t reach the service. Check your connection and sign-in session, then try again.",
      );
    } finally {
      window.clearInterval(timer);
      window.clearTimeout(timeout);
      busy = false;
      updateForm();
    }
  });

  window.addEventListener("pagehide", () => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
  });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) clearWorkspace();
  });
  document
    .querySelector('a[href="#limitations"]')
    .addEventListener("click", () => {
      byId("limitations").open = true;
    });
  if (!year.options.length)
    showError(
      "No supported tax year is configured. Ask the administrator to configure reference data.",
    );
  updateForm();
})();
