<script setup>
import { computed } from 'vue'
import { api } from '@/api'
import { useResource } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/PageHeader.vue'
import ScheduleTimeline from '@/components/ScheduleTimeline.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { addDays, fmtDateTime, hoursBetween, num, startOfDay, titleCase } from '@/utils/format'

const TONE = { proposed: 'info', confirmed: 'success', in_progress: 'warning', completed: 'muted' }

const auth = useAuthStore()
const reference = useReferenceStore()

const today = startOfDay()
// Monday-based week
const weekStart = addDays(today, -((today.getDay() + 6) % 7))
const weekEnd = addDays(weekStart, 7)

const { data: openDemands, loading: demandsLoading } = useResource(() =>
  api.demands.list({ status: 'open', start: today.toISOString() }),
)
const { data: leaveRequests } = useResource(() => api.unavailability.list({ status: 'requested' }))
const { data: proposed } = useResource(() => api.assignments.list({ status: 'proposed' }))
const { data: weekAssignments, loading: weekLoading } = useResource(() =>
  api.assignments.list({ start: weekStart.toISOString(), end: weekEnd.toISOString() }),
)

const openAog = computed(() => openDemands.value.filter((d) => d.demand_type === 'aog').length)
const upcoming = computed(() =>
  [...openDemands.value].sort((a, b) => a.start_time.localeCompare(b.start_time)).slice(0, 8),
)
const timelineItems = computed(() =>
  weekAssignments.value
    .filter((a) => a.status !== 'cancelled')
    .map((a) => ({ key: a.id, rep_id: a.rep_id, mro_id: a.mro_id, start_time: a.start_time, end_time: a.end_time, tone: TONE[a.status] })),
)
</script>

<template>
  <div>
    <PageHeader :title="`Welcome, ${auth.user.name.split(' ')[0]}`" subtitle="Open demand, pending requests and this week's coverage.">
      <RouterLink to="/scheduler/run" class="btn btn--primary">Run scheduler</RouterLink>
    </PageHeader>

    <div class="grid grid-4">
      <RouterLink to="/scheduler/demands" class="card stat">
        <div class="stat__label">Open demand</div>
        <div class="stat__value">{{ openDemands.length }}</div>
        <div class="stat__hint">Unfilled from today</div>
      </RouterLink>
      <RouterLink to="/scheduler/demands" class="card stat">
        <div class="stat__label">Open AOG</div>
        <div class="stat__value">{{ openAog }}</div>
        <div class="stat__hint">Aircraft on ground</div>
      </RouterLink>
      <RouterLink to="/scheduler/unavailability" class="card stat">
        <div class="stat__label">Leave requests</div>
        <div class="stat__value">{{ leaveRequests.length }}</div>
        <div class="stat__hint">Awaiting a decision</div>
      </RouterLink>
      <RouterLink to="/scheduler/assignments" class="card stat">
        <div class="stat__label">Proposed assignments</div>
        <div class="stat__value">{{ proposed.length }}</div>
        <div class="stat__hint">Ready to confirm</div>
      </RouterLink>
    </div>

    <div class="card" style="margin-top: 1.25rem">
      <div class="card__head">
        <h2>This week</h2>
        <RouterLink to="/scheduler/assignments" class="btn btn--ghost btn--sm">All assignments</RouterLink>
      </div>
      <div v-if="weekLoading" class="loading"><span class="spinner" /> Loading…</div>
      <ScheduleTimeline v-else :items="timelineItems" :start="weekStart" :end="weekEnd" />
    </div>

    <div class="card" style="margin-top: 1.25rem">
      <div class="card__head">
        <h2>Upcoming open demand</h2>
        <RouterLink to="/scheduler/demands" class="btn btn--ghost btn--sm">Manage demand</RouterLink>
      </div>
      <div v-if="demandsLoading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>MRO</th><th>Type</th><th>Aircraft</th><th>Start</th><th>Duration</th><th>Reps</th><th>Priority</th><th>Status</th></tr>
          </thead>
          <tbody>
            <tr v-for="d in upcoming" :key="d.id">
              <td><strong>{{ reference.mroName(d.mro_id) }}</strong></td>
              <td>{{ d.demand_type === 'aog' ? 'AOG' : titleCase(d.demand_type) }}</td>
              <td>{{ reference.aircraftName(d.aircraft_type_id) }}</td>
              <td>{{ fmtDateTime(d.start_time) }}</td>
              <td>{{ num(hoursBetween(d.start_time, d.end_time)) }} h</td>
              <td>{{ d.reps_needed }}</td>
              <td>{{ d.priority }}</td>
              <td><StatusBadge :value="d.status" /></td>
            </tr>
          </tbody>
        </table>
        <div v-if="!upcoming.length" class="empty">No open demand.</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
a.stat {
  color: inherit;
  text-decoration: none;
}
</style>
