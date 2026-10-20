import { onBeforeUnmount, onMounted, ref } from 'vue'

const SCROLLABLE = /(auto|scroll|overlay)/

/** 单次滚轮事件最多计这么多像素，避免惯性大事件一口气把进度打满 */
const PER_EVENT_MAX = 140

/** deltaMode=1（按行）时的换算：一行大约滚这么多像素 */
const LINE_TO_PX = 40

/**
 * 把不同浏览器的滚轮量统一成像素。
 * Chrome/Edge 是 deltaMode=0（像素），Firefox 及部分鼠标是 1（行），
 * 还有 2（页）。不换算的话"行模式"下每格只有 3，攒满阈值要滚几十格。
 */
function wheelPixels(event) {
  if (event.deltaMode === 1) return event.deltaY * LINE_TO_PX
  if (event.deltaMode === 2) return event.deltaY * window.innerHeight
  return event.deltaY
}

/**
 * 判断这次滚动会不会被"内层可滚动区域"吃掉（比如聊天记录、计划正文）。
 * 内层还能往这个方向滚就放行给它；已经滚到头就交还给整页翻页。
 */
function innerCanScroll(target, deltaY) {
  let node = target
  while (node && node !== document.body && node !== document.documentElement) {
    if (node.nodeType === 1) {
      const locked = Boolean(node.getAttribute && node.getAttribute('data-scroll-lock') !== null)
      const overflowY = window.getComputedStyle(node).overflowY
      if (locked || SCROLLABLE.test(overflowY)) {
        const max = node.scrollHeight - node.clientHeight
        if (max > 2) {
          if (deltaY > 0 && node.scrollTop < max - 2) return true
          if (deltaY < 0 && node.scrollTop > 2) return true
        }
        // 走到这说明这块区域已经滚到头了，别再拦着整页翻页
        if (locked) return false
      }
    }
    node = node.parentElement
  }
  return false
}

/**
 * 滚到页面边界后继续滚动 → 切换上一个/下一个页面。
 * - 只有"已经滚到底/顶"才会计数，不影响正常阅读
 * - 累计到阈值才触发，避免滑动惯性误触
 * - 换页后有冷却时间，防止一次猛滚连跳两页
 * - 滚一点点就停手时，进度会自动回弹，圆环不会卡在半路
 */
export function useScrollPaging({
  enabled,
  hasNext,
  hasPrev,
  onNext,
  onPrev,
  threshold = 150,
  cooldown = 800,
  idle = 900,
}) {
  const progress = ref(0)
  const direction = ref('') // 'down' | 'up' | ''
  let accum = 0
  let accumStep = 0 // 当前这一轮累计的方向：1=向下，-1=向上，0=还没开始
  let lockedUntil = 0
  let idleTimer = null
  let touchStartY = null

  const atBottom = () =>
    window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4
  const atTop = () => window.scrollY <= 8

  function clearIdle() {
    if (idleTimer !== null) {
      window.clearTimeout(idleTimer)
      idleTimer = null
    }
  }

  function reset() {
    clearIdle()
    accum = 0
    accumStep = 0
    progress.value = 0
    direction.value = ''
  }

  /** 停手一小会儿就回弹，避免进度条/圆环一直停在中间看起来像卡住 */
  function resetSoon() {
    clearIdle()
    idleTimer = window.setTimeout(reset, idle)
  }

  function trigger(step) {
    lockedUntil = Date.now() + cooldown
    reset()
    if (step > 0) onNext()
    else onPrev()
  }

  function push(deltaY) {
    const step = deltaY > 0 ? 1 : -1
    if (Date.now() < lockedUntil) return
    if (!enabled.value) {
      reset()
      return
    }
    // 方向变了就重新累计。注意不能拿 accum 的正负去判断方向——
    // accum 累加的是绝对值，永远是正数，那样写会让"向上"每格都被清零。
    if (accumStep !== step) {
      accum = 0
      accumStep = step
    }

    if (step > 0) {
      if (!hasNext.value || !atBottom()) {
        reset()
        return
      }
    } else if (!hasPrev.value || !atTop()) {
      reset()
      return
    }

    direction.value = step > 0 ? 'down' : 'up'
    accum += Math.min(Math.abs(deltaY), PER_EVENT_MAX)
    progress.value = Math.min(1, accum / threshold)
    if (accum >= threshold) {
      trigger(step)
      return
    }
    resetSoon()
  }

  function onWheel(event) {
    if (!enabled.value) return
    if (event.ctrlKey || event.metaKey) return
    const deltaY = wheelPixels(event)
    if (Math.abs(deltaY) < 1) return
    if (innerCanScroll(event.target, deltaY)) {
      reset()
      return
    }
    push(deltaY)
  }

  function onScroll() {
    if (Date.now() < lockedUntil) return
    reset()
  }

  function onTouchStart(event) {
    if (!enabled.value || event.touches.length !== 1) return
    touchStartY = event.touches[0].clientY
  }

  function onTouchEnd(event) {
    if (!enabled.value || touchStartY === null) return
    const touch = event.changedTouches && event.changedTouches[0]
    const endY = touch ? touch.clientY : touchStartY
    const delta = touchStartY - endY
    touchStartY = null
    if (Date.now() < lockedUntil || Math.abs(delta) < 60) return

    if (delta > 0 && hasNext.value && atBottom() && !innerCanScroll(event.target, 1)) trigger(1)
    else if (delta < 0 && hasPrev.value && atTop() && !innerCanScroll(event.target, -1)) trigger(-1)
  }

  onMounted(() => {
    window.addEventListener('wheel', onWheel, { passive: true })
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchend', onTouchEnd, { passive: true })
  })

  onBeforeUnmount(() => {
    clearIdle()
    window.removeEventListener('wheel', onWheel)
    window.removeEventListener('scroll', onScroll)
    window.removeEventListener('touchstart', onTouchStart)
    window.removeEventListener('touchend', onTouchEnd)
  })

  return { progress, direction, reset }
}
