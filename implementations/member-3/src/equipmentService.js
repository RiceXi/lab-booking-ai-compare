'use strict';

const crypto = require('node:crypto');
const { AppError } = require('./errors');
const { validateEquipmentPayload } = require('./validators');

class EquipmentService {
  /**
   * @param {import('./storage').JsonStorage} storage
   */
  constructor(storage) {
    this.storage = storage;
  }

  /**
   * 获取全部设备列表
   */
  listEquipments() {
    const { equipments, reservations } = this.storage.read();
    return equipments.map((eq) => {
      const activeReservationCount = reservations.filter(
        (r) => r.equipment_id === eq.id && (r.status === 'booked' || r.status === 'in_use')
      ).length;
      return {
        ...eq,
        active_reservation_count: activeReservationCount
      };
    });
  }

  /**
   * 获取单个设备详情及其关联预约记录
   */
  getEquipmentDetail(id) {
    const { equipments, reservations } = this.storage.read();
    const equipment = equipments.find((item) => item.id === id);
    if (!equipment) {
      throw new AppError('未找到指定的设备', 404, 'EQUIPMENT_NOT_FOUND');
    }

    const relatedReservations = reservations
      .filter((r) => r.equipment_id === id)
      .sort((a, b) => {
        if (a.date !== b.date) return b.date.localeCompare(a.date);
        return a.start_time.localeCompare(b.start_time);
      });

    return {
      ...equipment,
      reservations: relatedReservations
    };
  }

  /**
   * 添加新设备（严格遵守数据契约 Equipment 字段定义与编号唯一性约束）
   */
  createEquipment(payload) {
    const valid = validateEquipmentPayload(payload);
    const data = this.storage.read();

    const duplicate = data.equipments.find((item) => item.code === valid.code);
    if (duplicate) {
      throw new AppError(
        `设备编号 "${valid.code}" 已存在，设备编号不能重复`,
        409,
        'DUPLICATE_EQUIPMENT_CODE'
      );
    }

    const now = new Date().toISOString();
    const equipment = {
      id: crypto.randomUUID(),
      code: valid.code,
      name: valid.name,
      location: valid.location,
      status: valid.status,
      opening_start: valid.opening_start,
      opening_end: valid.opening_end,
      notes: valid.notes,
      created_at: now,
      updated_at: now
    };

    data.equipments.push(equipment);
    this.storage.write(data);
    return equipment;
  }

  /**
   * 编辑已有设备信息
   */
  updateEquipment(id, payload) {
    const valid = validateEquipmentPayload(payload);
    const data = this.storage.read();

    const index = data.equipments.findIndex((item) => item.id === id);
    if (index === -1) {
      throw new AppError('未找到指定的设备', 404, 'EQUIPMENT_NOT_FOUND');
    }

    const duplicate = data.equipments.find((item) => item.id !== id && item.code === valid.code);
    if (duplicate) {
      throw new AppError(
        `设备编号 "${valid.code}" 已被其他设备使用，设备编号不能重复`,
        409,
        'DUPLICATE_EQUIPMENT_CODE'
      );
    }

    const existing = data.equipments[index];
    const updated = {
      id: existing.id,
      code: valid.code,
      name: valid.name,
      location: valid.location,
      status: valid.status,
      opening_start: valid.opening_start,
      opening_end: valid.opening_end,
      notes: valid.notes,
      created_at: existing.created_at,
      updated_at: new Date().toISOString()
    };

    data.equipments[index] = updated;
    this.storage.write(data);
    return updated;
  }

  /**
   * 删除设备
   * 规则：存在状态为 booked 或 in_use 的有效预约时禁止删除；保留历史预约记录
   */
  deleteEquipment(id) {
    const data = this.storage.read();
    const index = data.equipments.findIndex((item) => item.id === id);
    if (index === -1) {
      throw new AppError('未找到指定的设备', 404, 'EQUIPMENT_NOT_FOUND');
    }

    const target = data.equipments[index];
    const activeReservations = data.reservations.filter(
      (r) => r.equipment_id === id && (r.status === 'booked' || r.status === 'in_use')
    );

    if (activeReservations.length > 0) {
      throw new AppError(
        `无法删除设备 "${target.name}"（${target.code}）：当前仍存在 ${activeReservations.length} 条有效预约（已预约/使用中），请先取消或完成相关预约`,
        409,
        'EQUIPMENT_HAS_ACTIVE_RESERVATIONS',
        { activeReservationCount: activeReservations.length }
      );
    }

    data.equipments.splice(index, 1);
    this.storage.write(data);
    return { deleted: true, id: target.id, code: target.code, name: target.name };
  }
}

module.exports = { EquipmentService };
