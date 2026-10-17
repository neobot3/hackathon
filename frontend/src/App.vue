<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppNavbar from '@/components/AppNavbar.vue'
import AppFooter from '@/components/AppFooter.vue'
import ToastHost from '@/components/ToastHost.vue'

const route = useRoute()
const isDashboard = computed(() => route.matched.some((r) => r.meta.requiresAuth))
</script>

<template>
  <AppNavbar :solid="isDashboard" />
  <main :class="{ 'main--dashboard': isDashboard }">
    <RouterView />
  </main>
  <AppFooter v-if="!isDashboard" />
  <ToastHost />
</template>
