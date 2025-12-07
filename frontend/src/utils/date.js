/**
 * 格式化日期字符串
 * 解决后端返回的 UTC 时间在前端显示时未正确转换为本地时间的问题（少8小时）
 * @param {string} dateString - 日期字符串
 * @param {object} options - Intl.DateTimeFormat options
 * @returns {string} - 格式化后的日期字符串
 */
export const formatDate = (dateString, options = {}) => {
  if (!dateString) return '未知时间';

  let dateStr = dateString;
  
  // 检测是否为 ISO 格式且没有时区信息 (e.g. "2023-12-07T12:00:00.000000")
  // 如果是，则追加 'Z' 将其视为 UTC 时间
  if (typeof dateStr === 'string' && 
      dateStr.includes('T') && 
      !dateStr.endsWith('Z') && 
      !dateStr.match(/[+-]\d{2}:?\d{2}$/)) {
    dateStr += 'Z';
  }

  const date = new Date(dateStr);
  
  // 检查日期是否有效
  if (isNaN(date.getTime())) {
    return '无效时间';
  }

  const defaultOptions = {
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit',
    ...options
  };

  return date.toLocaleString('zh-CN', defaultOptions);
};
