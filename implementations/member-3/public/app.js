'use strict';

(function () {
  const {
    EQUIPMENT_STATUS_MAP,
    RESERVATION_STATUS_MAP,
    escapeHtml,
    getTodayLocalStr,
    buildTimeSlots,
    requestJson
  } = window.LabHelper;
  const {
    renderKpis,
    renderEquipmentSelects,
    renderReservationsTable,
    renderEquipmentsTable,
    renderStatsTable,
    renderEquipmentDetailModal
  } = window.LabRender;
  const { renderEquipmentBarChart, renderStatusDonutChart } = window.LabCharts;

  const state = {
    equipments: [],
    reservations: [],
    stats: null,
    health: null,
    chartMetric: 'count',
    filters: { equipment_id: '', date: '', status: '', requester: '' }
  };

  function showGlobalAlert(message, type) {
    const banner = document.getElementById('globalAlert');
    document.getElementById('globalAlertText').textContent = message;
    banner.className = `alert-banner ${type || 'success'}`;
  }

  function showFormError(elId, message) {
    const el = document.getElementById(elId);
    if (!message) {
      el.classList.add('hidden');
      el.textContent = '';
      return;
    }
    el.textContent = message;
    el.classList.remove('hidden');
  }

  function switchTab(tabName) {
    document.querySelectorAll('.nav-tab').forEach((btn) => {
      const active = btn.dataset.tab === tabName;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-selected', String(active));
    });
    document.querySelectorAll('.tab-panel').forEach((panel) => {
      panel.classList.toggle('active', panel.id === `tab-${tabName}`);
    });
  }

  function populateTimeDropdowns() {
    const startSlots = buildTimeSlots(false);
    const endSlots = buildTimeSlots(true);
    const fill = (id, list, defVal) => {
      const sel = document.getElementById(id);
      sel.innerHTML = list.map((t) => `<option value="${t}">${t}</option>`).join('');
      sel.value = defVal;
    };
    fill('resStartTime', startSlots, '09:00');
    fill('resEndTime', endSlots, '10:00');
    fill('eqOpeningStart', startSlots, '08:00');
    fill('eqOpeningEnd', endSlots, '22:00');
  }

  async function updateDayOccupancyPreview() {
    const eqId = document.getElementById('resEquipmentId').value;
    const dateVal = document.getElementById('resDate').value;
    const hintEl = document.getElementById('selectedEquipmentHint');
    const listEl = document.getElementById('dayOccupancyList');

    const eq = state.equipments.find((e) => e.id === eqId);
    if (!eq) {
      hintEl.textContent = '请选择要预约的实验室设备';
      listEl.innerHTML = '<span class="text-muted">选择设备与日期后显示当日占用情况</span>';
      return;
    }

    const stLabel = EQUIPMENT_STATUS_MAP[eq.status] || eq.status;
    hintEl.textContent = `位置：${eq.location} · 状态：${stLabel} · 每日开放：${eq.opening_start}-${eq.opening_end}`;

    if (!dateVal) {
      listEl.innerHTML = '<span class="text-muted">请选择预约日期</span>';
      return;
    }

    try {
      const q = new URLSearchParams({ equipment_id: eqId, date: dateVal });
      const res = await requestJson(`/api/reservations?${q.toString()}`);
      const active = (res.data || []).filter((r) => r.status === 'booked' || r.status === 'in_use');
      if (active.length === 0) {
        listEl.innerHTML = '<span class="text-muted">该日期暂无有效预约占用，开放时段内均可预约</span>';
      } else {
        listEl.innerHTML = active
          .map((r) => {
            const rl = RESERVATION_STATUS_MAP[r.status] || r.status;
            return `<span class="slot-pill">${escapeHtml(r.start_time)}-${escapeHtml(r.end_time)} · ${escapeHtml(r.requester)} (${escapeHtml(rl)})</span>`;
          })
          .join('');
      }
    } catch (_) {
      listEl.innerHTML = '<span class="text-muted">暂无法获取占用预览</span>';
    }
  }

  async function refreshAll() {
    const selectedResEq = document.getElementById('resEquipmentId').value;
    const q = new URLSearchParams();
    Object.entries(state.filters).forEach(([k, v]) => {
      if (v) q.set(k, v);
    });

    const [eqResp, resResp, statsResp, healthResp] = await Promise.all([
      requestJson('/api/equipments'),
      requestJson(`/api/reservations?${q.toString()}`),
      requestJson('/api/stats'),
      requestJson('/api/health')
    ]);

    state.equipments = eqResp.data || [];
    state.reservations = resResp.data || [];
    state.stats = statsResp.data;
    state.health = healthResp;

    renderKpis(state.stats, state.health);
    renderEquipmentSelects(state.equipments, selectedResEq, state.filters.equipment_id);
    renderReservationsTable(state.reservations);
    renderEquipmentsTable(state.equipments);
    renderStatsTable(state.stats.per_equipment);
    renderEquipmentBarChart(document.getElementById('equipmentBarChart'), state.stats.per_equipment, state.chartMetric);
    renderStatusDonutChart(document.getElementById('statusDonutChart'), state.stats.reservation_status_counts);
    await updateDayOccupancyPreview();
  }

  function resetEquipmentForm() {
    document.getElementById('eqEditId').value = '';
    document.getElementById('equipmentForm').reset();
    document.getElementById('eqOpeningStart').value = '08:00';
    document.getElementById('eqOpeningEnd').value = '22:00';
    document.getElementById('equipmentFormTitle').textContent = '添加实验室设备';
    document.getElementById('eqSubmitBtn').textContent = '保存新设备';
    document.getElementById('cancelEditEquipmentBtn').classList.add('hidden');
    showFormError('equipmentFormError', '');
  }

  function bindEvents() {
    document.querySelectorAll('.nav-tab').forEach((btn) => {
      btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    document.getElementById('globalAlertClose').addEventListener('click', () => {
      document.getElementById('globalAlert').classList.add('hidden');
    });

    document.getElementById('resEquipmentId').addEventListener('change', updateDayOccupancyPreview);
    document.getElementById('resDate').addEventListener('change', updateDayOccupancyPreview);

    document.getElementById('reservationForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      showFormError('reservationFormError', '');
      try {
        const body = {
          equipment_id: document.getElementById('resEquipmentId').value,
          requester: document.getElementById('resRequester').value,
          date: document.getElementById('resDate').value,
          start_time: document.getElementById('resStartTime').value,
          end_time: document.getElementById('resEndTime').value,
          notes: document.getElementById('resNotes').value
        };
        await requestJson('/api/reservations', { method: 'POST', body });
        document.getElementById('resNotes').value = '';
        showGlobalAlert('预约创建成功！', 'success');
        await refreshAll();
      } catch (err) {
        showFormError('reservationFormError', err.message);
        showGlobalAlert(err.message, 'error');
      }
    });

    document.getElementById('filterForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      state.filters = {
        equipment_id: document.getElementById('filterEquipment').value,
        date: document.getElementById('filterDate').value,
        status: document.getElementById('filterStatus').value,
        requester: document.getElementById('filterRequester').value.trim()
      };
      await refreshAll();
    });

    document.getElementById('resetFilterBtn').addEventListener('click', async () => {
      document.getElementById('filterForm').reset();
      state.filters = { equipment_id: '', date: '', status: '', requester: '' };
      await refreshAll();
    });

    document.getElementById('reservationTableBody').addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-action]');
      if (!btn) return;
      const id = btn.dataset.id;
      try {
        if (btn.dataset.action === 'res-cancel') {
          await requestJson(`/api/reservations/${encodeURIComponent(id)}/cancel`, { method: 'POST' });
          showGlobalAlert('预约已取消，对应时段已释放', 'success');
        } else if (btn.dataset.action === 'res-status') {
          await requestJson(`/api/reservations/${encodeURIComponent(id)}/status`, {
            method: 'PATCH',
            body: { status: btn.dataset.next }
          });
          showGlobalAlert('预约状态更新成功', 'success');
        }
        await refreshAll();
      } catch (err) {
        showGlobalAlert(err.message, 'error');
      }
    });

    document.getElementById('equipmentForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      showFormError('equipmentFormError', '');
      const editId = document.getElementById('eqEditId').value;
      const body = {
        code: document.getElementById('eqCode').value,
        name: document.getElementById('eqName').value,
        location: document.getElementById('eqLocation').value,
        status: document.getElementById('eqStatus').value,
        opening_start: document.getElementById('eqOpeningStart').value,
        opening_end: document.getElementById('eqOpeningEnd').value,
        notes: document.getElementById('eqNotes').value
      };
      try {
        if (editId) {
          await requestJson(`/api/equipments/${encodeURIComponent(editId)}`, { method: 'PUT', body });
          showGlobalAlert('设备信息更新成功', 'success');
        } else {
          await requestJson('/api/equipments', { method: 'POST', body });
          showGlobalAlert('新设备添加成功', 'success');
        }
        resetEquipmentForm();
        await refreshAll();
      } catch (err) {
        showFormError('equipmentFormError', err.message);
        showGlobalAlert(err.message, 'error');
      }
    });

    document.getElementById('cancelEditEquipmentBtn').addEventListener('click', resetEquipmentForm);

    document.getElementById('equipmentTableBody').addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-action]');
      if (!btn) return;
      const id = btn.dataset.id;
      const eq = state.equipments.find((item) => item.id === id);
      if (!eq) return;

      if (btn.dataset.action === 'eq-book') {
        switchTab('reservations');
        document.getElementById('resEquipmentId').value = eq.id;
        await updateDayOccupancyPreview();
      } else if (btn.dataset.action === 'eq-edit') {
        document.getElementById('eqEditId').value = eq.id;
        document.getElementById('eqCode').value = eq.code;
        document.getElementById('eqName').value = eq.name;
        document.getElementById('eqLocation').value = eq.location;
        document.getElementById('eqStatus').value = eq.status;
        document.getElementById('eqOpeningStart').value = eq.opening_start;
        document.getElementById('eqOpeningEnd').value = eq.opening_end;
        document.getElementById('eqNotes').value = eq.notes || '';
        document.getElementById('equipmentFormTitle').textContent = `编辑设备：${eq.code}`;
        document.getElementById('eqSubmitBtn').textContent = '保存修改';
        document.getElementById('cancelEditEquipmentBtn').classList.remove('hidden');
        showFormError('equipmentFormError', '');
      } else if (btn.dataset.action === 'eq-detail') {
        try {
          const resp = await requestJson(`/api/equipments/${encodeURIComponent(id)}`);
          renderEquipmentDetailModal(resp.data);
          document.getElementById('equipmentDetailModal').classList.remove('hidden');
        } catch (err) {
          showGlobalAlert(err.message, 'error');
        }
      } else if (btn.dataset.action === 'eq-delete') {
        try {
          await requestJson(`/api/equipments/${encodeURIComponent(id)}`, { method: 'DELETE' });
          if (document.getElementById('eqEditId').value === id) resetEquipmentForm();
          showGlobalAlert(`设备 "${eq.name}" 已成功删除`, 'success');
          await refreshAll();
        } catch (err) {
          showGlobalAlert(err.message, 'error');
        }
      }
    });

    document.getElementById('closeDetailModalBtn').addEventListener('click', () => {
      document.getElementById('equipmentDetailModal').classList.add('hidden');
    });
    document.getElementById('equipmentDetailModal').addEventListener('click', (e) => {
      if (e.target.id === 'equipmentDetailModal') {
        e.currentTarget.classList.add('hidden');
      }
    });

    document.querySelectorAll('.seg-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.chartMetric = btn.dataset.metric;
        document.querySelectorAll('.seg-btn').forEach((b) => b.classList.toggle('active', b === btn));
        if (state.stats) {
          renderEquipmentBarChart(
            document.getElementById('equipmentBarChart'),
            state.stats.per_equipment,
            state.chartMetric
          );
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    populateTimeDropdowns();
    document.getElementById('resDate').value = getTodayLocalStr();
    bindEvents();
    try {
      await refreshAll();
    } catch (err) {
      showGlobalAlert(`初始化加载失败：${err.message}`, 'error');
    }
  });
})();
