<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Redirect target for Azure SSO; auth.init() processes the redirect response.
const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  await auth.init()
  router.replace(auth.isAuthenticated ? auth.homeRoute : '/login')
})
</script>

<template>
  <div class="loading" style="min-height: 100vh"><span class="spinner" /> Signing you in…</div>
</template>
