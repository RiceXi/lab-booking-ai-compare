'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { createLabBookingApp } = require('../src/app');

async function startTestServer(dataFilePath) {
  const app = createLabBookingApp({ dataFilePath });
  await new Promise((resolve) => app.server.listen(0, '127.0.0.1', resolve));
  const { port } = app.server.address();
  const baseUrl = `http://127.0.0.1:${port}`;

  async function api(pathname, options = {}) {
    const opts = { ...options, headers: { ...(options.headers || {}) } };
    if (opts.body && typeof opts.body === 'object') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(`${baseUrl}${pathname}`, opts);
    const json = await res.json();
    return { status: res.status, body: json };
  }

  async function close() {
    await new Promise((resolve) => app.server.close(resolve));
  }

  return { app, baseUrl, api, close };
}

test('实验室设备预约管理器 AC1-AC12 全量验收用例与契约边界验证', async (t) => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-booking-m3-'));
  const dataFilePath = path.join(tmpDir, 'data.json');
  let srv = await startTestServer(dataFilePath);

  t.after(async () => {
    try {
      await srv.close();
    } catch (_) {}
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  let eq1;
  let eq2;
  let eq3;
  let res1;

  await t.test('AC1 添加设备：输入唯一编号、名称、位置和可用时间，保存后出现在列表中', async () => {
    const created = await srv.api('/api/equipments', {
      method: 'POST',
      body: {
        code: 'EQ-SEM-01',
        name: '扫描电子显微镜',
        location: '理科楼 A201',
        status: 'available',
        opening_start: '08:00',
        opening_end: '20:00',
        notes: '高精度形貌观测'
      }
    });
    assert.equal(created.status, 201);
    eq1 = created.body.data;
    assert.equal(eq1.code, 'EQ-SEM-01');
    assert.ok(eq1.id && eq1.created_at && eq1.updated_at);

    const list = await srv.api('/api/equipments');
    assert.equal(list.status, 200);
    assert.equal(list.body.data.length, 1);
    assert.equal(list.body.data[0].name, '扫描电子显微镜');
  });

  await t.test('AC2 重复设备编号：添加相同编号必须阻止保存并显示明确提示', async () => {
    const dup = await srv.api('/api/equipments', {
      method: 'POST',
      body: {
        code: 'EQ-SEM-01',
        name: '另一台电镜',
        location: '理科楼 A202',
        status: 'available',
        opening_start: '08:00',
        opening_end: '18:00'
      }
    });
    assert.equal(dup.status, 409);
    assert.equal(dup.body.error.code, 'DUPLICATE_EQUIPMENT_CODE');
    assert.match(dup.body.error.message, /不能重复|已存在/);
  });

  await t.test('AC3 创建有效预约：填写预约人、日期和合法时间，保存后出现在预约列表中', async () => {
    const created = await srv.api('/api/reservations', {
      method: 'POST',
      body: {
        equipment_id: eq1.id,
        requester: '张三(2024001)',
        date: '2026-11-16',
        start_time: '09:00',
        end_time: '10:00',
        notes: '金属断口扫描'
      }
    });
    assert.equal(created.status, 201);
    res1 = created.body.data;
    assert.equal(res1.status, 'booked');

    const list = await srv.api('/api/reservations');
    assert.equal(list.body.data.length, 1);
    assert.equal(list.body.data[0].requester, '张三(2024001)');
  });

  await t.test('AC4 冲突预约：同一设备同一日期时间重叠必须阻止并说明冲突', async () => {
    const conflict = await srv.api('/api/reservations', {
      method: 'POST',
      body: {
        equipment_id: eq1.id,
        requester: '李四',
        date: '2026-11-16',
        start_time: '09:30',
        end_time: '10:30'
      }
    });
    assert.equal(conflict.status, 409);
    assert.equal(conflict.body.error.code, 'RESERVATION_CONFLICT');
    assert.match(conflict.body.error.message, /冲突/);
  });

  await t.test('AC5 首尾相接：09:00-10:00 与 10:00-11:00 允许保存', async () => {
    const adjacent = await srv.api('/api/reservations', {
      method: 'POST',
      body: {
        equipment_id: eq1.id,
        requester: '王五',
        date: '2026-11-16',
        start_time: '10:00',
        end_time: '11:00'
      }
    });
    assert.equal(adjacent.status, 201);
  });

  await t.test('AC6 非法时间与非法输入：结束早于或等于开始、非30分钟粒度、非法日期均被阻止', async () => {
    const equalTime = await srv.api('/api/reservations', {
      method: 'POST',
      body: { equipment_id: eq1.id, requester: '赵六', date: '2026-11-16', start_time: '11:00', end_time: '11:00' }
    });
    assert.equal(equalTime.status, 400);

    const earlierEnd = await srv.api('/api/reservations', {
      method: 'POST',
      body: { equipment_id: eq1.id, requester: '赵六', date: '2026-11-16', start_time: '14:00', end_time: '13:00' }
    });
    assert.equal(earlierEnd.status, 400);

    const badGranularity = await srv.api('/api/reservations', {
      method: 'POST',
      body: { equipment_id: eq1.id, requester: '赵六', date: '2026-11-16', start_time: '14:15', end_time: '15:00' }
    });
    assert.equal(badGranularity.status, 400);

    const fakeDate = await srv.api('/api/reservations', {
      method: 'POST',
      body: { equipment_id: eq1.id, requester: '赵六', date: '2026-02-31', start_time: '14:00', end_time: '15:00' }
    });
    assert.equal(fakeDate.status, 400);
  });

  await t.test('AC7 取消预约与非法状态流转拦截：取消后变为 cancelled 且释放原时间段', async () => {
    const cancelResp = await srv.api(`/api/reservations/${res1.id}/cancel`, { method: 'POST' });
    assert.equal(cancelResp.status, 200);
    assert.equal(cancelResp.body.data.status, 'cancelled');

    // 禁止 cancelled -> booked
    const illegal = await srv.api(`/api/reservations/${res1.id}/status`, {
      method: 'PATCH',
      body: { status: 'booked' }
    });
    assert.equal(illegal.status, 409);

    // 原 09:00-10:00 时段可重新预约
    const rebook = await srv.api('/api/reservations', {
      method: 'POST',
      body: { equipment_id: eq1.id, requester: '孙七', date: '2026-11-16', start_time: '09:00', end_time: '10:00' }
    });
    assert.equal(rebook.status, 201);
  });

  await t.test('AC12 设备不可用：维护中或已停用的设备不能创建新预约', async () => {
    eq2 = (
      await srv.api('/api/equipments', {
        method: 'POST',
        body: {
          code: 'EQ-XRD-02',
          name: 'X射线衍射仪',
          location: '理科楼 B105',
          status: 'maintenance',
          opening_start: '08:30',
          opening_end: '17:30'
        }
      })
    ).body.data;

    eq3 = (
      await srv.api('/api/equipments', {
        method: 'POST',
        body: {
          code: 'EQ-FTIR-03',
          name: '傅里叶红外光谱仪',
          location: '理科楼 C302',
          status: 'retired',
          opening_start: '09:00',
          opening_end: '18:00'
        }
      })
    ).body.data;

    const rMaint = await srv.api('/api/reservations', {
      method: 'POST',
      body: { equipment_id: eq2.id, requester: '测试员', date: '2026-11-17', start_time: '09:00', end_time: '10:00' }
    });
    assert.equal(rMaint.status, 409);
    assert.equal(rMaint.body.error.code, 'EQUIPMENT_UNAVAILABLE');

    const rRet = await srv.api('/api/reservations', {
      method: 'POST',
      body: { equipment_id: eq3.id, requester: '测试员', date: '2026-11-17', start_time: '09:00', end_time: '10:00' }
    });
    assert.equal(rRet.status, 409);
    assert.equal(rRet.body.error.code, 'EQUIPMENT_UNAVAILABLE');
  });

  await t.test('AC8 & AC11 多条件组合筛选与统计数据核验', async () => {
    // 将 eq2 编辑恢复为 available 并新增一条次日预约，用于多设备多日期筛选与统计
    const upd = await srv.api(`/api/equipments/${eq2.id}`, {
      method: 'PUT',
      body: {
        code: 'EQ-XRD-02',
        name: 'X射线衍射仪',
        location: '理科楼 B105',
        status: 'available',
        opening_start: '08:30',
        opening_end: '17:30'
      }
    });
    assert.equal(upd.status, 200);

    const eq2Res = await srv.api('/api/reservations', {
      method: 'POST',
      body: { equipment_id: eq2.id, requester: '周八', date: '2026-11-17', start_time: '09:00', end_time: '11:00' }
    });
    assert.equal(eq2Res.status, 201);

    // 组合筛选：eq1 + 2026-11-16 + booked -> 应有 2 条（10:00-11:00 王五、09:00-10:00 孙七）
    const filtered = await srv.api(
      `/api/reservations?equipment_id=${encodeURIComponent(eq1.id)}&date=2026-11-16&status=booked`
    );
    assert.equal(filtered.body.data.length, 2);

    // AC11 统计：3台设备，3条有效预约（booked），1条已取消预约（cancelled）
    const stats = (await srv.api('/api/stats')).body.data;
    assert.equal(stats.total_equipments, 3);
    assert.equal(stats.active_reservations, 3);
    assert.equal(stats.cancelled_reservations, 1);
  });

  await t.test('AC9 删除设备：存在有效预约时阻止删除；完成或取消全部相关预约后允许删除', async () => {
    const blocked = await srv.api(`/api/equipments/${eq2.id}`, { method: 'DELETE' });
    assert.equal(blocked.status, 409);
    assert.equal(blocked.body.error.code, 'EQUIPMENT_HAS_ACTIVE_RESERVATIONS');

    const eq2List = (await srv.api(`/api/reservations?equipment_id=${encodeURIComponent(eq2.id)}`)).body.data;
    const targetResId = eq2List[0].id;
    // booked -> in_use -> completed
    await srv.api(`/api/reservations/${targetResId}/status`, { method: 'PATCH', body: { status: 'in_use' } });
    const doneResp = await srv.api(`/api/reservations/${targetResId}/status`, {
      method: 'PATCH',
      body: { status: 'completed' }
    });
    assert.equal(doneResp.status, 200);

    // 禁止 completed -> cancelled
    const badCancel = await srv.api(`/api/reservations/${targetResId}/cancel`, { method: 'POST' });
    assert.equal(badCancel.status, 409);

    // 现在无有效预约，允许删除 eq2
    const allowed = await srv.api(`/api/equipments/${eq2.id}`, { method: 'DELETE' });
    assert.equal(allowed.status, 200);
  });

  await t.test('AC10 本地持久化：关闭服务并重新启动新实例，设备和预约数据完整保留', async () => {
    await srv.close();
    srv = await startTestServer(dataFilePath);

    const eqList = (await srv.api('/api/equipments')).body.data;
    assert.equal(eqList.length, 2); // eq1 与 eq3 仍在
    const stats = (await srv.api('/api/stats')).body.data;
    assert.equal(stats.total_equipments, 2);
    assert.equal(stats.active_reservations, 2);
    assert.equal(stats.completed_reservations, 1);
    assert.equal(stats.cancelled_reservations, 1);
  });
});
