'use strict';

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_DATA_PATH = path.resolve(__dirname, '..', 'data.json');

/**
 * 本地 JSON 持久化存储类
 * 确保文件不存在时自动初始化，并通过临时文件+Windows降级写策略保证写入完整性
 */
class JsonStorage {
  /**
   * @param {string} [filePath] JSON 数据文件路径，默认为 implementations/member-3/data.json
   */
  constructor(filePath = DEFAULT_DATA_PATH) {
    this.filePath = path.resolve(filePath);
    this.ensureInitialized();
  }

  /**
   * 确保目录与初始 JSON 结构存在
   */
  ensureInitialized() {
    const dir = path.dirname(this.filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    if (!fs.existsSync(this.filePath)) {
      this.write({ equipments: [], reservations: [] });
    }
  }

  /**
   * 读取完整数据快照
   * @returns {{ equipments: Array<object>, reservations: Array<object> }}
   */
  read() {
    this.ensureInitialized();
    const raw = fs.readFileSync(this.filePath, 'utf8');
    if (!raw || raw.trim().length === 0) {
      const empty = { equipments: [], reservations: [] };
      this.write(empty);
      return empty;
    }
    const parsed = JSON.parse(raw);
    return {
      equipments: Array.isArray(parsed.equipments) ? parsed.equipments : [],
      reservations: Array.isArray(parsed.reservations) ? parsed.reservations : []
    };
  }

  /**
   * 将数据写入本地 JSON 文件（兼顾原子性与 Windows 文件句柄锁降级处理）
   * @param {{ equipments: Array<object>, reservations: Array<object> }} data
   */
  write(data) {
    const dir = path.dirname(this.filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    const normalized = {
      equipments: Array.isArray(data.equipments) ? data.equipments : [],
      reservations: Array.isArray(data.reservations) ? data.reservations : []
    };
    const content = JSON.stringify(normalized, null, 2) + '\n';
    const tempPath = `${this.filePath}.${process.pid}.${Date.now()}.tmp`;

    try {
      fs.writeFileSync(tempPath, content, 'utf8');
      fs.renameSync(tempPath, this.filePath);
    } catch (err) {
      // Windows 环境下若目标文件被系统索引或杀毒软件短暂占用，renameSync 可能触发 EPERM/EACCES，降级为直接覆盖写入
      if (fs.existsSync(tempPath)) {
        try {
          fs.unlinkSync(tempPath);
        } catch (_) {
          // ignore cleanup failure
        }
      }
      fs.writeFileSync(this.filePath, content, 'utf8');
    }
  }
}

module.exports = {
  JsonStorage,
  DEFAULT_DATA_PATH
};
