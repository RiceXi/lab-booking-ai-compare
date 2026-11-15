'use strict';

const crypto = require('node:crypto');
const { AppError } = require('./errors');
const {
  RESERVATION_STATUSES,
  ALLOWED_STATUS_TRANSITIONS,
  EQUIPMENT_STATUS_LABELS,
  RESERVATION_STATUS_LABELS,
  parseTimeSlot,
  validateReservationPayload
} = require('./validators');

class ReservationService {
  /**
   * @param {import('./storage').JsonStorage} storage
   */
  constructor(storage) {
    this.storage = storage;
  }

  /**
   * 查询与多条件组合筛选预约列表
   * @param {{ equipment_id?: string, date?: string, status?: string, requester?: string }} [filters]
   */
  listReservations(filters = {}) {
    const { equipments, reservations } = this.storage.read();
    const equipmentMap = new Map(equipments.map((eq) => [eq.id, eq]));

    const equipmentIdFilter = typeof filters.equipment_id === 'string' ? filters.equipment_id.trim() : '';
    const dateFilter = typeof filters.date === 'string' ? filters.date.trim() : '';
    const statusFilter = typeof filters.status === 'string' ? filters.status.trim() : '';
    const requesterFilter = typeof filters.requester === 'string' ? filters.requester.trim().toLowerCase() : '';

    return reservations
      .filter((r) => {
        if (equipmentIdFilter && r.equipment_id !== equipmentIdFilter) {
          return false;
        }
        if (dateFilter && r.date !== dateFilter) {
          return false;
        }
        if (statusFilter && r.status !== statusFilter) {
          return false;
        }
        if (requesterFilter && !r.requester.toLowerCase().includes(requesterFilter)) {
          return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (a.date !== b.date) return b.date.localeCompare(a.date);
        if (a.start_time !== b.start_time) return a.start_time.localeCompare(b.start_time);
        return b.created_at.localeCompare(a.created_at);
      })
      .map((r) => {
        const eq = equipmentMap.get(r.equipment_id);
        return {
          ...r,
          equipment_code: eq ? eq.code : '已删除设备',
          equipment_name: eq ? eq.name : `已删除设备 (${r.equipment_id.slice(0, 8)})`,
          equipment_location: eq ? eq.location : '-'
        };
      });
  }

  /**
   * 创建新预约
   * 规则：
   * 1. 设备必须存在且状态为 available
   * 2. 预约区间落在设备 [opening_start, opening_end] 内
   * 3. 时间粒度 30 分钟，开始时间早于结束时间
   * 4. 半开区间 [start_time, end_time) 与同设备同日期的 booked/in_use 预约不重叠
   */
  createReservation(payload) {
    const valid = validateReservationPayload(payload);
    const data = this.storage.read();

    const equipment = data.equipments.find((eq) => eq.id === valid.equipment_id);
    if (!equipment) {
      throw new AppError('所选设备不存在，请刷新后重试', 404, 'EQUIPMENT_NOT_FOUND');
    }

    if (equipment.status !== 'available') {
      const statusLabel = EQUIPMENT_STATUS_LABELS[equipment.status] || equipment.status;
      throw new AppError(
        `设备 "${equipment.name}"（${equipment.code}）当前状态为“${statusLabel}”，不可创建新预约`,
        409,
        'EQUIPMENT_UNAVAILABLE'
      );
    }

    const openStart = parseTimeSlot(equipment.opening_start, '设备开放开始时间', false);
    const openEnd = parseTimeSlot(equipment.opening_end, '设备开放结束时间', true);

    if (valid.startMinutes < openStart.minutes || valid.endMinutes > openEnd.minutes) {
      throw new AppError(
        `预约时间（${valid.start_time}-${valid.end_time}）超出设备 "${equipment.name}" 的每日开放时段（${equipment.opening_start}-${equipment.opening_end}）`,
        400,
        'OUTSIDE_OPENING_HOURS'
      );
    }

    // 冲突检测：仅与同设备、同日期且状态为 booked 或 in_use 的预约按半开区间 [start, end) 判重
    const conflict = data.reservations.find((existing) => {
      if (existing.equipment_id !== equipment.id) return false;
      if (existing.date !== valid.date) return false;
      if (existing.status !== 'booked' && existing.status !== 'in_use') return false;

      const oldStart = parseTimeSlot(existing.start_time, '已有预约开始时间', false).minutes;
      const oldEnd = parseTimeSlot(existing.end_time, '已有预约结束时间', true).minutes;

      // new.start_time < old.end_time AND old.start_time < new.end_time
      return valid.startMinutes < oldEnd && oldStart < valid.endMinutes;
    });

    if (conflict) {
      const conflictStatusLabel = RESERVATION_STATUS_LABELS[conflict.status] || conflict.status;
      throw new AppError(
        `时间冲突：设备 "${equipment.name}" 在 ${valid.date} ${conflict.start_time}-${conflict.end_time} 已有预约（预约人：${conflict.requester}，状态：${conflictStatusLabel}）`,
        409,
        'RESERVATION_CONFLICT',
        { conflictingReservation: conflict }
      );
    }

    const now = new Date().toISOString();
    const reservation = {
      id: crypto.randomUUID(),
      equipment_id: equipment.id,
      requester: valid.requester,
      date: valid.date,
      start_time: valid.start_time,
      end_time: valid.end_time,
      status: 'booked',
      notes: valid.notes,
      created_at: now,
      updated_at: now
    };

    data.reservations.push(reservation);
    this.storage.write(data);
    return {
      ...reservation,
      equipment_code: equipment.code,
      equipment_name: equipment.name,
      equipment_location: equipment.location
    };
  }

  /**
   * 变更预约状态（严格执行数据契约第 3 节状态机）
   * 允许：booked -> in_use, booked -> cancelled, in_use -> completed
   */
  updateReservationStatus(id, nextStatus) {
    if (!RESERVATION_STATUSES.includes(nextStatus)) {
      throw new AppError(
        `目标预约状态不合法，仅允许：${RESERVATION_STATUSES.join('、')}`,
        400,
        'INVALID_RESERVATION_STATUS'
      );
    }

    const data = this.storage.read();
    const index = data.reservations.findIndex((item) => item.id === id);
    if (index === -1) {
      throw new AppError('未找到指定的预约记录', 404, 'RESERVATION_NOT_FOUND');
    }

    const current = data.reservations[index];
    const allowedTargets = ALLOWED_STATUS_TRANSITIONS[current.status] || [];

    if (!allowedTargets.includes(nextStatus)) {
      const fromLabel = RESERVATION_STATUS_LABELS[current.status] || current.status;
      const toLabel = RESERVATION_STATUS_LABELS[nextStatus] || nextStatus;
      throw new AppError(
        `不允许将预约状态从“${fromLabel}（${current.status}）”变更为“${toLabel}（${nextStatus}）”`,
        409,
        'INVALID_STATUS_TRANSITION'
      );
    }

    const updated = {
      ...current,
      status: nextStatus,
      updated_at: new Date().toISOString()
    };

    data.reservations[index] = updated;
    this.storage.write(data);

    const equipment = data.equipments.find((eq) => eq.id === updated.equipment_id);
    return {
      ...updated,
      equipment_code: equipment ? equipment.code : '已删除设备',
      equipment_name: equipment ? equipment.name : `已删除设备 (${updated.equipment_id.slice(0, 8)})`,
      equipment_location: equipment ? equipment.location : '-'
    };
  }

  /**
   * 取消预约快捷方法
   */
  cancelReservation(id) {
    return this.updateReservationStatus(id, 'cancelled');
  }
}

module.exports = { ReservationService };
