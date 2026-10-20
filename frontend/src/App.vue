<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from './components/AppHeader.vue'
import Backdrop from './components/Backdrop.vue'
import PageRail from './components/PageRail.vue'
import PageScrollHint from './components/PageScrollHint.vue'
import { useScrollPaging } from './composables/useScrollPaging'
import { NAV_PAGES, pageIndex } from './utils/nav'
import { useUserStore } from './stores/user'

const user = useUserStore()
const route = useRoute()
const router = useRouter()

const showNav = computed(() => Boolean(user.token))
const index = computed(() => pageIndex(route.name))
const pagingEnabled = computed(() => showNav.value && index.value >= 0)
const hasNext = computed(() => index.value >= 0 && index.value < NAV_PAGES.length - 1)
const hasPrev = computed(() => index.value > 0)
const nextPage = computed(() => (hasNext.value ? NAV_PAGES[index.value + 1] : null))
const prevPage = computed(() => (hasPrev.value ? NAV_PAGES[index.value - 1] : null))

function go(step) {
  const target = NAV_PAGES[index.value + step]
  if (!target) return
  router.push({ name: target.name })
}

function gotoScreen(position) {
  const target = NAV_PAGES[position]
  if (target) router.push({ name: target.name })
}

const { progress, direction, reset: resetPaging } = useScrollPaging({
  enabled: pagingEnabled,
  hasNext,
  hasPrev,
  onNext: () => go(1),
  onPrev: () => go(-1),
})

const upProgress = computed(() => (direction.value === 'up' ? progress.value : 0))
const downProgress = computed(() => (direction.value === 'down' ? progress.value : 0))

// 换页后把翻页进度清零，免得进度的圆环停在半路像卡住
watch(() => route.name, resetPaging)

onMounted(() => {
  if (user.token && !user.profile) user.fetchMe()
})
</script>

<template>
  <div class="relative flex min-h-screen flex-col">
    <Backdrop />
    <AppHeader v-if="showNav" />

    <main class="mx-auto w-full max-w-6xl flex-1 px-4 pb-28 pt-6">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>

    <template v-if="pagingEnabled">
      <PageScrollHint :target="prevPage" arrow="up" :progress="upProgress" @go="go(-1)" />
      <PageScrollHint :target="nextPage" arrow="down" :progress="downProgress" @go="go(1)" />
      <PageRail :pages="NAV_PAGES" :index="index" @select="gotoScreen" @step="go" />
    </template>
  </div>
</template>
