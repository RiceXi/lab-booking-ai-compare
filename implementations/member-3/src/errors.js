'use strict';

/**
 * 统一业务异常类，携带 HTTP 状态码与错误码，便于前端精准展示错误提示
 */
class AppError extends Error {
  /**
   * @param {string} message 面向用户的明确中文错误提示
   * @param {number} [statusCode=400] HTTP 状态码
   * @param {string} [code='VALIDATION_ERROR'] 业务错误标识
   * @param {object} [details=null] 附加诊断信息（如冲突的预约记录）
   */
  constructor(message, statusCode = 400, code = 'VALIDATION_ERROR', details = null) {
    super(message);
    this.name = 'AppError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

module.exports = { AppError };
