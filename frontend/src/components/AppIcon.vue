<script setup>
/**
 * 极简内联图标（不引第三方图标库、不请求外网字体），
 * 全部用 currentColor 描边，方便跟随主题色。
 */
defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  strokeWidth: { type: [Number, String], default: 1.7 },
})

const ICONS = {
  door: '<path d="M4 21h16"/><path d="M6.5 21V4.8A1.8 1.8 0 0 1 8.3 3h7.4A1.8 1.8 0 0 1 17.5 4.8V21"/><path d="M14.2 12.2h.01"/>',
  chart:
    '<path d="M4 20V4"/><path d="M4 20h16"/><path d="M8 20v-6"/><path d="M12.5 20V8"/><path d="M17 20v-9"/>',
  trophy:
    '<path d="M8 4h8v5a4 4 0 0 1-8 0V4Z"/><path d="M8 5H5.5a2.5 2.5 0 0 0 2.5 5"/><path d="M16 5h2.5a2.5 2.5 0 0 1-2.5 5"/><path d="M12 13v3.5"/><path d="M9 20h6"/><path d="M10.6 16.5h2.8l.6 3.5H10l.6-3.5Z"/>',
  sparkles:
    '<path d="M12 3.5l1.6 4.2 4.2 1.6-4.2 1.6L12 15.1l-1.6-4.2L6.2 9.3l4.2-1.6L12 3.5Z"/><path d="M18.3 5.4l.6 1.7 1.7.6-1.7.6-.6 1.7-.6-1.7-1.7-.6 1.7-.6.6-1.7Z"/><path d="M18 16.4l.6 1.5 1.5.6-1.5.6-.6 1.5-.6-1.5-1.5-.6 1.5-.6.6-1.5Z"/>',
  palette:
    '<path d="M12 3a9 9 0 0 0 0 18c1.4 0 2-.9 2-1.8 0-.6-.3-1-.3-1.6 0-.7.6-1.3 1.4-1.3H17a4 4 0 0 0 4-4c0-5-4-9.3-9-9.3Z"/><circle cx="7.8" cy="12.2" r="1.05"/><circle cx="9.8" cy="8.4" r="1.05"/><circle cx="14" cy="7.6" r="1.05"/><circle cx="17" cy="10.6" r="1.05"/>',
  plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
  logout:
    '<path d="M15 4h2.5A1.5 1.5 0 0 1 19 5.5v13A1.5 1.5 0 0 1 17.5 20H15"/><path d="M10 8l-4 4 4 4"/><path d="M6.5 12H15"/>',
  user: '<circle cx="12" cy="8.5" r="3.5"/><path d="M4.8 20a7.2 7.2 0 0 1 14.4 0"/>',
  chevronDown: '<path d="M6 9.5l6 6 6-6"/>',
  chevronUp: '<path d="M6 14.5l6-6 6 6"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  clock: '<circle cx="12" cy="12" r="8.4"/><path d="M12 7.6V12l3 1.9"/>',
  flame:
    '<path d="M12 3.5c3 3.4 5.4 5.9 5.4 9.4A5.4 5.4 0 0 1 6.6 13c0-1.4.5-2.4 1.4-3.6.4 1.5 1.2 2.2 2.1 2.4C9.7 9.3 10.5 6.4 12 3.5Z"/>',
  play: '<path d="M8 5.5l11 6.5-11 6.5v-13Z"/>',
  pause: '<path d="M9.2 5.5v13"/><path d="M14.8 5.5v13"/>',
  stop: '<rect x="6.5" y="6.5" width="11" height="11" rx="2.5"/>',
  send: '<path d="M4.5 12l15-7.5-6.3 15.5-2.1-6.1-6.6-1.9Z"/>',
  trash:
    '<path d="M5 7h14"/><path d="M9 7V5.6A1.6 1.6 0 0 1 10.6 4h2.8A1.6 1.6 0 0 1 15 5.6V7"/><path d="M7 7l.9 12.1A1.9 1.9 0 0 0 9.8 21h4.4a1.9 1.9 0 0 0 1.9-1.9L17 7"/>',
  rain: '<path d="M7.6 14.4a4 4 0 0 1 .7-7.9A5 5 0 0 1 18 8.1a3.8 3.8 0 0 1-.5 6.3"/><path d="M8.6 17.4l-.7 2.4"/><path d="M12.6 17.4l-.7 2.4"/><path d="M16.6 17.4l-.7 2.4"/>',
  coffee:
    '<path d="M5 8h11v5.4A4.6 4.6 0 0 1 11.4 18h-1.8A4.6 4.6 0 0 1 5 13.4V8Z"/><path d="M16 9.6h1.7a2.4 2.4 0 0 1 0 4.8H16"/><path d="M4 21h13"/>',
  book: '<path d="M4 5.6A1.6 1.6 0 0 1 5.6 4H10a2.4 2.4 0 0 1 2 1v14a2.4 2.4 0 0 0-2-1H5.6A1.6 1.6 0 0 1 4 16.4V5.6Z"/><path d="M20 5.6A1.6 1.6 0 0 0 18.4 4H14a2.4 2.4 0 0 0-2 1v14a2.4 2.4 0 0 1 2-1h4.4A1.6 1.6 0 0 0 20 16.4V5.6Z"/>',
  waves:
    '<path d="M3 9.6c2-1.7 4-1.7 6 0s4 1.7 6 0 4-1.7 6 0"/><path d="M3 14.4c2-1.7 4-1.7 6 0s4 1.7 6 0 4-1.7 6 0"/><path d="M3 19c2-1.7 4-1.7 6 0"/>',
  waveform: '<path d="M4 12h1.6"/><path d="M8 7.5v9"/><path d="M12 4.5v15"/><path d="M16 9v6"/><path d="M19.6 12h.4"/>',
  music:
    '<path d="M9 18V5.8l10-2.1v12"/><circle cx="6.4" cy="18.2" r="2.6"/><circle cx="16.4" cy="15.7" r="2.6"/>',
  search: '<circle cx="10.8" cy="10.8" r="6.4"/><path d="M15.6 15.6 20.2 20.2"/>',
  volume:
    '<path d="M4 9.6h3.1L12 5.4v13.2l-4.9-4.2H4V9.6Z"/><path d="M15.4 9.2a4 4 0 0 1 0 5.6"/><path d="M18 6.6a7.6 7.6 0 0 1 0 10.8"/>',
  refresh:
    '<path d="M19.8 11.6A7.9 7.9 0 0 0 6.4 6.5L4.6 8.2"/><path d="M4 4.6V9h4.4"/><path d="M4.2 12.4a7.9 7.9 0 0 0 13.4 5.1l1.8-1.7"/><path d="M20 19.4V15h-4.4"/>',
  target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.8"/><circle cx="12" cy="12" r="0.8"/>',
  calendar: '<rect x="4" y="5.6" width="16" height="14.4" rx="2.6"/><path d="M4 10.2h16"/><path d="M9 3.6v4"/><path d="M15 3.6v4"/>',
  info: '<circle cx="12" cy="12" r="8.4"/><path d="M12 11.2v5.4"/><path d="M12 7.9h.01"/>',
  bolt: '<path d="M13.4 3L6.2 13.4h4.9L10.4 21l7.4-10.6h-5L13.4 3Z"/>',
  users:
    '<circle cx="9" cy="8.6" r="3.3"/><path d="M3.5 19.6a5.6 5.6 0 0 1 11 0"/><path d="M16.2 6.2a3 3 0 0 1 0 5.6"/><path d="M17.4 19.6a5.4 5.4 0 0 0-1.6-3.8"/>',
  key: '<circle cx="8" cy="15.2" r="3.6"/><path d="M10.6 12.6 19 4.2"/><path d="M15.8 7.4l2.2 2.2"/><path d="M18.6 4.6l1.6 1.6"/>',
  settings:
    '<circle cx="12" cy="12" r="3.2"/><circle cx="12" cy="12" r="8.4"/><path d="M12 3.6v2.2"/><path d="M12 18.2v2.2"/><path d="M3.6 12h2.2"/><path d="M18.2 12h2.2"/>',
  image:
    '<rect x="3.6" y="4.8" width="16.8" height="14.4" rx="2.6"/><circle cx="9" cy="9.8" r="1.6"/><path d="M4.6 17.4l4.6-4.2 3.2 2.9 3-2.6 4.2 3.8"/>',
  upload: '<path d="M12 16.4V4.8"/><path d="M7.6 9.2 12 4.8l4.4 4.4"/><path d="M4.6 19.4h14.8"/>',
  close: '<path d="M6.6 6.6l10.8 10.8"/><path d="M17.4 6.6 6.6 17.4"/>',
}
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    v-html="ICONS[name] || ''"
  />
</template>
