'use strict';

(function () {
  function escapeXml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /**
   * 渲染各设备预约次数 / 累计使用时长原生 SVG 柱状图
   */
  function renderEquipmentBarChart(container, perEquipment, metric) {
    if (!container) return;
    if (!Array.isArray(perEquipment) || perEquipment.length === 0) {
      container.innerHTML = '<div class="text-muted">暂无设备统计数据，添加设备并创建预约后自动生成柱状图</div>';
      return;
    }

    const isHours = metric === 'hours';
    const values = perEquipment.map((item) => (isHours ? item.total_hours : item.reservation_count));
    const maxVal = Math.max(1, ...values);

    const width = 640;
    const rowHeight = 44;
    const topPad = 24;
    const bottomPad = 24;
    const leftPad = 156;
    const rightPad = 76;
    const chartHeight = Math.max(220, topPad + bottomPad + perEquipment.length * rowHeight);
    const barAreaWidth = width - leftPad - rightPad;

    const gridLines = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
      const x = leftPad + barAreaWidth * ratio;
      const tickVal = Number((maxVal * ratio).toFixed(1));
      return `
        <line x1="${x}" y1="${topPad - 6}" x2="${x}" y2="${chartHeight - bottomPad}" stroke="#e2e8f0" stroke-dasharray="3,3" />
        <text x="${x}" y="${chartHeight - 6}" text-anchor="middle" font-size="11" fill="#64748b">${tickVal}</text>
      `;
    }).join('');

    const bars = perEquipment.map((item, idx) => {
      const val = isHours ? item.total_hours : item.reservation_count;
      const barW = Math.max(val > 0 ? 4 : 0, (val / maxVal) * barAreaWidth);
      const y = topPad + idx * rowHeight;
      const label = item.name.length > 10 ? `${item.name.slice(0, 10)}…` : item.name;
      const color = isHours ? '#0ea5e9' : '#2563eb';
      const unitText = isHours ? `${val} 小时` : `${val} 次`;

      return `
        <text x="${leftPad - 10}" y="${y + 17}" text-anchor="end" font-size="12.5" font-weight="600" fill="#1e293b">${escapeXml(label)}</text>
        <text x="${leftPad - 10}" y="${y + 31}" text-anchor="end" font-size="10.5" fill="#64748b">${escapeXml(item.code)}</text>
        <rect x="${leftPad}" y="${y + 8}" width="${barAreaWidth}" height="20" rx="5" fill="#f1f5f9" />
        <rect x="${leftPad}" y="${y + 8}" width="${barW}" height="20" rx="5" fill="${color}" />
        <text x="${leftPad + barW + 8}" y="${y + 22}" font-size="12" font-weight="600" fill="#0f172a">${unitText}</text>
      `;
    }).join('');

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${chartHeight}" width="100%" height="${chartHeight}" role="img" aria-label="设备使用统计柱状图">
        ${gridLines}
        ${bars}
      </svg>
    `;
  }

  /**
   * 渲染预约状态分类占比原生 SVG 环形图
   */
  function renderStatusDonutChart(container, statusCounts) {
    if (!container) return;
    const segments = [
      { key: 'booked', label: '已预约', value: statusCounts.booked || 0, color: '#2563eb' },
      { key: 'in_use', label: '使用中', value: statusCounts.in_use || 0, color: '#d97706' },
      { key: 'completed', label: '已完成', value: statusCounts.completed || 0, color: '#16a34a' },
      { key: 'cancelled', label: '已取消', value: statusCounts.cancelled || 0, color: '#94a3b8' }
    ];

    const total = segments.reduce((sum, s) => sum + s.value, 0);
    if (total === 0) {
      container.innerHTML = '<div class="text-muted">暂无预约记录，创建预约后显示各状态占比分布</div>';
      return;
    }

    const cx = 115;
    const cy = 120;
    const r = 74;
    const circumference = 2 * Math.PI * r;
    let offset = 0;

    const circles = segments
      .filter((s) => s.value > 0)
      .map((s) => {
        const dash = (s.value / total) * circumference;
        const el = `
          <circle
            cx="${cx}"
            cy="${cy}"
            r="${r}"
            fill="transparent"
            stroke="${s.color}"
            stroke-width="26"
            stroke-dasharray="${dash} ${circumference - dash}"
            stroke-dashoffset="${-offset}"
            transform="rotate(-90 ${cx} ${cy})"
          />
        `;
        offset += dash;
        return el;
      })
      .join('');

    const legend = segments.map((s, idx) => {
      const ly = 48 + idx * 42;
      const pct = ((s.value / total) * 100).toFixed(1);
      return `
        <rect x="236" y="${ly}" width="12" height="12" rx="3" fill="${s.color}" />
        <text x="256" y="${ly + 10}" font-size="13" font-weight="600" fill="#1e293b">${s.label}</text>
        <text x="410" y="${ly + 10}" text-anchor="end" font-size="12.5" fill="#475569">${s.value} 条 (${pct}%)</text>
      `;
    }).join('');

    container.innerHTML = `
      <svg viewBox="0 0 430 240" width="100%" height="240" role="img" aria-label="预约状态占比环形图">
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="transparent" stroke="#f1f5f9" stroke-width="26" />
        ${circles}
        <text x="${cx}" y="${cy - 4}" text-anchor="middle" font-size="22" font-weight="700" fill="#0f172a">${total}</text>
        <text x="${cx}" y="${cy + 16}" text-anchor="middle" font-size="11.5" fill="#64748b">总预约数</text>
        ${legend}
      </svg>
    `;
  }

  window.LabCharts = {
    renderEquipmentBarChart,
    renderStatusDonutChart
  };
})();
