(() => {
  "use strict";

  const state = {
    view: "overview",
    equipment: [],
    reservations: [],
    allReservations: [],
    stats: null,
    filters: { equipment_id: "", date: "", status: "" },
    confirmAction: null,
    loading: false,
  };

  const equipmentStatus = {
    available: ["可预约", "status-available"],
    maintenance: ["维护中", "status-maintenance"],
    retired: ["已停用", "status-retired"],
  };

  const reservationStatus = {
    booked: ["已预约", "status-booked"],
    in_use: ["使用中", "status-in_use"],
    completed: ["已完成", "status-completed"],
    cancelled: ["已取消", "status-cancelled"],
  };

  const viewMeta = {
    overview: ["今日工作台", "工作概览"],
    equipment: ["资产与时段", "设备管理"],
    reservations: ["安排与状态", "预约管理"],
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const icon = (name) => window.LucideIcons.icon(name);
  const escapeHtml = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  async function api(path, options = {}) {
    const response = await fetch(path, {
      headers: options.body ? { "Content-Type": "application/json" } : {},
      ...options,
    });
    let payload = {};
    try {
      payload = await response.json();
    } catch {
      payload = {};
    }
    if (!response.ok) {
      const error = new Error(payload.error?.message || "请求失败，请稍后重试");
      error.code = payload.error?.code;
      throw error;
    }
    return payload;
  }

  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type === "error" ? "error" : ""}`;
    toast.innerHTML = `${icon(type === "error" ? "circle-alert" : "circle-check")}<span>${escapeHtml(message)}</span>`;
    $("#toast-region").append(toast);
    window.setTimeout(() => toast.remove(), 4200);
  }

  function setBusy(busy) {
    state.loading = busy;
    $$(".modal button[type='submit']").forEach((button) => {
      button.disabled = busy;
    });
  }

  function localDateString() {
    const now = new Date();
    const offset = now.getTimezoneOffset() * 60_000;
    return new Date(now.getTime() - offset).toISOString().slice(0, 10);
  }

  function timeOptions(selected = "") {
    const options = [];
    for (let hour = 0; hour < 24; hour += 1) {
      for (const minute of ["00", "30"]) {
        const value = `${String(hour).padStart(2, "0")}:${minute}`;
        options.push(
          `<option value="${value}" ${value === selected ? "selected" : ""}>${value}</option>`,
        );
      }
    }
    return options.join("");
  }

  function populateTimeSelects() {
    [
      ["#equipment-opening-start", "08:00"],
      ["#equipment-opening-end", "18:00"],
      ["#reservation-start", "09:00"],
      ["#reservation-end", "10:00"],
    ].forEach(([selector, value]) => {
      $(selector).innerHTML = timeOptions(value);
    });
  }

  function switchView(view) {
    if (!viewMeta[view]) return;
    state.view = view;
    $$(".view").forEach((node) => {
      const active = node.id === `view-${view}`;
      node.hidden = !active;
      node.classList.toggle("is-active", active);
    });
    $$(".nav-item").forEach((node) => {
      node.classList.toggle("is-active", node.dataset.view === view);
    });
    $("#page-eyebrow").textContent = viewMeta[view][0];
    $("#page-title").textContent = viewMeta[view][1];
    closeSidebar();
    window.location.hash = view === "overview" ? "overview" : view;
  }

  function openSidebar() {
    $("#sidebar").classList.add("is-open");
    $("#sidebar-scrim").hidden = false;
  }

  function closeSidebar() {
    $("#sidebar").classList.remove("is-open");
    $("#sidebar-scrim").hidden = true;
  }

  function renderStats() {
    const stats = state.stats || {};
    $("#stat-equipment").textContent = stats.equipment_count ?? 0;
    $("#stat-active").textContent = stats.active_count ?? 0;
    $("#stat-completed").textContent = stats.completed_count ?? 0;
    $("#stat-cancelled").textContent = stats.cancelled_count ?? 0;
    $("#nav-equipment-count").textContent = state.equipment.length;
    $("#nav-reservation-count").textContent = state.allReservations.length;
  }

  function renderChart() {
    const rows = state.stats?.by_equipment || [];
    const max = Math.max(1, ...rows.map((row) => row.reservation_count || 0));
    if (!rows.length) {
      $("#bar-chart").innerHTML = `
        <div class="empty-state">
          <span>${icon("chart-no-axes-column")}</span>
          <h3>暂无设备统计</h3>
          <p>添加设备后，这里会显示预约分布。</p>
        </div>`;
      return;
    }
    $("#bar-chart").innerHTML = rows
      .map(
        (row) => `
          <div class="chart-row">
            <div class="chart-label">
              <strong title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</strong>
              <small>${escapeHtml(row.code)}</small>
            </div>
            <progress value="${Number(row.reservation_count) || 0}" max="${max}"></progress>
            <span class="chart-value">${Number(row.reservation_count) || 0}</span>
          </div>`,
      )
      .join("");
  }

  function renderSchedule() {
    const items = state.allReservations.slice(0, 5);
    if (!items.length) {
      $("#schedule-list").innerHTML = `
        <div class="empty-state">
          <span>${icon("calendar-days")}</span>
          <h3>暂无预约</h3>
          <p>创建预约后会显示在这里。</p>
        </div>`;
      return;
    }
    $("#schedule-list").innerHTML = items
      .map((item) => {
        const [, month, day] = item.date.split("-");
        const status = reservationStatus[item.status] || ["未知", ""];
        return `
          <div class="schedule-item">
            <span class="schedule-date">
              <span>${escapeHtml(day)}<small>${escapeHtml(Number(month))}月</small></span>
            </span>
            <div class="schedule-info">
              <strong>${escapeHtml(item.equipment_name)} · ${escapeHtml(item.requester)}</strong>
              <span>${escapeHtml(item.start_time)}-${escapeHtml(item.end_time)} · ${escapeHtml(item.equipment_code)}</span>
            </div>
            <span class="status-badge ${status[1]}">${status[0]}</span>
          </div>`;
      })
      .join("");
  }

  function renderEquipment() {
    const query = $("#equipment-search").value.trim().toLowerCase();
    const visible = state.equipment.filter((item) =>
      [item.code, item.name, item.location].some((value) =>
        String(value).toLowerCase().includes(query),
      ),
    );
    $("#equipment-result-count").textContent = `显示 ${visible.length} / ${state.equipment.length} 台设备`;
    if (!visible.length) {
      $("#equipment-grid").innerHTML = `
        <div class="empty-state table-panel equipment-empty">
          <span>${icon("monitor")}</span>
          <h3>${state.equipment.length ? "没有匹配的设备" : "还没有设备"}</h3>
          <p>${state.equipment.length ? "尝试更换搜索关键词。" : "添加第一台设备以开始预约。"}</p>
        </div>`;
      return;
    }
    $("#equipment-grid").innerHTML = visible
      .map((item) => {
        const status = equipmentStatus[item.status] || ["未知", ""];
        return `
          <article class="equipment-card" data-status="${escapeHtml(item.status)}">
            <div class="equipment-card-head">
              <div>
                <span class="equipment-code">${escapeHtml(item.code)}</span>
                <h3>${escapeHtml(item.name)}</h3>
              </div>
              <div class="card-actions">
                <button class="icon-button" type="button" data-action="edit-equipment" data-id="${escapeHtml(item.id)}" aria-label="编辑 ${escapeHtml(item.name)}" title="编辑设备">
                  ${icon("pencil")}
                </button>
                <button class="icon-button danger-button" type="button" data-action="delete-equipment" data-id="${escapeHtml(item.id)}" aria-label="删除 ${escapeHtml(item.name)}" title="删除设备">
                  ${icon("trash-2")}
                </button>
              </div>
            </div>
            <div class="equipment-meta">
              <div class="meta-row">${icon("map-pin")}<span>${escapeHtml(item.location)}</span></div>
              <div class="meta-row">${icon("clock")}<span>每日 ${escapeHtml(item.opening_start)}-${escapeHtml(item.opening_end)}</span></div>
              ${item.notes ? `<div class="notes-line" title="${escapeHtml(item.notes)}">${escapeHtml(item.notes)}</div>` : ""}
            </div>
            <div class="equipment-foot">
              <span class="status-badge ${status[1]}">${status[0]}</span>
              <span class="active-note">${Number(item.active_reservations) || 0} 条有效预约</span>
            </div>
          </article>`;
      })
      .join("");
  }

  function renderEquipmentOptions() {
    const filter = $("#filter-equipment");
    const currentFilter = state.filters.equipment_id;
    filter.innerHTML = `
      <option value="">全部设备</option>
      ${state.equipment
        .map(
          (item) =>
            `<option value="${escapeHtml(item.id)}">${escapeHtml(item.code)} · ${escapeHtml(item.name)}</option>`,
        )
        .join("")}`;
    filter.value = currentFilter;

    const reservationSelect = $("#reservation-equipment");
    const available = state.equipment.filter((item) => item.status === "available");
    reservationSelect.innerHTML = `
      <option value="">请选择设备</option>
      ${available
        .map(
          (item) =>
            `<option value="${escapeHtml(item.id)}">${escapeHtml(item.code)} · ${escapeHtml(item.name)}</option>`,
        )
        .join("")}`;
  }

  function actionMarkup(item) {
    if (item.status === "booked") {
      return `
        <button class="row-action" type="button" data-action="reservation-status" data-id="${escapeHtml(item.id)}" data-status="in_use">
          ${icon("play")}开始使用
        </button>
        <button class="row-action cancel" type="button" data-action="reservation-status" data-id="${escapeHtml(item.id)}" data-status="cancelled">
          ${icon("ban")}取消
        </button>`;
    }
    if (item.status === "in_use") {
      return `
        <button class="row-action" type="button" data-action="reservation-status" data-id="${escapeHtml(item.id)}" data-status="completed">
          ${icon("circle-check")}完成
        </button>`;
    }
    return '<span class="table-secondary">无可用操作</span>';
  }

  function renderReservations() {
    const items = state.reservations;
    const body = $("#reservation-table-body");
    $("#reservation-empty").hidden = items.length > 0;
    $("#reservation-table-wrap").hidden = items.length === 0;
    body.innerHTML = items
      .map((item) => {
        const status = reservationStatus[item.status] || ["未知", ""];
        return `
          <tr>
            <td>
              <span class="table-primary">${escapeHtml(item.equipment_name)}</span>
              <span class="table-secondary">${escapeHtml(item.equipment_code)}</span>
            </td>
            <td>
              <span class="table-primary">${escapeHtml(item.requester)}</span>
              ${item.notes ? `<span class="table-secondary" title="${escapeHtml(item.notes)}">${escapeHtml(item.notes)}</span>` : ""}
            </td>
            <td class="table-time">${escapeHtml(item.date)}</td>
            <td class="table-time">${escapeHtml(item.start_time)}-${escapeHtml(item.end_time)}</td>
            <td><span class="status-badge ${status[1]}">${status[0]}</span></td>
            <td>
              <div class="row-actions">${actionMarkup(item)}</div>
            </td>
          </tr>`;
      })
      .join("");
  }

  function renderAll() {
    renderStats();
    renderChart();
    renderSchedule();
    renderEquipment();
    renderEquipmentOptions();
    renderReservations();
  }

  async function loadAll() {
    setBusy(true);
    try {
      const [equipmentPayload, reservationPayload, statsPayload] = await Promise.all([
        api("/api/equipment"),
        api("/api/reservations"),
        api("/api/stats"),
      ]);
      state.equipment = equipmentPayload.items;
      state.allReservations = reservationPayload.items;
      state.stats = statsPayload.item;
      await loadFilteredReservations(false);
      renderAll();
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function loadFilteredReservations(render = true) {
    const params = new URLSearchParams();
    Object.entries(state.filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    const query = params.toString();
    const payload = await api(`/api/reservations${query ? `?${query}` : ""}`);
    state.reservations = payload.items;
    if (render) renderReservations();
  }

  function openEquipmentDialog(item = null) {
    const form = $("#equipment-form");
    form.reset();
    $("#equipment-id").value = item?.id || "";
    $("#equipment-dialog-title").textContent = item ? "编辑设备" : "添加设备";
    populateTimeSelects();
    if (item) {
      $("#equipment-code").value = item.code;
      $("#equipment-name").value = item.name;
      $("#equipment-location").value = item.location;
      $("#equipment-status").value = item.status;
      $("#equipment-opening-start").value = item.opening_start;
      $("#equipment-opening-end").value = item.opening_end;
      $("#equipment-notes").value = item.notes || "";
    }
    $("#equipment-dialog").showModal();
    window.setTimeout(() => $("#equipment-code").focus(), 40);
  }

  function nextTime(value, minutesToAdd = 60) {
    const [hours, minutes] = value.split(":").map(Number);
    const total = Math.min(hours * 60 + minutes + minutesToAdd, 23 * 60 + 30);
    return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  }

  function updateReservationAvailability() {
    const selected = state.equipment.find(
      (item) => item.id === $("#reservation-equipment").value,
    );
    if (!selected) {
      $("#reservation-availability").textContent = "";
      return;
    }
    $("#reservation-availability").textContent =
      `开放时段 ${selected.opening_start}-${selected.opening_end} · ${selected.location}`;
    $("#reservation-start").value = selected.opening_start;
    const proposedEnd = nextTime(selected.opening_start);
    $("#reservation-end").value =
      proposedEnd <= selected.opening_end ? proposedEnd : selected.opening_end;
  }

  function openReservationDialog(equipmentId = "") {
    renderEquipmentOptions();
    const available = state.equipment.filter((item) => item.status === "available");
    if (!available.length) {
      showToast("当前没有可预约设备，请先调整设备状态", "error");
      return;
    }
    $("#reservation-form").reset();
    $("#reservation-date").value = localDateString();
    const preferred = available.find((item) => item.id === equipmentId) || available[0];
    $("#reservation-equipment").value = preferred.id;
    updateReservationAvailability();
    $("#reservation-dialog").showModal();
    window.setTimeout(() => $("#reservation-requester").focus(), 40);
  }

  function askConfirm({ title, message, acceptLabel = "确认", danger = true, action }) {
    $("#confirm-title").textContent = title;
    $("#confirm-message").textContent = message;
    $("#confirm-accept").textContent = acceptLabel;
    $("#confirm-accept").className = `button ${danger ? "button-danger" : "button-primary"}`;
    state.confirmAction = action;
    $("#confirm-dialog").showModal();
  }

  async function runConfirmedAction() {
    const action = state.confirmAction;
    if (!action) return;
    state.confirmAction = null;
    $("#confirm-dialog").close();
    setBusy(true);
    try {
      await action();
      await loadAll();
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function submitEquipment(event) {
    event.preventDefault();
    if (state.loading) return;
    const id = $("#equipment-id").value;
    const payload = {
      code: $("#equipment-code").value.trim(),
      name: $("#equipment-name").value.trim(),
      location: $("#equipment-location").value.trim(),
      status: $("#equipment-status").value,
      opening_start: $("#equipment-opening-start").value,
      opening_end: $("#equipment-opening-end").value,
      notes: $("#equipment-notes").value.trim(),
    };
    setBusy(true);
    try {
      await api(id ? `/api/equipment/${encodeURIComponent(id)}` : "/api/equipment", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      $("#equipment-dialog").close();
      showToast(id ? "设备信息已更新" : "设备已添加");
      await loadAll();
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function submitReservation(event) {
    event.preventDefault();
    if (state.loading) return;
    const payload = {
      equipment_id: $("#reservation-equipment").value,
      requester: $("#reservation-requester").value.trim(),
      date: $("#reservation-date").value,
      start_time: $("#reservation-start").value,
      end_time: $("#reservation-end").value,
      notes: $("#reservation-notes").value.trim(),
    };
    setBusy(true);
    try {
      await api("/api/reservations", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      $("#reservation-dialog").close();
      showToast("预约已创建");
      await loadAll();
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function handleAction(button) {
    const action = button.dataset.action;
    const id = button.dataset.id;
    if (action === "new-reservation") {
      openReservationDialog();
      return;
    }
    if (action === "edit-equipment") {
      const item = state.equipment.find((equipment) => equipment.id === id);
      if (item) openEquipmentDialog(item);
      return;
    }
    if (action === "delete-equipment") {
      const item = state.equipment.find((equipment) => equipment.id === id);
      if (!item) return;
      askConfirm({
        title: "删除设备",
        message: `确定删除“${item.code} · ${item.name}”吗？设备的历史预约也会一并删除，操作无法撤销。`,
        acceptLabel: "删除",
        action: async () => {
          await api(`/api/equipment/${encodeURIComponent(id)}`, { method: "DELETE" });
          showToast("设备已删除");
        },
      });
      return;
    }
    if (action === "reservation-status") {
      const item = state.reservations.find((reservation) => reservation.id === id);
      if (!item) return;
      const target = button.dataset.status;
      const messages = {
        in_use: ["开始使用", `确认“${item.requester}”开始使用该设备吗？`],
        cancelled: ["取消预约", `确认取消 ${item.date} ${item.start_time}-${item.end_time} 的预约吗？`],
        completed: ["完成预约", "确认本次设备使用已经完成吗？"],
      };
      const [title, message] = messages[target] || ["更新状态", "确认更新预约状态吗？"];
      askConfirm({
        title,
        message,
        acceptLabel: title,
        danger: target === "cancelled",
        action: async () => {
          await api(`/api/reservations/${encodeURIComponent(id)}/status`, {
            method: "PATCH",
            body: JSON.stringify({ status: target }),
          });
          showToast(`预约状态已更新为${reservationStatus[target][0]}`);
        },
      });
    }
  }

  function bindEvents() {
    document.addEventListener("click", (event) => {
      const viewButton = event.target.closest("[data-view]");
      if (viewButton) {
        switchView(viewButton.dataset.view);
        return;
      }
      const closeButton = event.target.closest("[data-close-dialog]");
      if (closeButton) {
        closeButton.closest("dialog").close();
        return;
      }
      const actionButton = event.target.closest("[data-action]");
      if (actionButton) handleAction(actionButton);
    });

    $("#menu-button").addEventListener("click", openSidebar);
    $("#sidebar-scrim").addEventListener("click", closeSidebar);
    $("#refresh-button").addEventListener("click", loadAll);
    $("#add-equipment-button").addEventListener("click", () => openEquipmentDialog());
    $("#equipment-search").addEventListener("input", renderEquipment);
    $("#equipment-form").addEventListener("submit", submitEquipment);
    $("#reservation-form").addEventListener("submit", submitReservation);
    $("#reservation-equipment").addEventListener("change", updateReservationAvailability);
    $("#confirm-cancel").addEventListener("click", () => {
      state.confirmAction = null;
      $("#confirm-dialog").close();
    });
    $("#confirm-accept").addEventListener("click", runConfirmedAction);

    $("#reservation-filters").addEventListener("submit", async (event) => {
      event.preventDefault();
      state.filters = {
        equipment_id: $("#filter-equipment").value,
        date: $("#filter-date").value,
        status: $("#filter-status").value,
      };
      setBusy(true);
      try {
        await loadFilteredReservations();
      } catch (error) {
        showToast(error.message, "error");
      } finally {
        setBusy(false);
      }
    });

    $("#clear-filters").addEventListener("click", async () => {
      state.filters = { equipment_id: "", date: "", status: "" };
      $("#reservation-filters").reset();
      setBusy(true);
      try {
        await loadFilteredReservations();
      } catch (error) {
        showToast(error.message, "error");
      } finally {
        setBusy(false);
      }
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeSidebar();
    });
  }

  function init() {
    window.LucideIcons.hydrate();
    populateTimeSelects();
    $("#today-caption").textContent = new Intl.DateTimeFormat("zh-CN", {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "long",
    }).format(new Date());
    const initialView = window.location.hash.replace("#", "");
    if (viewMeta[initialView]) switchView(initialView);
    bindEvents();
    loadAll();
  }

  init();
})();
