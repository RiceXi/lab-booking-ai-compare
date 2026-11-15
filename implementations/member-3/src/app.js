'use strict';

const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { URL } = require('node:url');

const { AppError } = require('./errors');
const { JsonStorage, DEFAULT_DATA_PATH } = require('./storage');
const { EquipmentService } = require('./equipmentService');
const { ReservationService } = require('./reservationService');
const { StatsService } = require('./statsService');

const PUBLIC_DIR = path.resolve(__dirname, '..', 'public');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon'
};

/**
 * 解析请求 JSON Body
 */
function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let totalBytes = 0;

    req.on('data', (chunk) => {
      totalBytes += chunk.length;
      if (totalBytes > 1024 * 1024) {
        reject(new AppError('请求体过大', 413, 'PAYLOAD_TOO_LARGE'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });

    req.on('end', () => {
      if (chunks.length === 0) {
        resolve({});
        return;
      }
      const raw = Buffer.concat(chunks).toString('utf8').trim();
      if (!raw) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(raw));
      } catch (_) {
        reject(new AppError('请求 JSON 格式无效', 400, 'INVALID_JSON'));
      }
    });

    req.on('error', (err) => reject(err));
  });
}

/**
 * 发送 JSON 响应
 */
function sendJson(res, statusCode, data) {
  const payload = JSON.stringify(data);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store'
  });
  res.end(payload);
}

/**
 * 创建实验室设备预约管理器应用实例
 * @param {{ dataFilePath?: string }} [options]
 */
function createLabBookingApp(options = {}) {
  const dataFilePath = options.dataFilePath || DEFAULT_DATA_PATH;
  const storage = new JsonStorage(dataFilePath);
  const equipmentService = new EquipmentService(storage);
  const reservationService = new ReservationService(storage);
  const statsService = new StatsService(storage);

  async function handleApi(req, res, urlObj) {
    const pathname = urlObj.pathname;
    const method = req.method.toUpperCase();

    // GET /api/health
    if (pathname === '/api/health' && method === 'GET') {
      return sendJson(res, 200, {
        ok: true,
        dataFile: storage.filePath
      });
    }

    // GET /api/stats
    if (pathname === '/api/stats' && method === 'GET') {
      return sendJson(res, 200, {
        data: statsService.getSummaryStats()
      });
    }

    // GET /api/equipments & POST /api/equipments
    if (pathname === '/api/equipments') {
      if (method === 'GET') {
        return sendJson(res, 200, { data: equipmentService.listEquipments() });
      }
      if (method === 'POST') {
        const body = await readJsonBody(req);
        const created = equipmentService.createEquipment(body);
        return sendJson(res, 201, { data: created, message: '设备添加成功' });
      }
    }

    // /api/equipments/:id
    const eqMatch = /^\/api\/equipments\/([^/]+)$/.exec(pathname);
    if (eqMatch) {
      const id = decodeURIComponent(eqMatch[1]);
      if (method === 'GET') {
        return sendJson(res, 200, { data: equipmentService.getEquipmentDetail(id) });
      }
      if (method === 'PUT') {
        const body = await readJsonBody(req);
        const updated = equipmentService.updateEquipment(id, body);
        return sendJson(res, 200, { data: updated, message: '设备信息已更新' });
      }
      if (method === 'DELETE') {
        const result = equipmentService.deleteEquipment(id);
        return sendJson(res, 200, { data: result, message: '设备已删除' });
      }
    }

    // GET /api/reservations & POST /api/reservations
    if (pathname === '/api/reservations') {
      if (method === 'GET') {
        const filters = {
          equipment_id: urlObj.searchParams.get('equipment_id') || '',
          date: urlObj.searchParams.get('date') || '',
          status: urlObj.searchParams.get('status') || '',
          requester: urlObj.searchParams.get('requester') || ''
        };
        return sendJson(res, 200, { data: reservationService.listReservations(filters) });
      }
      if (method === 'POST') {
        const body = await readJsonBody(req);
        const created = reservationService.createReservation(body);
        return sendJson(res, 201, { data: created, message: '预约创建成功' });
      }
    }

    // PATCH /api/reservations/:id/status
    const statusMatch = /^\/api\/reservations\/([^/]+)\/status$/.exec(pathname);
    if (statusMatch && (method === 'PATCH' || method === 'POST')) {
      const id = decodeURIComponent(statusMatch[1]);
      const body = await readJsonBody(req);
      const updated = reservationService.updateReservationStatus(id, body.status);
      return sendJson(res, 200, { data: updated, message: '预约状态已更新' });
    }

    // POST /api/reservations/:id/cancel
    const cancelMatch = /^\/api\/reservations\/([^/]+)\/cancel$/.exec(pathname);
    if (cancelMatch && method === 'POST') {
      const id = decodeURIComponent(cancelMatch[1]);
      const cancelled = reservationService.cancelReservation(id);
      return sendJson(res, 200, { data: cancelled, message: '预约已取消' });
    }

    throw new AppError(`未找到接口：${method} ${pathname}`, 404, 'ROUTE_NOT_FOUND');
  }

  function serveStatic(req, res, urlObj) {
    let relativePath = urlObj.pathname === '/' ? '/index.html' : urlObj.pathname;
    relativePath = path.normalize(relativePath).replace(/^(\.\.[/\\])+/, '');
    const fullPath = path.join(PUBLIC_DIR, relativePath);

    if (!fullPath.startsWith(PUBLIC_DIR)) {
      res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Forbidden');
      return;
    }

    if (!fs.existsSync(fullPath) || fs.statSync(fullPath).isDirectory()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not Found');
      return;
    }

    const ext = path.extname(fullPath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    const content = fs.readFileSync(fullPath);
    res.writeHead(200, {
      'Content-Type': contentType,
      'Cache-Control': 'no-cache'
    });
    res.end(content);
  }

  const server = http.createServer(async (req, res) => {
    try {
      const urlObj = new URL(req.url || '/', 'http://127.0.0.1');
      if (urlObj.pathname.startsWith('/api/')) {
        await handleApi(req, res, urlObj);
      } else {
        serveStatic(req, res, urlObj);
      }
    } catch (err) {
      if (err instanceof AppError) {
        sendJson(res, err.statusCode, {
          error: {
            code: err.code,
            message: err.message,
            details: err.details || null
          }
        });
      } else {
        console.error('[Server Error]', err);
        sendJson(res, 500, {
          error: {
            code: 'INTERNAL_ERROR',
            message: '服务器内部错误，请查看控制台日志'
          }
        });
      }
    }
  });

  return {
    server,
    storage,
    equipmentService,
    reservationService,
    statsService
  };
}

module.exports = { createLabBookingApp };
