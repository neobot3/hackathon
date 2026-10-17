<script setup>
import { reactive, ref, watch } from 'vue'
import { api } from '@/api'
import { useResource, useSubmit } from '@/composables/useResource'
import { useToastStore } from '@/stores/toast'
import PageHeader from '@/components/PageHeader.vue'
import { fmtDate } from '@/utils/format'

const toast = useToastStore()
const year = ref(new Date().getFullYear())
const range = () => ({ start: `${year.value}-01-01`, end: `${year.value}-12-31` })

const { data: holidays, reload: reloadHolidays } = useResource(() => api.cba.holidays(range()))
const { data: periods, reload: reloadPeriods } = useResource(() => api.cba.payPeriods({ start: `${year.value}-01-01`, end: `${year.value + 1}-01-01` }))
watch(year, () => {
  reloadHolidays()
  reloadPeriods()
})

const holidayForm = reactive({ holiday_date: '', name: '' })
const holidaySave = useSubmit()
async function addHoliday() {
  if (await holidaySave.run(() => api.cba.createHoliday({ ...holidayForm }), 'Holiday added')) {
    Object.assign(holidayForm, { holiday_date: '', name: '' })
    reloadHolidays()
  }
}

const periodForm = reactive({ start_date: '', end_date: '' })
const periodSave = useSubmit()
async function addPeriod() {
  if (await periodSave.run(() => api.cba.createPayPeriod({ ...periodForm }), 'Pay period added')) {
    Object.assign(periodForm, { start_date: '', end_date: '' })
    reloadPeriods()
  }
}
async function removePeriod(p) {
  if (!confirm(`Delete pay period ${fmtDate(p.start_date)} – ${fmtDate(p.end_date)}?`)) return
  try {
    await api.cba.deletePayPeriod(p.id)
    toast.success('Pay period deleted')
    reloadPeriods()
  } catch (e) {
    toast.error(e.message)
  }
}

const weekday = (d) => new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { weekday: 'short' })
</script>

<template>
  <div>
    <PageHeader title="Holidays & pay periods" subtitle="Statutory holidays drive premium pay; pay periods bound overtime calculations.">
      <div class="row">
        <button class="btn btn--ghost btn--sm" @click="year--">&larr;</button>
        <strong style="font-family: var(--font-display); font-size: 1.2rem">{{ year }}</strong>
        <button class="btn btn--ghost btn--sm" @click="year++">&rarr;</button>
      </div>
    </PageHeader>

    <div class="grid grid-2" style="align-items: start">
      <div class="card">
        <div class="card__head"><h2>Statutory holidays</h2><span class="badge badge--muted">{{ holidays.length }}</span></div>
        <form class="filters" @submit.prevent="addHoliday">
          <label class="field"><span>Date</span><input v-model="holidayForm.holiday_date" type="date" required /></label>
          <label class="field" style="flex: 1"><span>Name</span><input v-model="holidayForm.name" required maxlength="100" /></label>
          <button class="btn btn--primary" :disabled="holidaySave.busy.value">Add</button>
        </form>
        <p v-if="holidaySave.error.value" class="form-error" style="margin: 1rem">{{ holidaySave.error.value }}</p>
        <ul class="list">
          <li v-for="h in holidays" :key="h.holiday_date">
            <span class="date-chip">
              <small>{{ weekday(h.holiday_date) }}</small>
              <strong>{{ h.holiday_date.slice(8) }}</strong>
            </span>
            <div>
              <strong>{{ h.name }}</strong>
              <div class="muted" style="font-size: 0.8rem">{{ fmtDate(h.holiday_date) }}</div>
            </div>
          </li>
        </ul>
        <div v-if="!holidays.length" class="empty">No holidays for {{ year }}.</div>
      </div>

      <div class="card">
        <div class="card__head"><h2>Pay periods</h2><span class="badge badge--muted">{{ periods.length }}</span></div>
        <form class="filters" @submit.prevent="addPeriod">
          <label class="field"><span>Start</span><input v-model="periodForm.start_date" type="date" required /></label>
          <label class="field"><span>End (exclusive)</span><input v-model="periodForm.end_date" type="date" required /></label>
          <button class="btn btn--primary" :disabled="periodSave.busy.value">Add</button>
        </form>
        <p v-if="periodSave.error.value" class="form-error" style="margin: 1rem">{{ periodSave.error.value }}</p>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Start</th><th>End (exclusive)</th><th /></tr></thead>
            <tbody>
              <tr v-for="p in periods" :key="p.id">
                <td>{{ fmtDate(p.start_date) }}</td>
                <td>{{ fmtDate(p.end_date) }}</td>
                <td class="actions"><button class="btn btn--danger btn--sm" @click="removePeriod(p)">Delete</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!periods.length" class="empty">No custom pay periods; semi-monthly defaults apply.</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.list {
  list-style: none;
  margin: 0;
  padding: 0.5rem 1.25rem;
}
.list li {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.7rem 0;
}
.list li + li {
  border-top: 1px solid var(--border);
}
.date-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 52px;
  border-radius: 12px;
  background: linear-gradient(160deg, #eef2ff, #e0f2fe);
  color: var(--primary-600);
}
.date-chip small {
  font-size: 0.65rem;
  text-transform: uppercase;
  font-weight: 700;
}
.date-chip strong {
  font-size: 1.15rem;
  font-family: var(--font-display);
}
</style>
