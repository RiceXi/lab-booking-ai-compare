'use strict';

const path = require('node:path');
const { createLabBookingApp } = require('./app');
const { DEFAULT_DATA_PATH } = require('./storage');

const PORT = Number(process.env.PORT) || 3003;
const HOST = process.env.HOST || '127.0.0.1';
const DATA_FILE = process.env.DATA_FILE
  ? path.resolve(process.env.DATA_FILE)
  : DEFAULT_DATA_PATH;

const { server, storage } = createLabBookingApp({ dataFilePath: DATA_FILE });

server.listen(PORT, HOST, () => {
  console.log('====================================================');
  console.log('  实验室设备预约管理器 (Member-3 / KingSure000)');
  console.log(`  本地访问地址: http://${HOST}:${PORT}`);
  console.log(`  本地数据文件: ${storage.filePath}`);
  console.log('  按 Ctrl+C 停止服务');
  console.log('====================================================');
});
