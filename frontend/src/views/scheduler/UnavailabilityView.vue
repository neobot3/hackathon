<script setup>
import { computed, reactive, ref } from 'vue'
import { api } from '@/api'
import { useResource, useSubmit } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useToastStore } from '@/stores/toast'
import BaseModal from '@/components/BaseModal.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { addDays, fmtDateTime, startOfDay, titleCase, toDateInput, toIso, toLocalInput } from '@/utils/format'

const REASONS = ['vacation', 'sick', 'training', 'bereavement', 'parental', 'union_leave', 'unpaid_leave', 'jury_duty', 'other']

const reference = useReferenceStore()
const toast = useToastStore()

const filters = reactive({
  rep_id: '',
  status: '',
  start: toDateInput(addDays(new Date(), -7)),
  end: toDateInput(addDays(new Date(), 60)),
})
const { data: entries, loading, reload } = useResource(() =>
  api.unavailability.list({
    ...filters,
    start: filters.start ? toIso(`${filters.start}T00:00`) : null,
    end: filters.end ? toIso(`${filters.end}T23:59`) : null,
  }),
)
const sorted = computed(() => [...entries.value].sort((a, b) => a.start_time.localeCompare(b.start_time)))
const pending = computed(() => entries.value.filter((e) => e.status === 'requested').length)
const activeReps = computed(() => reference.reps.filter((r) => r.active))

const showForm = ref(false)
const save = useSubmit()
const form = reactive({})

function openCreate() {
  const start = addDays(startOfDay(), 1)
  Object.assign(form, {
    rep_id: '',
    reason: 'vacation',
    status: 'approved',
    start_time: toLocalInput(start),
    end_time: toLocalInput(addDays(start, 1)),
    notes: '',
  })
  save.error.value = ''
  showForm.value = true
}

async function submit() {
  const body = { ...form, start_time: toIso(form.start_time), end_time: toIso(form.end_time), notes: form.notes.trim() || null }
  if (await save.run(() => api.unavailability.create(body), 'Unavailability recorded')) {
    showForm.value = false
    reload()
  }
}

async function setStatus(entry, status) {
  try {
    await api.unavailability.setStatus(entry.id, status)
    toast.success(`Marked ${status}`)
    reload()
  } catch (e) {
    toast.error(e.message)
  }
}
</script>

<template>
  <div>
    <PageHeader title="Rep unavailability" subtitle="Leave and other absences. Approved entries block assignments.">
      <span v-if="pending" class="badge badge--warning" style="align-self: center">{{ pending }} awaiting approval</span>
      <button class="btn btn--primary" @click="openCreate">+ Record absence</button>
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
          <span>Status</span>
          <select v-model="filters.status">
            <option value="">All</option>
            <option v-for="s in ['requested', 'approved', 'denied', 'cancelled']" :key="s" :value="s">{{ titleCase(s) }}</option>
          </select>
        </label>
        <label class="field"><span>From</span><input v-model="filters.start" type="date" /></label>
        <label class="field"><span>To</span><input v-model="filters.end" type="date" /></label>
        <button class="btn btn--ghost">Apply</button>
      </form>

      <div v-if="loading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead><tr><th>Rep</th><th>Reason</th><th>From</th><th>To</th><th>Status</th><th>Notes</th><th /></tr></thead>
          <tbody>
            <tr v-for="e in sorted" :key="e.id">
              <td><strong>{{ reference.repName(e.rep_id) }}</strong></td>
              <td>{{ titleCase(e.reason) }}</td>
              <td>{{ fmtDateTime(e.start_time) }}</td>
              <td>{{ fmtDateTime(e.end_time) }}</td>
              <td><StatusBadge :value="e.status" /></td>
              <td class="muted" style="max-width: 220px">{{ e.notes || '—' }}</td>
              <td class="actions">
                <template v-if="e.status === 'requested'">
                  <button class="btn btn--ghost btn--sm" @click="setStatus(e, 'approved')">Approve</button>
                  <button class="btn btn--danger btn--sm" @click="setStatus(e, 'denied')">Deny</button>
                </template>
                <button v-if="e.status === 'approved' || e.status === 'requested'" class="btn-link" @click="setStatus(e, 'cancelled')">Cancel</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!sorted.length" class="empty">No unavailability in this window.</div>
      </div>
    </div>

    <BaseModal v-if="showForm" title="Record unavailability" @close="showForm = false">
      <form id="unavail-form" class="grid grid-2" @submit.prevent="submit">
        <label class="field span-all">
          <span>Rep *</span>
          <select v-model="form.rep_id" required>
            <option value="" disabled>Select a rep…</option>
            <option v-for="r in activeReps" :key="r.id" :value="r.id">{{ r.name }} · {{ r.home_base }}</option>
          </select>
        </label>
        <label class="field">
          <span>Reason *</span>
          <select v-model="form.reason">
            <option v-for="r in REASONS" :key="r" :value="r">{{ titleCase(r) }}</option>
          </select>
        </label>
        <label class="field">
          <span>Status</span>
          <select v-model="form.status">
            <option value="requested">Requested</option>
            <option value="approved">Approved</option>
          </select>
        </label>
        <label class="field"><span>Start *</span><input v-model="form.start_time" type="datetime-local" required /></label>
        <label class="field"><span>End *</span><input v-model="form.end_time" type="datetime-local" required /></label>
        <label class="field span-all"><span>Notes</span><textarea v-model="form.notes" maxlength="500" /></label>
        <p v-if="save.error.value" class="form-error span-all">{{ save.error.value }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" @click="showForm = false">Cancel</button>
        <button class="btn btn--primary" form="unavail-form" :disabled="save.busy.value">Save</button>
      </template>
    </BaseModal>
  </div>
</template>
