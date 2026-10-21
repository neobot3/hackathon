<script setup>
import { computed, reactive } from 'vue'
import { api } from '@/api'
import { useResource } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import PageHeader from '@/components/PageHeader.vue'
import { addDays, fmtDate, startOfDay, toDateInput, toIso } from '@/utils/format'

const reference = useReferenceStore()

const today = startOfDay()
const filters = reactive({ start: toDateInput(today), end: toDateInput(addDays(today, 84)), mro_id: '' })

const { data: weeks, loading, reload } = useResource(() =>
  api.dashboards.coverage({
    start: toIso(`${filters.start}T00:00`),
    end: toIso(`${filters.end}T23:59`),
    mro_id: filters.mro_id,
  }),
)

const totals = computed(() =>
  weeks.value.reduce(
    (t, w) => ({ needed: t.needed + w.seats_needed, filled: t.filled + w.seats_filled, gaps: t.gaps + (w.gap > 0 ? 1 : 0) }),
    { needed: 0, filled: 0, gaps: 0 },
  ),
)
const pct = (w) => (w.seats_needed ? Math.round((100 * w.seats_filled) / w.seats_needed) : 100)
</script>

<template>
  <div>
    <PageHeader title="Coverage" subtitle="MRO staffing levels and future staffing gaps by week." />

    <div class="grid grid-3">
      <div class="card stat">
        <div class="stat__label">Seats needed</div>
        <div class="stat__value">{{ totals.needed }}</div>
        <div class="stat__hint">Rep shifts across all demand</div>
      </div>
      <div class="card stat">
        <div class="stat__label">Seats filled</div>
        <div class="stat__value">{{ totals.filled }}</div>
        <div class="stat__hint">Proposed or confirmed</div>
      </div>
      <div class="card stat">
        <div class="stat__label">Weeks with gaps</div>
        <div class="stat__value">{{ totals.gaps }}</div>
        <div class="stat__hint">Location-weeks short of reps</div>
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
            <tr><th>Week of</th><th>MRO</th><th>Shifts</th><th>Needed</th><th>Filled</th><th>Staffing</th><th>Gap</th></tr>
          </thead>
          <tbody>
            <tr v-for="w in weeks" :key="`${w.mro_id}-${w.week_start}`">
              <td>{{ fmtDate(w.week_start) }}</td>
              <td><strong>{{ reference.mroName(w.mro_id) }}</strong></td>
              <td>{{ w.shifts }}</td>
              <td>{{ w.seats_needed }}</td>
              <td>{{ w.seats_filled }}</td>
              <td>
                <div class="meter" :title="`${pct(w)}%`">
                  <span :style="{ width: `${pct(w)}%` }" :class="{ 'meter--short': w.gap > 0 }" />
                </div>
              </td>
              <td :class="{ gap: w.gap > 0 }">{{ w.gap }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!weeks.length" class="empty">No demand in this period.</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.meter {
  width: 120px;
  height: 8px;
  border-radius: 4px;
  background: var(--border);
  overflow: hidden;
}
.meter span {
  display: block;
  height: 100%;
  background: var(--success);
}
.meter .meter--short {
  background: var(--warning);
}
.gap {
  color: var(--danger);
  font-weight: 700;
}
</style>
