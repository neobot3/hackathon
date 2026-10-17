<script setup>
import { computed, reactive, ref } from 'vue'
import { api } from '@/api'
import { useResource, useSubmit } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useToastStore } from '@/stores/toast'
import BaseModal from '@/components/BaseModal.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { addDays, fmtDateTime, hoursBetween, startOfDay, toDateInput, toIso, toLocalInput } from '@/utils/format'

const reference = useReferenceStore()
const toast = useToastStore()

const filters = reactive({
  mro_id: '',
  demand_type: '',
  status: 'open',
  start: toDateInput(startOfDay()),
  end: toDateInput(addDays(new Date(), 30)),
})
const { data: demands, loading, reload } = useResource(() =>
  api.demands.list({
    ...filters,
    start: filters.start ? toIso(`${filters.start}T00:00`) : null,
    end: filters.end ? toIso(`${filters.end}T23:59`) : null,
  }),
)
const sorted = computed(() => [...demands.value].sort((a, b) => a.start_time.localeCompare(b.start_time)))

// ---------- Create ----------
const showForm = ref(false)
const save = useSubmit()
const form = reactive({})

function openCreate() {
  const start = addDays(startOfDay(), 1)
  start.setHours(7)
  Object.assign(form, {
    mro_id: reference.mros[0]?.id ?? '',
    aircraft_type_id: reference.aircraftTypes[0]?.id ?? '',
    demand_type: 'base_coverage',
    start_time: toLocalInput(start),
    end_time: toLocalInput(new Date(start.getTime() + 12 * 36e5)),
    reps_needed: 1,
    priority: 3,
    notes: '',
  })
  save.error.value = ''
  showForm.value = true
}

async function submit() {
  const body = {
    ...form,
    start_time: toIso(form.start_time),
    end_time: toIso(form.end_time),
    reps_needed: Number(form.reps_needed),
    priority: Number(form.priority),
    notes: form.notes.trim() || null,
  }
  if (await save.run(() => api.demands.create(body), 'Demand created')) {
    showForm.value = false
    reload()
  }
}

async function setStatus(d, status) {
  try {
    await api.demands.setStatus(d.id, status)
    toast.success(`Demand #${d.id} marked ${status}`)
    reload()
  } catch (e) {
    toast.error(e.message)
  }
}

// ---------- Rep responses ----------
const respDemand = ref(null)
const responses = ref([])

const eligibleReps = computed(() =>
  respDemand.value
    ? reference.reps
        .filter((r) => r.active && r.certified_aircraft_type_ids.includes(respDemand.value.aircraft_type_id))
        .map((r) => ({ ...r, response: responses.value.find((x) => x.rep_id === r.id) }))
    : [],
)

async function openResponses(d) {
  respDemand.value = d
  try {
    responses.value = await api.demands.responses(d.id)
  } catch (e) {
    toast.error(e.message)
  }
}

async function respond(rep, value) {
  try {
    if (value) await api.demands.setResponse(respDemand.value.id, rep.id, value)
    else await api.demands.deleteResponse(respDemand.value.id, rep.id)
    responses.value = await api.demands.responses(respDemand.value.id)
  } catch (e) {
    toast.error(e.message)
  }
}
</script>

<template>
  <div>
    <PageHeader title="MRO demand" subtitle="Base coverage and AOG requests the scheduler must fill.">
      <button class="btn btn--primary" @click="openCreate">+ New demand</button>
    </PageHeader>

    <div class="card">
      <form class="filters" @submit.prevent="reload">
        <label class="field">
          <span>MRO</span>
          <select v-model="filters.mro_id">
            <option value="">All</option>
            <option v-for="m in reference.mros" :key="m.id" :value="m.id">{{ m.facility_name }}</option>
          </select>
        </label>
        <label class="field">
          <span>Type</span>
          <select v-model="filters.demand_type">
            <option value="">All</option>
            <option value="base_coverage">Base coverage</option>
            <option value="aog">AOG</option>
          </select>
        </label>
        <label class="field">
          <span>Status</span>
          <select v-model="filters.status">
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="filled">Filled</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </label>
        <label class="field"><span>From</span><input v-model="filters.start" type="date" /></label>
        <label class="field"><span>To</span><input v-model="filters.end" type="date" /></label>
        <button class="btn btn--ghost">Apply</button>
      </form>

      <div v-if="loading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>#</th><th>MRO</th><th>Aircraft</th><th>Type</th><th>Window</th><th>Reps</th><th>Priority</th><th>Status</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="d in sorted" :key="d.id">
              <td class="muted">{{ d.id }}</td>
              <td><strong>{{ reference.mroName(d.mro_id) }}</strong></td>
              <td>{{ reference.aircraftName(d.aircraft_type_id) }}</td>
              <td><StatusBadge :value="d.demand_type" /></td>
              <td>
                {{ fmtDateTime(d.start_time) }}
                <div class="muted" style="font-size: 0.78rem">→ {{ fmtDateTime(d.end_time) }} · {{ hoursBetween(d.start_time, d.end_time).toFixed(1) }} h</div>
              </td>
              <td>{{ d.reps_needed }}</td>
              <td>
                <span class="prio" :title="`Priority ${d.priority}`">
                  <i v-for="n in 5" :key="n" :class="{ on: n <= d.priority }" />
                </span>
              </td>
              <td><StatusBadge :value="d.status" /></td>
              <td class="actions">
                <button class="btn btn--ghost btn--sm" @click="openResponses(d)">Responses</button>
                <template v-if="d.status === 'open'">
                  <button class="btn btn--ghost btn--sm" @click="setStatus(d, 'filled')">Filled</button>
                  <button class="btn btn--danger btn--sm" @click="setStatus(d, 'cancelled')">Cancel</button>
                </template>
                <button v-else class="btn btn--ghost btn--sm" @click="setStatus(d, 'open')">Reopen</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!sorted.length" class="empty">No demand matches these filters.</div>
      </div>
    </div>

    <BaseModal v-if="showForm" title="New MRO demand" wide @close="showForm = false">
      <form id="demand-form" class="grid grid-3" @submit.prevent="submit">
        <label class="field">
          <span>MRO location *</span>
          <select v-model="form.mro_id" required>
            <option v-for="m in reference.mros" :key="m.id" :value="m.id">{{ m.facility_name }}</option>
          </select>
        </label>
        <label class="field">
          <span>Aircraft type *</span>
          <select v-model="form.aircraft_type_id" required>
            <option v-for="t in reference.aircraftTypes" :key="t.id" :value="t.id">{{ t.model_name }}</option>
          </select>
        </label>
        <label class="field">
          <span>Demand type</span>
          <select v-model="form.demand_type">
            <option value="base_coverage">Base coverage</option>
            <option value="aog">AOG (aircraft on ground)</option>
          </select>
        </label>
        <label class="field"><span>Start *</span><input v-model="form.start_time" type="datetime-local" required /></label>
        <label class="field"><span>End *</span><input v-model="form.end_time" type="datetime-local" required /></label>
        <label class="field"><span>Reps needed</span><input v-model="form.reps_needed" type="number" min="1" max="50" required /></label>
        <label class="field">
          <span>Priority (1 low – 5 high)</span>
          <input v-model="form.priority" type="range" min="1" max="5" />
          <small>Priority {{ form.priority }}</small>
        </label>
        <label class="field span-2"><span>Notes</span><textarea v-model="form.notes" maxlength="500" /></label>
        <p v-if="save.error.value" class="form-error span-all">{{ save.error.value }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" @click="showForm = false">Cancel</button>
        <button class="btn btn--primary" form="demand-form" :disabled="save.busy.value">Create demand</button>
      </template>
    </BaseModal>

    <BaseModal v-if="respDemand" :title="`Rep responses · Demand #${respDemand.id}`" wide @close="respDemand = null">
      <p class="muted" style="margin-top: 0">
        Active reps certified on <strong>{{ reference.aircraftName(respDemand.aircraft_type_id) }}</strong>. Reps who decline are only assigned
        when the scheduler run allows mandatory overtime.
      </p>
      <div class="card table-wrap">
        <table class="table">
          <thead><tr><th>Rep</th><th>Home base</th><th>Response</th><th /></tr></thead>
          <tbody>
            <tr v-for="r in eligibleReps" :key="r.id">
              <td><strong>{{ r.name }}</strong></td>
              <td>{{ r.home_base }}</td>
              <td>
                <StatusBadge v-if="r.response" :value="r.response.response" />
                <span v-else class="muted">No response</span>
              </td>
              <td class="actions">
                <button class="btn btn--ghost btn--sm" :disabled="r.response?.response === 'accepted'" @click="respond(r, 'accepted')">Accept</button>
                <button class="btn btn--ghost btn--sm" :disabled="r.response?.response === 'declined'" @click="respond(r, 'declined')">Decline</button>
                <button v-if="r.response" class="btn-link" @click="respond(r, null)">Clear</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!eligibleReps.length" class="empty">No active reps are certified on this aircraft type.</div>
      </div>
    </BaseModal>
  </div>
</template>

<style scoped>
.prio {
  display: inline-flex;
  gap: 3px;
}
.prio i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
}
.prio i.on {
  background: linear-gradient(135deg, var(--amber), var(--danger));
}
</style>
