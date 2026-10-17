import { createRouter, createWebHistory } from 'vue-router'
import { ROLES } from '@/auth/roles'
import { useAuthStore } from '@/stores/auth'
import HomeView from '@/views/HomeView.vue'

const DashboardLayout = () => import('@/layouts/DashboardLayout.vue')

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
  { path: '/auth/callback', name: 'auth-callback', component: () => import('@/views/AuthCallbackView.vue') },
  {
    path: '/admin',
    component: DashboardLayout,
    meta: { requiresAuth: true, role: ROLES.ADMIN, area: 'admin' },
    children: [
      { path: '', name: 'admin', component: () => import('@/views/admin/AdminDashboard.vue'), meta: { title: 'Admin overview' } },
      { path: 'reps', name: 'admin-reps', component: () => import('@/views/admin/RepsView.vue'), meta: { title: 'Tech reps' } },
      { path: 'aircraft-types', name: 'admin-aircraft', component: () => import('@/views/admin/AircraftTypesView.vue'), meta: { title: 'Aircraft types' } },
      { path: 'mro-locations', name: 'admin-mro', component: () => import('@/views/admin/MroLocationsView.vue'), meta: { title: 'MRO locations' } },
      { path: 'cba-rules', name: 'admin-cba', component: () => import('@/views/admin/CbaRulesView.vue'), meta: { title: 'CBA rules' } },
      { path: 'calendar', name: 'admin-calendar', component: () => import('@/views/admin/CalendarView.vue'), meta: { title: 'Holidays & pay periods' } },
    ],
  },
  {
    path: '/scheduler',
    component: DashboardLayout,
    meta: { requiresAuth: true, role: ROLES.SCHEDULER, area: 'scheduler' },
    children: [
      { path: '', name: 'scheduler', component: () => import('@/views/scheduler/SchedulerDashboard.vue'), meta: { title: 'Scheduling overview' } },
      { path: 'demands', name: 'scheduler-demands', component: () => import('@/views/scheduler/DemandsView.vue'), meta: { title: 'MRO demand' } },
      { path: 'unavailability', name: 'scheduler-unavailability', component: () => import('@/views/scheduler/UnavailabilityView.vue'), meta: { title: 'Rep unavailability' } },
      { path: 'run', name: 'scheduler-run', component: () => import('@/views/scheduler/ScheduleRunView.vue'), meta: { title: 'Run scheduler' } },
      { path: 'assignments', name: 'scheduler-assignments', component: () => import('@/views/scheduler/AssignmentsView.vue'), meta: { title: 'Assignments' } },
    ],
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, _from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, behavior: 'smooth', top: 80 }
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()

  if (to.name === 'login' && auth.isAuthenticated) return auth.homeRoute

  const required = to.matched.find((r) => r.meta.requiresAuth)
  if (!required) return true
  if (!auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } }
  if (required.meta.role && !auth.can(required.meta.role)) return auth.homeRoute
  return true
})

router.afterEach((to) => {
  const title = to.meta.title
  document.title = title ? `${title} · TechRep Scheduler` : 'TechRep Scheduler'
})

export default router
