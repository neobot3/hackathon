import { createRouter, createWebHistory } from 'vue-router'
import { ROLES } from '@/auth/roles'
import { useAuthStore } from '@/stores/auth'
import HomeView from '@/views/HomeView.vue'

const DashboardLayout = () => import('@/layouts/DashboardLayout.vue')

const EVERYONE = [ROLES.ADMIN, ROLES.SCHEDULER, ROLES.REP, ROLES.VIEWER]

// meta.roles gates each page; meta.nav is the sidebar entry (see DashboardLayout).
export const dashboardRoutes = [
  {
    path: '',
    name: 'dashboards',
    component: () => import('@/views/dashboards/WorkforceDashboard.vue'),
    meta: { title: 'Workforce', roles: EVERYONE, nav: { label: 'Workforce', icon: 'M17 20h5v-2a4 4 0 00-5-3.9M9 20H2v-2a4 4 0 017-2.6M12 11a3 3 0 100-6 3 3 0 000 6zM19 10a2 2 0 100-4 2 2 0 000 4z' } },
  },
  {
    path: 'coverage',
    name: 'dashboards-coverage',
    component: () => import('@/views/dashboards/CoverageDashboard.vue'),
    meta: { title: 'Coverage', roles: EVERYONE, nav: { label: 'Coverage', icon: 'M3 3v18h18M7 15l4-4 3 3 5-6' } },
  },
  {
    path: 'vacation',
    name: 'dashboards-vacation',
    component: () => import('@/views/dashboards/VacationDashboard.vue'),
    meta: { title: 'Vacation', roles: EVERYONE, nav: { label: 'Vacation', icon: 'M3 20h18M12 4v16M12 4c-4 0-7 3-7 6h14c0-3-3-6-7-6z' } },
  },
  {
    path: 'training',
    name: 'dashboards-training',
    component: () => import('@/views/dashboards/TrainingDashboard.vue'),
    meta: { title: 'Training', roles: [ROLES.ADMIN, ROLES.REP], nav: { label: 'Training', icon: 'M12 3L2 8l10 5 10-5-10-5zM6 10.5V16c0 1.5 2.7 3 6 3s6-1.5 6-3v-5.5' } },
  },
  {
    path: 'alerts',
    name: 'dashboards-alerts',
    component: () => import('@/views/dashboards/AlertsView.vue'),
    meta: { title: 'Alerts', roles: [ROLES.ADMIN, ROLES.SCHEDULER], nav: { label: 'Alerts', icon: 'M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 01-3.4 0' } },
  },
]

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
      { path: 'roster', name: 'admin-roster', component: () => import('@/views/admin/RosterView.vue'), meta: { title: 'Roster' } },
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
  {
    path: '/dashboards',
    component: DashboardLayout,
    meta: { requiresAuth: true, area: 'dashboards' },
    children: dashboardRoutes,
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
  if (to.matched.some((r) => r.meta.roles && !auth.canAny(r.meta.roles))) return auth.homeRoute
  return true
})

router.afterEach((to) => {
  const title = to.meta.title
  document.title = title ? `${title} · TechRep Scheduler` : 'TechRep Scheduler'
})

export default router
