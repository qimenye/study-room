/** 顶部导航 = 支持"滚动切换"的页面顺序（进房间的详情页不参与翻页）。 */
export const NAV_PAGES = [
  { name: 'rooms', label: '自习室', icon: 'door' },
  { name: 'records', label: '学习记录', icon: 'chart' },
  { name: 'ranking', label: '排行榜', icon: 'trophy' },
  { name: 'agent', label: 'AI 助手', icon: 'sparkles' },
]

export function pageIndex(routeName) {
  return NAV_PAGES.findIndex((page) => page.name === routeName)
}