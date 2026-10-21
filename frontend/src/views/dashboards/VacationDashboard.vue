<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '@/api'
import { useResource } from '@/composables/useResource'
import { useAuthStore } from '@/stores/auth'
import { useReferenceStore } from '@/stores/reference'
import PageHeader from '@/components/PageHeader.vue'
import { fmtDate, num, titleCase } from '@/utils/format'

const auth = useAuthStore()
const reference = useReferenceStore()

const thisYear = new Date().getFullYear()
const year = ref(thisYear)

// Balances: admins see everyone, tech reps see their own; other roles see none.
const ownRep = computed(() => {
  const email = auth.user?.email?.toLowerCase()
  return email ? reference.reps.find((r) => r.email?.toLowerCase() === email) : null
})
const showBalances = computed(() => auth.isAdmin || auth.isRep)

const { data: weeks, loading, reload } = useResource(() => api.vacation.capacity(year.value))
const { data: balances, reload: reloadBalances } = useResource(() => {
  if (auth.isAdmin) return api.leaveBalances.list({ year: year.value })
  if (auth.isRep && ownRep.value) return api.leaveBalances.list({ year: year.value, rep_id: ownRep.value.id })
  return Promise.resolve([])
})

watch(year, () => {
  reload()
  reloadBalances()
})
watch(ownRep, () => reloadBalances())

const booked = computed(() => weeks.value.filter((w) => w.reps_off > 0))
const fullWeeks = computed(() => weeks.value.filter((w) => w.remaining === 0).length)
</script>

<template>
  <div>
    <PageHeader title="Vacation" subtitle="Scheduled vacation and open places by week.">
      <label class="field">
        <span>Year</span>
        <select v-model.number="year">
          <option v-for="y in [thisYear - 1, thisYear, thisYear + 1]" :key="y" :value="y">{{ y }}</option>
        </select>
      </label>
    </PageHeader>

    <div class="grid grid-3">
      <div class="card stat">
        <div class="stat__label">Weeks with vacation</div>
        <div class="stat__value">{{ booked.length }}</div>
        <div class="stat__hint">At least one rep off</div>
      </div>
      <div class="card stat">
        <div class="stat__label">Full weeks</div>
        <div class="stat__value">{{ fullWeeks }}</div>
        <div class="stat__hint">No places left under the cap</div>
      </div>
      <div class="card stat">
        <div class="stat__label">Weekly cap</div>
        <div class="stat__value">{{ weeks[0]?.cap ?? '—' }}</div>
        <div class="stat__hint">Reps off in the same week</div>
      </div>
    </div>

    <div v-if="showBalances" class="card" style="margin-top: 1.25rem">
      <div class="card__head">
        <h2>{{ auth.isAdmin ? 'Remaining balances' : 'My balances' }}</h2>
      </div>
      <p v-if="auth.isRep && !auth.isAdmin && !ownRep" class="empty">
        No tech rep record matches {{ auth.user.email || 'your account' }}.
      </p>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Rep</th><th>Leave</th><th>Entitled</th><th>Used</th><th>Remaining</th></tr>
          </thead>
          <tbody>
            <tr v-for="b in balances" :key="`${b.rep_id}-${b.leave_type}`">
              <td><strong>{{ reference.repName(b.rep_id) }}</strong></td>
              <td>{{ b.leave_type === 'stat' ? 'Stat holidays' : titleCase(b.leave_type) }}</td>
              <td>{{ num(b.entitled_days) }}</td>
              <td>{{ num(b.used_days) }}</td>
              <td><strong>{{ num(b.remaining_days) }}</strong></td>
            </tr>
          </tbody>
        </table>
        <div v-if="!balances.length" class="empty">No balances on file for {{ year }}.</div>
      </div>
    </div>

    <div class="card" style="margin-top: 1.25rem">
      <div class="card__head"><h2>Vacation capacity</h2></div>
      <div v-if="loading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Week of</th><th>Off</th><th>Places left</th><th>On vacation</th></tr>
          </thead>
          <tbody>
            <tr v-for="w in weeks" :key="w.week_start">
              <td>{{ fmtDate(w.week_start) }}</td>
              <td>{{ w.reps_off }} / {{ w.cap }}</td>
              <td :class="{ full: w.remaining === 0 }">{{ w.remaining }}</td>
              <td>{{ w.rep_ids.map(reference.repName).join(', ') || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.full {
  color: var(--danger);
  font-weight: 700;
}
</style>
