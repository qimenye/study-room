<script setup>
import { computed } from 'vue'

import { useWallpaper } from '../composables/useWallpaper'

const { current, dim } = useWallpaper()

// 自定义图片用 background-image 铺满；用引号包住，避免地址里有括号时解析错
const imageStyle = computed(() =>
  current.value.image ? { backgroundImage: 'url("' + current.value.image + '")' } : null,
)

const veil = computed(() => 'rgba(3, 6, 12, ' + dim.value + ')')
</script>

<template>
  <div class="backdrop" aria-hidden="true">
    <Transition name="wp" mode="out-in">
      <div :key="current.key" class="absolute inset-0" :style="{ background: current.css }">
        <div v-if="imageStyle" class="absolute inset-0 bg-cover bg-center" :style="imageStyle" />
      </div>
    </Transition>

    <!-- 照片壁纸压一层暗色遮罩，保证文字能看清；强度可在壁纸面板里调 -->
    <div v-if="current.image" class="absolute inset-0" :style="{ background: veil }" />

    <div
      v-for="(color, index) in current.orbs"
      :key="index"
      class="orb"
      :class="index === 1 ? 'animate-floaty-slow' : 'animate-floaty'"
      :style="[
        { background: color },
        [
          { width: '44rem', height: '44rem', top: '-16rem', left: '-12rem' },
          { width: '38rem', height: '38rem', top: '-8rem', right: '-10rem' },
          { width: '34rem', height: '34rem', bottom: '-16rem', left: '38%' },
        ][index] || {},
        index === 2 ? { animationDelay: '-8s' } : {},
      ]"
    />

    <div class="backdrop-noise" />
    <div class="backdrop-vignette" />
  </div>
</template>
