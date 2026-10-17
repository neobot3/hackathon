<script setup>
import { config } from '@/config'

defineProps({ compact: Boolean })

// Swap this for your brand asset: drop a file in public/ and point logoSrc at it.
const logoSrc = '/logo.svg'
</script>

<template>
  <RouterLink to="/" class="brand" :class="{ 'brand--compact': compact }" aria-label="Home">
    <span class="brand__logo">
      <img :src="logoSrc" alt="" width="36" height="36" />
    </span>
    <span class="brand__text">
      <strong>{{ config.appName }}</strong>
      <small v-if="!compact">MRO Tech Rep Scheduling</small>
    </span>
  </RouterLink>
</template>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  color: inherit;
  text-decoration: none;
}
.brand__logo {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
}
.brand__logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}
.brand__text strong {
  font-family: var(--font-display);
  font-size: 1.1rem;
  letter-spacing: -0.01em;
}
.brand__text small {
  font-size: 0.7rem;
  opacity: 0.65;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
</style>
