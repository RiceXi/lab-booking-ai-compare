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

server.on('error', (err) => {
  if (err && err.code === 'EADDRINUSE') {
    console.error(`[提示] 端口 ${PORT} 已被占用，说明服务可能已在运行，可直接浏览器访问 http://${HOST}:${PORT}`);
    process.exit(1);
  }
  throw err;
});

server.listen(PORT, HOST, () => {
  console.log('====================================================');
  console.log('  实验室设备预约管理器 (Member-3 / KingSure000)');
  console.log(`  本地访问地址: http://${HOST}:${PORT}`);
  console.log(`  本地数据文件: ${storage.filePath}`);
  console.log('  按 Ctrl+C 停止服务');
  console.log('====================================================');
});
