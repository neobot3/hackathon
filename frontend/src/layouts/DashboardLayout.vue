<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useReferenceStore } from '@/stores/reference'
import { useToastStore } from '@/stores/toast'

const auth = useAuthStore()
const reference = useReferenceStore()
const toast = useToastStore()
const route = useRoute()

const sections = computed(() => {
  const out = []
  if (auth.isAdmin) {
    out.push({
      title: 'Administration',
      links: [
        { to: '/admin', label: 'Overview', icon: 'M3 12l9-9 9 9M5 10v10h14V10' },
        { to: '/admin/reps', label: 'Tech reps', icon: 'M16 11a4 4 0 10-8 0 4 4 0 008 0zM4 21a8 8 0 0116 0' },
        { to: '/admin/aircraft-types', label: 'Aircraft types', icon: 'M2 16l20-6-20-6 4 6-4 6zM6 10h8' },
        { to: '/admin/mro-locations', label: 'MRO locations', icon: 'M12 21s-7-6.5-7-12a7 7 0 0114 0c0 5.5-7 12-7 12zM12 11a2 2 0 100-4 2 2 0 000 4z' },
        { to: '/admin/cba-rules', label: 'CBA rules', icon: 'M9 12l2 2 4-4M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z' },
        { to: '/admin/calendar', label: 'Holidays & pay', icon: 'M3 8h18M7 3v4M17 3v4M4 5h16v16H4z' },
      ],
    })
  }
  if (auth.isScheduler) {
    out.push({
      title: 'Scheduling',
      links: [
        { to: '/scheduler', label: 'Overview', icon: 'M4 13h6V4H4zM14 20h6V11h-6zM4 20h6v-3H4zM14 7h6V4h-6z' },
        { to: '/scheduler/demands', label: 'MRO demand', icon: 'M12 8v4l3 2M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
        { to: '/scheduler/unavailability', label: 'Unavailability', icon: 'M18.4 5.6L5.6 18.4M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
        { to: '/scheduler/run', label: 'Run scheduler', icon: 'M5 3l14 9-14 9V3z' },
        { to: '/scheduler/assignments', label: 'Assignments', icon: 'M9 5h11M9 12h11M9 19h11M4 5h.01M4 12h.01M4 19h.01' },
      ],
    })
  }
  return out
})

// Area roots (/admin, /scheduler) match exactly; sub-pages match by prefix.
const isActive = (to) => (to.split('/').length > 2 ? route.path.startsWith(to) : route.path === to)

onMounted(() => reference.load().catch((e) => toast.error(e.message)))
</script>

<template>
  <div class="dash">
    <aside class="dash__side">
      <div v-for="s in sections" :key="s.title" class="dash__section">
        <p class="dash__section-title">{{ s.title }}</p>
        <RouterLink
          v-for="l in s.links"
          :key="l.to"
          :to="l.to"
          class="dash__link"
          :class="{ 'dash__link--active': isActive(l.to) }"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path :d="l.icon" />
          </svg>
          {{ l.label }}
        </RouterLink>
      </div>
    </aside>

    <section class="dash__content">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" :key="route.path" />
        </Transition>
      </RouterView>
    </section>
  </div>
</template>

<style scoped>
.dash {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  min-height: calc(100vh - var(--nav-height));
}
.dash__side {
  position: sticky;
  top: var(--nav-height);
  height: calc(100vh - var(--nav-height));
  overflow-y: auto;
  padding: 1.5rem 1rem;
  background: linear-gradient(180deg, var(--ink) 0%, var(--ink-2) 100%);
  color: #fff;
}
.dash__section + .dash__section {
  margin-top: 1.75rem;
}
.dash__section-title {
  margin: 0 0 0.5rem 0.75rem;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: rgba(255, 255, 255, 0.4);
  font-weight: 700;
}
.dash__link {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: background 0.2s, color 0.2s;
}
.dash__link svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
.dash__link:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.dash__link--active {
  background: linear-gradient(90deg, rgba(34, 211, 238, 0.18), rgba(79, 70, 229, 0.12));
  color: #fff;
  box-shadow: inset 3px 0 0 var(--accent);
}
.dash__content {
  padding: 2rem clamp(1rem, 3vw, 2.5rem) 3rem;
  min-width: 0;
}
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
}
@media (max-width: 900px) {
  .dash {
    grid-template-columns: 1fr;
  }
  .dash__side {
    position: static;
    height: auto;
    display: flex;
    gap: 1rem;
    overflow-x: auto;
    padding: 0.75rem;
  }
  .dash__section {
    display: flex;
    gap: 0.25rem;
    align-items: center;
  }
  .dash__section + .dash__section {
    margin-top: 0;
  }
  .dash__section-title {
    display: none;
  }
  .dash__link {
    white-space: nowrap;
  }
}
</style>
