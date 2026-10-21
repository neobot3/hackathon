<script setup>
import { computed, reactive } from 'vue'
import { api } from '@/api'
import { useResource } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { addDays, num, startOfDay, titleCase, toDateInput, toIso } from '@/utils/format'

const reference = useReferenceStore()

const today = startOfDay()
const monday = addDays(today, -((today.getDay() + 6) % 7))
const filters = reactive({ start: toDateInput(monday), end: toDateInput(addDays(monday, 6)), mro_id: '' })

const { data: summary, loading, reload } = useResource(
  () =>
    api.dashboards.workforce({
      start: toIso(`${filters.start}T00:00`),
      end: toIso(`${filters.end}T23:59`),
      mro_id: filters.mro_id,
    }),
  { initial: { available: 0, assigned: 0, on_leave: 0, reps: [] } },
)

const groups = computed(() => ['assigned', 'available', 'on_leave'].map((s) => ({ status: s, reps: summary.value.reps.filter((r) => r.status === s) })))
</script>

<template>
  <div>
    <PageHeader title="Workforce" subtitle="Who is assigned, who is available, and who is on leave." />

    <div class="grid grid-3">
      <div class="card stat">
        <div class="stat__label">Assigned</div>
        <div class="stat__value">{{ summary.assigned }}</div>
        <div class="stat__hint">Working at least one shift</div>
      </div>
      <div class="card stat">
        <div class="stat__label">Available</div>
        <div class="stat__value">{{ summary.available }}</div>
        <div class="stat__hint">No assignment or leave</div>
      </div>
      <div class="card stat">
        <div class="stat__label">On leave</div>
        <div class="stat__value">{{ summary.on_leave }}</div>
        <div class="stat__hint">Approved vacation, sick, training, or other leave</div>
      </div>
    </div>

    <div class="card" style="margin-top: 1.25rem">
      <form class="filters" @submit.prevent="reload">
        <label class="field"><span>From</span><input v-model="filters.start" type="date" required /></label>
        <label class="field"><span>To</span><input v-model="filters.end" type="date" required /></label>
        <label class="field">
          <span>Location</span>
          <select v-model="filters.mro_id">
            <option value="">All locations</option>
            <option v-for="m in reference.mros" :key="m.id" :value="m.id">{{ m.facility_name }}</option>
          </select>
        </label>
        <button class="btn btn--ghost">Apply</button>
      </form>

      <div v-if="loading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Rep</th><th>Home base</th><th>Status</th><th>MROs</th><th>Hours</th><th>Leave</th></tr>
          </thead>
          <tbody>
            <template v-for="g in groups" :key="g.status">
              <tr v-for="r in g.reps" :key="r.rep_id">
                <td><strong>{{ r.name }}</strong></td>
                <td>{{ r.home_base }}</td>
                <td><StatusBadge :value="r.status" /></td>
                <td>{{ r.mro_ids.map(reference.mroCode).join(', ') || '—' }}</td>
                <td>{{ r.assigned_hours ? num(r.assigned_hours) : '—' }}</td>
                <td>{{ r.leave_reasons.map(titleCase).join(', ') || '—' }}</td>
              </tr>
            </template>
          </tbody>
        </table>
        <div v-if="!summary.reps.length" class="empty">No active reps for this location.</div>
      </div>
    </div>
  </div>
</template>
