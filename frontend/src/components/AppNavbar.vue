<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLogo from './AppLogo.vue'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({ solid: Boolean })

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const scrolled = ref(false)
const open = ref(false)

const isSolid = computed(() => props.solid || scrolled.value || open.value)
const initials = computed(() =>
  (auth.user?.name || '')
    .split(' ')
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase(),
)
const roleLabel = computed(() => auth.roleLabel)

function onScroll() {
  scrolled.value = window.scrollY > 24
}

async function logout() {
  await auth.logout()
  router.push('/')
}

watch(() => route.fullPath, () => (open.value = false))
onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <header class="nav" :class="{ 'nav--solid': isSolid }">
    <div class="nav__inner">
      <AppLogo />

      <button class="nav__toggle" :aria-expanded="open" aria-label="Toggle menu" @click="open = !open">
        <span /><span /><span />
      </button>

      <nav class="nav__links" :class="{ 'nav__links--open': open }">
        <RouterLink to="/#features">Features</RouterLink>
        <RouterLink to="/#workflow">How it works</RouterLink>
        <RouterLink to="/#compliance">Compliance</RouterLink>

        <template v-if="auth.isAuthenticated">
          <span class="nav__divider" />
          <RouterLink v-if="auth.isAdmin" to="/admin" class="nav__area">Admin</RouterLink>
          <RouterLink v-if="auth.isScheduler" to="/scheduler" class="nav__area">Scheduler</RouterLink>
          <RouterLink to="/dashboards" class="nav__area">Dashboards</RouterLink>
          <div class="nav__user">
            <span class="nav__avatar">{{ initials }}</span>
            <span class="nav__who">
              <strong>{{ auth.user.name }}</strong>
              <small>{{ roleLabel }}</small>
            </span>
            <button class="btn btn--ghost btn--sm" @click="logout">Sign out</button>
          </div>
        </template>
        <RouterLink v-else to="/login" class="btn btn--primary btn--sm">Sign in</RouterLink>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.nav {
  position: fixed;
  inset: 0 0 auto 0;
  z-index: 50;
  color: #fff;
  transition: background 0.3s, box-shadow 0.3s, backdrop-filter 0.3s;
}
.nav--solid {
  background: rgba(8, 13, 31, 0.86);
  backdrop-filter: blur(14px);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.06);
}
.nav__inner {
  max-width: 1280px;
  margin: 0 auto;
  height: var(--nav-height);
  padding: 0 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.nav__links {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}
.nav__links > a:not(.btn) {
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.92rem;
  position: relative;
  transition: color 0.2s;
}
.nav__links > a:not(.btn)::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -6px;
  height: 2px;
  border-radius: 2px;
  background: var(--accent);
  transform: scaleX(0);
  transition: transform 0.25s;
}
.nav__links > a:not(.btn):hover,
.nav__area.router-link-active {
  color: #fff;
}
.nav__links > a:not(.btn):hover::after,
.nav__area.router-link-active::after {
  transform: scaleX(1);
}
.nav__divider {
  width: 1px;
  height: 22px;
  background: rgba(255, 255, 255, 0.15);
}
.nav__user {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.nav__avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 0.8rem;
  background: linear-gradient(135deg, var(--accent), var(--primary));
}
.nav__who {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.nav__who strong {
  font-size: 0.85rem;
}
.nav__who small {
  font-size: 0.7rem;
  opacity: 0.6;
}
.nav .btn--ghost {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.25);
}
.nav__toggle {
  display: none;
  background: none;
  border: 0;
  padding: 0.5rem;
  cursor: pointer;
}
.nav__toggle span {
  display: block;
  width: 22px;
  height: 2px;
  margin: 5px 0;
  background: #fff;
  border-radius: 2px;
}

@media (max-width: 900px) {
  .nav__toggle {
    display: block;
  }
  .nav__links {
    position: absolute;
    top: var(--nav-height);
    left: 0;
    right: 0;
    flex-direction: column;
    align-items: flex-start;
    padding: 1rem 1.5rem 1.5rem;
    background: rgba(8, 13, 31, 0.97);
    display: none;
  }
  .nav__links--open {
    display: flex;
  }
  .nav__divider {
    width: 100%;
    height: 1px;
  }
}
</style>
