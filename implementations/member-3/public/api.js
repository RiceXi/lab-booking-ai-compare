'use strict';

(function () {
  const EQUIPMENT_STATUS_MAP = {
    available: '可预约',
    maintenance: '维护中',
    retired: '已停用'
  };

  const RESERVATION_STATUS_MAP = {
    booked: '已预约',
    in_use: '使用中',
    completed: '已完成',
    cancelled: '已取消'
  };

  function escapeHtml(str) {
    return String(str === undefined || str === null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getTodayLocalStr() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function buildTimeSlots(includeEnd24) {
    const slots = [];
    for (let h = 0; h < 24; h += 1) {
      const hh = String(h).padStart(2, '0');
      slots.push(`${hh}:00`);
      slots.push(`${hh}:30`);
    }
    if (includeEnd24) {
      slots.push('24:00');
    }
    return slots;
  }

  function calcDurationHours(startStr, endStr) {
    const [sh, sm] = startStr.split(':').map(Number);
    const [eh, em] = endStr.split(':').map(Number);
    const mins = eh * 60 + em - (sh * 60 + sm);
    return mins > 0 ? Number((mins / 60).toFixed(1)) : 0;
  }

  async function requestJson(url, options) {
    const opts = Object.assign({ headers: {} }, options || {});
    if (opts.body && typeof opts.body === 'object') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    const resp = await fetch(url, opts);
    const payload = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const msg = (payload.error && payload.error.message) || `请求失败 (${resp.status})`;
      const err = new Error(msg);
      err.code = payload.error && payload.error.code;
      throw err;
    }
    return payload;
  }

  window.LabHelper = {
    EQUIPMENT_STATUS_MAP,
    RESERVATION_STATUS_MAP,
    escapeHtml,
    getTodayLocalStr,
    buildTimeSlots,
    calcDurationHours,
    requestJson
  };
})();
