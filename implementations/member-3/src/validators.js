'use strict';

const { AppError } = require('./errors');

const EQUIPMENT_STATUSES = ['available', 'maintenance', 'retired'];
const RESERVATION_STATUSES = ['booked', 'in_use', 'completed', 'cancelled'];

/**
 * 数据契约第 3 节规定的预约状态合法流转表
 */
const ALLOWED_STATUS_TRANSITIONS = {
  booked: ['in_use', 'cancelled'],
  in_use: ['completed'],
  completed: [],
  cancelled: []
};

const EQUIPMENT_STATUS_LABELS = {
  available: '可预约',
  maintenance: '维护中',
  retired: '已停用'
};

const RESERVATION_STATUS_LABELS = {
  booked: '已预约',
  in_use: '使用中',
  completed: '已完成',
  cancelled: '已取消'
};

/**
 * 校验必填非空字符串并返回去除首尾空白后的结果
 */
function requireNonEmptyString(value, fieldLabel) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new AppError(`${fieldLabel}不能为空`, 400, 'VALIDATION_ERROR');
  }
  return value.trim();
}

/**
 * 校验可选字符串（如备注 notes）
 */
function normalizeOptionalString(value) {
  if (value === undefined || value === null) {
    return '';
  }
  if (typeof value !== 'string') {
    return String(value).trim();
  }
  return value.trim();
}

/**
 * 严格校验本地日期格式 YYYY-MM-DD，防止如 2026-02-31 被 Date 自动进位放行
 */
function validateDateString(dateStr, fieldLabel = '预约日期') {
  const cleaned = requireNonEmptyString(dateStr, fieldLabel);
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(cleaned);
  if (!match) {
    throw new AppError(`${fieldLabel}格式不合法，必须为 YYYY-MM-DD（如 2026-11-15）`, 400, 'INVALID_DATE');
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);

  if (month < 1 || month > 12 || day < 1 || day > 31) {
    throw new AppError(`${fieldLabel}不是真实存在的日历日期`, 400, 'INVALID_DATE');
  }

  const utcDate = new Date(Date.UTC(year, month - 1, day));
  if (
    utcDate.getUTCFullYear() !== year ||
    utcDate.getUTCMonth() + 1 !== month ||
    utcDate.getUTCDate() !== day
  ) {
    throw new AppError(`${fieldLabel}不是真实存在的日历日期（例如 ${cleaned} 不存在）`, 400, 'INVALID_DATE');
  }

  return cleaned;
}

/**
 * 解析并校验 HH:mm 时间格式及 30 分钟粒度
 * @param {string} timeStr 时间字符串
 * @param {string} fieldLabel 字段中文名
 * @param {boolean} [allowEndOfDay=false] 结束时间是否允许 24:00
 * @returns {{ formatted: string, minutes: number }}
 */
function parseTimeSlot(timeStr, fieldLabel, allowEndOfDay = false) {
  const cleaned = requireNonEmptyString(timeStr, fieldLabel);
  if (allowEndOfDay && cleaned === '24:00') {
    return { formatted: '24:00', minutes: 24 * 60 };
  }

  const match = /^(\d{2}):(\d{2})$/.exec(cleaned);
  if (!match) {
    throw new AppError(`${fieldLabel}格式不合法，必须为 HH:mm（如 09:00 或 14:30）`, 400, 'INVALID_TIME');
  }

  const hours = Number(match[1]);
  const minutes = Number(match[2]);

  if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
    throw new AppError(`${fieldLabel}超出合法时间范围（00:00 至 23:59）`, 400, 'INVALID_TIME');
  }

  if (minutes !== 0 && minutes !== 30) {
    throw new AppError(`${fieldLabel}必须满足 30 分钟时间粒度（分钟只能为 00 或 30）`, 400, 'INVALID_TIME_GRANULARITY');
  }

  return {
    formatted: cleaned,
    minutes: hours * 60 + minutes
  };
}

/**
 * 校验时间区间 [start_time, end_time)，要求开始时间严格早于结束时间
 */
function validateTimeRange(startStr, endStr, startLabel = '开始时间', endLabel = '结束时间') {
  const start = parseTimeSlot(startStr, startLabel, false);
  const end = parseTimeSlot(endStr, endLabel, true);

  if (start.minutes >= end.minutes) {
    throw new AppError(`${startLabel}（${start.formatted}）必须早于${endLabel}（${end.formatted}）`, 400, 'INVALID_TIME_RANGE');
  }

  return { start, end };
}

/**
 * 校验设备输入字段
 */
function validateEquipmentPayload(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new AppError('请求数据格式不正确', 400, 'VALIDATION_ERROR');
  }

  const code = requireNonEmptyString(payload.code, '设备编号');
  const name = requireNonEmptyString(payload.name, '设备名称');
  const location = requireNonEmptyString(payload.location, '存放位置');
  const status = requireNonEmptyString(payload.status || 'available', '设备状态');

  if (!EQUIPMENT_STATUSES.includes(status)) {
    throw new AppError(
      `设备状态不合法，仅允许：${EQUIPMENT_STATUSES.join('、')}`,
      400,
      'INVALID_EQUIPMENT_STATUS'
    );
  }

  const { start: openingStart, end: openingEnd } = validateTimeRange(
    payload.opening_start,
    payload.opening_end,
    '每日可预约开始时间',
    '每日可预约结束时间'
  );

  const notes = normalizeOptionalString(payload.notes);

  return {
    code,
    name,
    location,
    status,
    opening_start: openingStart.formatted,
    opening_end: openingEnd.formatted,
    notes
  };
}

/**
 * 校验新建预约输入字段
 */
function validateReservationPayload(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new AppError('请求数据格式不正确', 400, 'VALIDATION_ERROR');
  }

  const equipment_id = requireNonEmptyString(payload.equipment_id, '预约设备');
  const requester = requireNonEmptyString(payload.requester, '预约人');
  const date = validateDateString(payload.date, '预约日期');
  const { start, end } = validateTimeRange(payload.start_time, payload.end_time, '开始时间', '结束时间');
  const notes = normalizeOptionalString(payload.notes);

  return {
    equipment_id,
    requester,
    date,
    start_time: start.formatted,
    end_time: end.formatted,
    startMinutes: start.minutes,
    endMinutes: end.minutes,
    notes
  };
}

module.exports = {
  EQUIPMENT_STATUSES,
  RESERVATION_STATUSES,
  ALLOWED_STATUS_TRANSITIONS,
  EQUIPMENT_STATUS_LABELS,
  RESERVATION_STATUS_LABELS,
  requireNonEmptyString,
  normalizeOptionalString,
  validateDateString,
  parseTimeSlot,
  validateTimeRange,
  validateEquipmentPayload,
  validateReservationPayload
};
