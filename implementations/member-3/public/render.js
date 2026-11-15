'use strict';

(function () {
  const {
    EQUIPMENT_STATUS_MAP,
    RESERVATION_STATUS_MAP,
    escapeHtml,
    calcDurationHours
  } = window.LabHelper;

  function renderKpis(stats, health) {
    document.getElementById('kpiTotalEquipments').textContent = stats.total_equipments;
    const eqCounts = stats.equipment_status_counts || {};
    document.getElementById('kpiEquipmentMeta').textContent =
      `可预约 ${eqCounts.available || 0} · 维护中 ${eqCounts.maintenance || 0} · 已停用 ${eqCounts.retired || 0}`;

    document.getElementById('kpiActiveReservations').textContent = stats.active_reservations;
    const resCounts = stats.reservation_status_counts || {};
    document.getElementById('kpiActiveMeta').textContent =
      `已预约 ${resCounts.booked || 0} · 使用中 ${resCounts.in_use || 0}`;

    document.getElementById('kpiCompletedReservations').textContent = stats.completed_reservations;
    document.getElementById('kpiCompletedMeta').textContent =
      `非取消有效累计 ${stats.non_cancelled_reservations || 0} 条`;

    document.getElementById('kpiCancelledReservations').textContent = stats.cancelled_reservations;
    document.getElementById('kpiCancelledMeta').textContent =
      `历史总记录 ${stats.total_reservations || 0} 条`;

    if (health && health.dataFile) {
      document.getElementById('dataFileHint').textContent = `本地持久化文件：${health.dataFile}`;
    }
  }

  function renderEquipmentSelects(equipments, selectedResEqId, selectedFilterEqId) {
    const resSelect = document.getElementById('resEquipmentId');
    const filterSelect = document.getElementById('filterEquipment');

    if (equipments.length === 0) {
      resSelect.innerHTML = '<option value="">-- 请先在“设备管理”页添加设备 --</option>';
    } else {
      resSelect.innerHTML = ['<option value="">-- 请选择预约设备 --</option>']
        .concat(
          equipments.map((eq) => {
            const st = EQUIPMENT_STATUS_MAP[eq.status] || eq.status;
            const suffix = eq.status !== 'available' ? ` [${st} - 禁止新预约]` : ` [${eq.opening_start}-${eq.opening_end}]`;
            return `<option value="${escapeHtml(eq.id)}">${escapeHtml(eq.code)} · ${escapeHtml(eq.name)}${escapeHtml(suffix)}</option>`;
          })
        )
        .join('');
      if (selectedResEqId && equipments.some((e) => e.id === selectedResEqId)) {
        resSelect.value = selectedResEqId;
      }
    }

    filterSelect.innerHTML = ['<option value="">全部设备</option>']
      .concat(
        equipments.map(
          (eq) => `<option value="${escapeHtml(eq.id)}">${escapeHtml(eq.code)} · ${escapeHtml(eq.name)}</option>`
        )
      )
      .join('');
    if (selectedFilterEqId) {
      filterSelect.value = selectedFilterEqId;
    }
  }

  function renderReservationsTable(reservations) {
    const tbody = document.getElementById('reservationTableBody');
    document.getElementById('reservationCountBadge').textContent = `共 ${reservations.length} 条记录`;

    if (reservations.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty-cell">当前筛选条件下暂无预约记录</td></tr>';
      return;
    }

    tbody.innerHTML = reservations
      .map((r) => {
        const statusLabel = RESERVATION_STATUS_MAP[r.status] || r.status;
        const hrs = calcDurationHours(r.start_time, r.end_time);
        let actionsHtml = '<span class="sub-line">终态</span>';

        if (r.status === 'booked') {
          actionsHtml = `
            <div class="row-actions">
              <button type="button" class="btn btn-sm btn-warning" data-action="res-status" data-id="${escapeHtml(r.id)}" data-next="in_use">开始使用</button>
              <button type="button" class="btn btn-sm btn-danger-outline" data-action="res-cancel" data-id="${escapeHtml(r.id)}">取消预约</button>
            </div>
          `;
        } else if (r.status === 'in_use') {
          actionsHtml = `
            <div class="row-actions">
              <button type="button" class="btn btn-sm btn-success" data-action="res-status" data-id="${escapeHtml(r.id)}" data-next="completed">完成使用</button>
            </div>
          `;
        }

        return `
          <tr>
            <td>
              <div><strong>${escapeHtml(r.equipment_name)}</strong></div>
              <div class="sub-line"><span class="code-mono">${escapeHtml(r.equipment_code)}</span> · ${escapeHtml(r.equipment_location)}</div>
            </td>
            <td><strong>${escapeHtml(r.requester)}</strong></td>
            <td>${escapeHtml(r.date)}</td>
            <td>
              <div class="code-mono">${escapeHtml(r.start_time)} - ${escapeHtml(r.end_time)}</div>
              <div class="sub-line">${hrs} 小时</div>
            </td>
            <td><span class="badge badge-${escapeHtml(r.status)}">${escapeHtml(statusLabel)}</span></td>
            <td>${r.notes ? escapeHtml(r.notes) : '<span class="text-muted">-</span>'}</td>
            <td>${actionsHtml}</td>
          </tr>
        `;
      })
      .join('');
  }

  function renderEquipmentsTable(equipments) {
    const tbody = document.getElementById('equipmentTableBody');
    document.getElementById('equipmentCountBadge').textContent = `共 ${equipments.length} 台设备`;

    if (equipments.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty-cell">暂无设备，请在左侧表单添加设备</td></tr>';
      return;
    }

    tbody.innerHTML = equipments
      .map((eq) => {
        const statusLabel = EQUIPMENT_STATUS_MAP[eq.status] || eq.status;
        return `
          <tr>
            <td class="code-mono">${escapeHtml(eq.code)}</td>
            <td>
              <div><strong>${escapeHtml(eq.name)}</strong></div>
              ${eq.notes ? `<div class="sub-line">${escapeHtml(eq.notes)}</div>` : ''}
            </td>
            <td>${escapeHtml(eq.location)}</td>
            <td><span class="badge badge-${escapeHtml(eq.status)}">${escapeHtml(statusLabel)}</span></td>
            <td class="code-mono">${escapeHtml(eq.opening_start)} - ${escapeHtml(eq.opening_end)}</td>
            <td>${eq.active_reservation_count || 0} 条</td>
            <td>
              <div class="row-actions">
                <button type="button" class="btn btn-sm btn-ghost" data-action="eq-detail" data-id="${escapeHtml(eq.id)}">详情</button>
                <button type="button" class="btn btn-sm btn-ghost" data-action="eq-book" data-id="${escapeHtml(eq.id)}">去预约</button>
                <button type="button" class="btn btn-sm btn-ghost" data-action="eq-edit" data-id="${escapeHtml(eq.id)}">编辑</button>
                <button type="button" class="btn btn-sm btn-danger-outline" data-action="eq-delete" data-id="${escapeHtml(eq.id)}">删除</button>
              </div>
            </td>
          </tr>
        `;
      })
      .join('');
  }

  function renderStatsTable(perEquipment) {
    const tbody = document.getElementById('statsEquipmentTableBody');
    if (!perEquipment || perEquipment.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty-cell">暂无统计数据</td></tr>';
      return;
    }
    tbody.innerHTML = perEquipment
      .map((item) => {
        const statusLabel = EQUIPMENT_STATUS_MAP[item.status] || item.status;
        return `
          <tr>
            <td class="code-mono">${escapeHtml(item.code)}</td>
            <td><strong>${escapeHtml(item.name)}</strong></td>
            <td>${escapeHtml(item.location)}</td>
            <td><span class="badge badge-${escapeHtml(item.status)}">${escapeHtml(statusLabel)}</span></td>
            <td>${item.active_count}</td>
            <td>${item.completed_count}</td>
            <td><strong>${item.reservation_count}</strong></td>
            <td>${item.cancelled_count}</td>
            <td><strong>${item.total_hours}</strong></td>
          </tr>
        `;
      })
      .join('');
  }

  function renderEquipmentDetailModal(detail) {
    const statusLabel = EQUIPMENT_STATUS_MAP[detail.status] || detail.status;
    const rows = (detail.reservations || [])
      .map((r) => {
        const rl = RESERVATION_STATUS_MAP[r.status] || r.status;
        return `
          <tr>
            <td>${escapeHtml(r.date)}</td>
            <td class="code-mono">${escapeHtml(r.start_time)} - ${escapeHtml(r.end_time)}</td>
            <td>${escapeHtml(r.requester)}</td>
            <td><span class="badge badge-${escapeHtml(r.status)}">${escapeHtml(rl)}</span></td>
            <td>${r.notes ? escapeHtml(r.notes) : '-'}</td>
          </tr>
        `;
      })
      .join('');

    document.getElementById('equipmentDetailContent').innerHTML = `
      <div class="detail-grid">
        <div><div class="detail-item-label">系统唯一 ID</div><div class="detail-item-value code-mono">${escapeHtml(detail.id)}</div></div>
        <div><div class="detail-item-label">设备编号</div><div class="detail-item-value code-mono">${escapeHtml(detail.code)}</div></div>
        <div><div class="detail-item-label">设备名称</div><div class="detail-item-value">${escapeHtml(detail.name)}</div></div>
        <div><div class="detail-item-label">存放位置</div><div class="detail-item-value">${escapeHtml(detail.location)}</div></div>
        <div><div class="detail-item-label">当前状态</div><div class="detail-item-value"><span class="badge badge-${escapeHtml(detail.status)}">${escapeHtml(statusLabel)}</span></div></div>
        <div><div class="detail-item-label">每日开放时段</div><div class="detail-item-value code-mono">${escapeHtml(detail.opening_start)} - ${escapeHtml(detail.opening_end)}</div></div>
        <div><div class="detail-item-label">创建时间</div><div class="detail-item-value small-text">${escapeHtml(detail.created_at)}</div></div>
        <div><div class="detail-item-label">更新时间</div><div class="detail-item-value small-text">${escapeHtml(detail.updated_at)}</div></div>
        <div style="grid-column: 1 / -1;"><div class="detail-item-label">备注说明</div><div class="detail-item-value">${detail.notes ? escapeHtml(detail.notes) : '无'}</div></div>
      </div>
      <h4 style="margin: 0 0 10px;">关联预约记录（共 ${(detail.reservations || []).length} 条）</h4>
      <div class="table-wrapper">
        <table class="data-table">
          <thead><tr><th>日期</th><th>时间区间</th><th>预约人</th><th>状态</th><th>备注</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="5" class="empty-cell">该设备暂无预约记录</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }

  window.LabRender = {
    renderKpis,
    renderEquipmentSelects,
    renderReservationsTable,
    renderEquipmentsTable,
    renderStatsTable,
    renderEquipmentDetailModal
  };
})();
