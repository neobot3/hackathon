<script setup>
import { computed, reactive, ref } from 'vue'
import { api } from '@/api'
import { useResource, useSubmit } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useToastStore } from '@/stores/toast'
import BaseModal from '@/components/BaseModal.vue'
import PageHeader from '@/components/PageHeader.vue'
import ScheduleTimeline from '@/components/ScheduleTimeline.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { addDays, fmtDateTime, num, startOfDay, titleCase, toDateInput, toIso, toLocalInput } from '@/utils/format'

const NEXT = {
  proposed: ['confirmed', 'cancelled'],
  confirmed: ['in_progress', 'cancelled'],
  in_progress: ['completed', 'cancelled'],
}
const TONE = { proposed: 'info', confirmed: 'success', in_progress: 'warning', completed: 'muted', cancelled: 'muted' }
const ACTION_LABEL = { confirmed: 'Confirm', in_progress: 'Start', completed: 'Complete', cancelled: 'Cancel' }

const reference = useReferenceStore()
const toast = useToastStore()

const filters = reactive({
  rep_id: '',
  mro_id: '',
  status: '',
  start: toDateInput(startOfDay()),
  end: toDateInput(addDays(new Date(), 14)),
})
const range = computed(() => ({
  start: filters.start ? toIso(`${filters.start}T00:00`) : null,
  end: filters.end ? toIso(`${filters.end}T23:59`) : null,
}))
const { data: assignments, loading, reload } = useResource(() => api.assignments.list({ ...filters, ...range.value }))
const sorted = computed(() => [...assignments.value].sort((a, b) => a.start_time.localeCompare(b.start_time)))
const view = ref('table')

const timelineItems = computed(() =>
  sorted.value
    .filter((a) => a.status !== 'cancelled')
    .map((a) => ({ key: a.id, rep_id: a.rep_id, mro_id: a.mro_id, start_time: a.start_time, end_time: a.end_time, tone: TONE[a.status] })),
)
const timelineRange = computed(() => ({
  start: range.value.start ?? sorted.value[0]?.start_time ?? startOfDay(),
  end: range.value.end ?? (sorted.value.reduce((max, a) => (a.end_time > max ? a.end_time : max), '') || addDays(startOfDay(), 14)),
}))
const proposed = computed(() => assignments.value.filter((a) => a.status === 'proposed'))

async function setStatus(a, status) {
  try {
    await api.assignments.setStatus(a.id, status)
    toast.success(`Assignment #${a.id} → ${titleCase(status)}`)
    reload()
  } catch (e) {
    toast.error(e.message)
  }
}

async function confirmAllProposed() {
  const outcomes = await Promise.allSettled(proposed.value.map((a) => api.assignments.setStatus(a.id, 'confirmed')))
  const failed = outcomes.filter((o) => o.status === 'rejected')
  if (failed.length) toast.error(`${failed.length} could not be confirmed: ${failed[0].reason.message}`)
  else toast.success(`${outcomes.length} assignment(s) confirmed`)
  reload()
}

// ---------- Manual assignment ----------
const showForm = ref(false)
const save = useSubmit()
const form = reactive({})

function openCreate() {
  const start = addDays(startOfDay(), 1)
  start.setHours(7)
  Object.assign(form, {
    rep_id: '',
    mro_id: reference.mros[0]?.id ?? '',
    aircraft_type_id: '',
    start_time: toLocalInput(start),
    end_time: toLocalInput(new Date(start.getTime() + 12 * 36e5)),
    status: 'proposed',
    overtime_type: 'none',
    overtime_hours: 0,
    travel_hours: 0,
  })
  save.error.value = ''
  showForm.value = true
}

async function submit() {
  const body = {
    ...form,
    aircraft_type_id: form.aircraft_type_id || null,
    start_time: toIso(form.start_time),
    end_time: toIso(form.end_time),
    overtime_hours: Number(form.overtime_hours),
    travel_hours: Number(form.travel_hours),
  }
  if (await save.run(() => api.assignments.create(body), 'Assignment created')) {
    showForm.value = false
    reload()
  }
}
</script>

<template>
  <div>
    <PageHeader title="Assignments" subtitle="Review proposals, confirm the schedule and track work in progress.">
      <button v-if="proposed.length" class="btn btn--accent" @click="confirmAllProposed">Confirm {{ proposed.length }} proposed</button>
      <button class="btn btn--primary" @click="openCreate">+ Manual assignment</button>
    </PageHeader>

    <div class="card">
      <form class="filters" @submit.prevent="reload">
        <label class="field">
          <span>Rep</span>
          <select v-model="filters.rep_id">
            <option value="">All reps</option>
            <option v-for="r in reference.reps" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </label>
        <label class="field">
          <span>MRO</span>
          <select v-model="filters.mro_id">
            <option value="">All</option>
            <option v-for="m in reference.mros" :key="m.id" :value="m.id">{{ m.facility_name }}</option>
          </select>
        </label>
        <label class="field">
          <span>Status</span>
          <select v-model="filters.status">
            <option value="">All</option>
            <option v-for="s in Object.keys(TONE)" :key="s" :value="s">{{ titleCase(s) }}</option>
          </select>
        </label>
        <label class="field"><span>From</span><input v-model="filters.start" type="date" /></label>
        <label class="field"><span>To</span><input v-model="filters.end" type="date" /></label>
        <button class="btn btn--ghost">Apply</button>
        <div class="seg" style="margin-left: auto">
          <button type="button" :class="{ on: view === 'table' }" @click="view = 'table'">Table</button>
          <button type="button" :class="{ on: view === 'timeline' }" @click="view = 'timeline'">Timeline</button>
        </div>
      </form>

      <div v-if="loading" class="loading"><span class="spinner" /> Loading…</div>
      <ScheduleTimeline v-else-if="view === 'timeline'" :items="timelineItems" :start="timelineRange.start" :end="timelineRange.end" />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>#</th><th>Rep</th><th>MRO</th><th>Aircraft</th><th>Start</th><th>End</th><th>OT</th><th>Travel</th><th>Status</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="a in sorted" :key="a.id">
              <td class="muted">{{ a.id }}</td>
              <td><strong>{{ reference.repName(a.rep_id) }}</strong></td>
              <td>{{ reference.mroName(a.mro_id) }}</td>
              <td>{{ reference.aircraftName(a.aircraft_type_id) }}</td>
              <td>{{ fmtDateTime(a.start_time) }}</td>
              <td>{{ fmtDateTime(a.end_time) }}</td>
              <td>
                <span v-if="a.overtime_type !== 'none'">{{ num(a.overtime_hours) }} h <small class="muted">{{ a.overtime_type }}</small></span>
                <span v-else class="muted">—</span>
              </td>
              <td>{{ num(a.travel_hours) }} h</td>
              <td><StatusBadge :value="a.status" /></td>
              <td class="actions">
                <button
                  v-for="s in NEXT[a.status] || []"
                  :key="s"
                  class="btn btn--sm"
                  :class="s === 'cancelled' ? 'btn--danger' : 'btn--ghost'"
                  @click="setStatus(a, s)"
                >
                  {{ ACTION_LABEL[s] }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!sorted.length" class="empty">No assignments in this window.</div>
      </div>
    </div>

    <BaseModal v-if="showForm" title="Manual assignment" wide @close="showForm = false">
      <form id="assign-form" class="grid grid-3" @submit.prevent="submit">
        <label class="field">
          <span>Rep *</span>
          <select v-model="form.rep_id" required>
            <option value="" disabled>Select…</option>
            <option v-for="r in reference.reps.filter((x) => x.active)" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </label>
        <label class="field">
          <span>MRO *</span>
          <select v-model="form.mro_id" required>
            <option v-for="m in reference.mros" :key="m.id" :value="m.id">{{ m.facility_name }}</option>
          </select>
        </label>
        <label class="field">
          <span>Aircraft type</span>
          <select v-model="form.aircraft_type_id">
            <option value="">—</option>
            <option v-for="t in reference.aircraftTypes" :key="t.id" :value="t.id">{{ t.model_name }}</option>
          </select>
        </label>
        <label class="field"><span>Start *</span><input v-model="form.start_time" type="datetime-local" required /></label>
        <label class="field"><span>End *</span><input v-model="form.end_time" type="datetime-local" required /></label>
        <label class="field">
          <span>Status</span>
          <select v-model="form.status">
            <option value="proposed">Proposed</option>
            <option value="confirmed">Confirmed</option>
          </select>
        </label>
        <label class="field">
          <span>Overtime type</span>
          <select v-model="form.overtime_type">
            <option value="none">None</option>
            <option value="voluntary">Voluntary</option>
            <option value="mandatory">Mandatory</option>
          </select>
        </label>
        <label class="field"><span>Overtime hours</span><input v-model="form.overtime_hours" type="number" min="0" step="0.5" /></label>
        <label class="field"><span>Travel hours</span><input v-model="form.travel_hours" type="number" min="0" max="24" step="0.25" /></label>
        <p v-if="save.error.value" class="form-error span-all">{{ save.error.value }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" @click="showForm = false">Cancel</button>
        <button class="btn btn--primary" form="assign-form" :disabled="save.busy.value">Create</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.seg {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  align-self: flex-end;
}
.seg button {
  border: 0;
  background: var(--surface);
  padding: 0.55rem 0.9rem;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  color: var(--muted);
}
.seg button.on {
  background: var(--primary);
  color: #fff;
}
</style>
