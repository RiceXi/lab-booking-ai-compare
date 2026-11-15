'use strict';

const { parseTimeSlot } = require('./validators');

class StatsService {
  /**
   * @param {import('./storage').JsonStorage} storage
   */
  constructor(storage) {
    this.storage = storage;
  }

  /**
   * 统计设备与预约核心指标及按设备维度聚合数据
   * 口径说明（严格对应 docs/data-schema.md 与 docs/requirement.md）：
   * - 设备总数：当前系统中的设备数量
   * - 有效预约数量（active_reservations）：状态为 booked 或 in_use 的预约数
   * - 已完成预约数量（completed_reservations）：状态为 completed 的预约数
   * - 已取消预约数量（cancelled_reservations）：状态为 cancelled 的预约数
   * - 按设备统计：统计每台设备的非取消预约次数（booked + in_use + completed）、当前有效预约数及累计预约时长（小时）
   */
  getSummaryStats() {
    const { equipments, reservations } = this.storage.read();

    const equipmentStatusCounts = {
      available: 0,
      maintenance: 0,
      retired: 0
    };

    for (const eq of equipments) {
      if (equipmentStatusCounts[eq.status] !== undefined) {
        equipmentStatusCounts[eq.status] += 1;
      }
    }

    const reservationStatusCounts = {
      booked: 0,
      in_use: 0,
      completed: 0,
      cancelled: 0
    };

    for (const r of reservations) {
      if (reservationStatusCounts[r.status] !== undefined) {
        reservationStatusCounts[r.status] += 1;
      }
    }

    const activeReservations = reservationStatusCounts.booked + reservationStatusCounts.in_use;
    const completedReservations = reservationStatusCounts.completed;
    const cancelledReservations = reservationStatusCounts.cancelled;
    const nonCancelledReservations = activeReservations + completedReservations;

    const perEquipmentMap = new Map();
    for (const eq of equipments) {
      perEquipmentMap.set(eq.id, {
        equipment_id: eq.id,
        code: eq.code,
        name: eq.name,
        location: eq.location,
        status: eq.status,
        active_count: 0,
        completed_count: 0,
        cancelled_count: 0,
        reservation_count: 0, // 非取消的有效使用预约总次数 (booked + in_use + completed)
        total_hours: 0
      });
    }

    for (const r of reservations) {
      const bucket = perEquipmentMap.get(r.equipment_id);
      if (!bucket) continue;

      if (r.status === 'cancelled') {
        bucket.cancelled_count += 1;
        continue;
      }

      const startMin = parseTimeSlot(r.start_time, '开始时间', false).minutes;
      const endMin = parseTimeSlot(r.end_time, '结束时间', true).minutes;
      const durationHours = Math.max(0, (endMin - startMin) / 60);

      if (r.status === 'booked' || r.status === 'in_use') {
        bucket.active_count += 1;
      } else if (r.status === 'completed') {
        bucket.completed_count += 1;
      }

      bucket.reservation_count += 1;
      bucket.total_hours = Number((bucket.total_hours + durationHours).toFixed(2));
    }

    const perEquipment = Array.from(perEquipmentMap.values()).sort((a, b) => {
      if (b.reservation_count !== a.reservation_count) {
        return b.reservation_count - a.reservation_count;
      }
      return a.code.localeCompare(b.code);
    });

    return {
      total_equipments: equipments.length,
      active_reservations: activeReservations,
      completed_reservations: completedReservations,
      cancelled_reservations: cancelledReservations,
      non_cancelled_reservations: nonCancelledReservations,
      total_reservations: reservations.length,
      equipment_status_counts: equipmentStatusCounts,
      reservation_status_counts: reservationStatusCounts,
      per_equipment: perEquipment
    };
  }
}

module.exports = { StatsService };
