<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '@/api'
import { useResource } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useToastStore } from '@/stores/toast'
import BaseModal from '@/components/BaseModal.vue'
import PageHeader from '@/components/PageHeader.vue'
import { fmtDate, fmtDateTime, titleCase } from '@/utils/format'

const reference = useReferenceStore()
const toast = useToastStore()

const days = ref(60)
const { data: due, loading, reload } = useResource(() => api.training.due(days.value))
watch(days, reload)

// Dates submitted by the training department, waiting for the scheduler.
const { data: types } = useResource(() => api.training.types())
const typeName = (id) => types.value.find((t) => t.id === id)?.name ?? `Type ${id}`
const { data: pending, loading: pendingLoading, reload: reloadPending } = useResource(async () => {
  await reference.load()
  return api.training.records({ status: 'submitted' })
})
const busy = ref(false)

async function approve(record) {
  busy.value = true
  try {
    const res = await api.training.approve(record.id)
    const n = res.warnings.length
    toast.success(n ? `Training approved with ${n} warning(s); see Alerts` : 'Training approved')
    reloadPending()
    reload()
  } catch (e) {
    toast.error(e.message)
  } finally {
    busy.value = false
  }
}

const rejecting = ref(null)
const rejectNote = ref('')
function openReject(record) {
  rejecting.value = record
  rejectNote.value = ''
}
async function reject() {
  busy.value = true
  try {
    await api.training.reject(rejecting.value.id, rejectNote.value.trim())
    toast.success('Training sent back to the training department')
    rejecting.value = null
    reloadPending()
  } catch (e) {
    toast.error(e.message)
  } finally {
    busy.value = false
  }
}

// Certification status: one row per rep and aircraft type.
const { data: certs, loading: certsLoading } = useResource(async () => {
  await reference.load()
  const active = reference.reps.filter((r) => r.active)
  const lists = await Promise.all(active.map((r) => api.reps.certifications(r.id)))
  return active.flatMap((r, i) => lists[i].map((c) => ({ ...c, rep_id: r.id })))
})

const today = new Date().toISOString().slice(0, 10)
function certStatus(c) {
  if (!c.expires_on) return 'active'
  if (c.expires_on < today) return 'expired'
  const soon = new Date()
  soon.setDate(soon.getDate() + days.value)
  return c.expires_on <= soon.toISOString().slice(0, 10) ? 'expiring' : 'active'
}
const CERT_TONE = { active: 'success', expiring: 'warning', expired: 'danger' }
const certRows = computed(() =>
  certs.value
    .map((c) => ({ ...c, status: certStatus(c) }))
    .sort((a, b) => (a.expires_on || '9999').localeCompare(b.expires_on || '9999')),
)
const expired = computed(() => due.value.filter((d) => d.days_left === null || d.days_left < 0).length)
</script>

<template>
  <div>
    <PageHeader title="Training" subtitle="Training dates to approve, upcoming expiries, and certification status.">
      <label class="field">
        <span>Due within</span>
        <select v-model.number="days">
          <option v-for="d in [30, 60, 90, 180]" :key="d" :value="d">{{ d }} days</option>
        </select>
      </label>
    </PageHeader>

    <div class="grid grid-3">
      <div class="card stat">
        <div class="stat__label">Due</div>
        <div class="stat__value">{{ due.length }}</div>
        <div class="stat__hint">Expiring within {{ days }} days or overdue</div>
      </div>
      <div class="card stat">
        <div class="stat__label">Overdue</div>
        <div class="stat__value">{{ expired }}</div>
        <div class="stat__hint">Expired or never completed</div>
      </div>
      <div class="card stat">
        <div class="stat__label">Certifications</div>
        <div class="stat__value">{{ certRows.length }}</div>
        <div class="stat__hint">Across active reps</div>
      </div>
    </div>

    <div class="card" style="margin-top: 1.25rem">
      <div class="card__head"><h2>Pending approval</h2></div>
      <div v-if="pendingLoading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Rep</th><th>Training</th><th>Start</th><th>End</th><th>Notes</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="r in pending" :key="r.id">
              <td><strong>{{ reference.repName(r.rep_id) }}</strong></td>
              <td>{{ typeName(r.training_type_id) }}</td>
              <td>{{ fmtDateTime(r.scheduled_start) }}</td>
              <td>{{ fmtDateTime(r.scheduled_end) }}</td>
              <td>{{ r.notes || '—' }}</td>
              <td class="actions">
                <button class="btn btn--primary btn--sm" :disabled="busy" @click="approve(r)">Accept</button>
                <button class="btn btn--ghost btn--sm" :disabled="busy" @click="openReject(r)">Reject</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!pending.length" class="empty">No training dates waiting for approval.</div>
      </div>
    </div>

    <div class="card" style="margin-top: 1.25rem">
      <div class="card__head"><h2>Upcoming expiries</h2></div>
      <div v-if="loading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Rep</th><th>Training</th><th>Location</th><th>Expires</th><th>Days left</th><th>Next session</th></tr>
          </thead>
          <tbody>
            <tr v-for="d in due" :key="`${d.rep_id}-${d.training_type_id}`">
              <td><strong>{{ d.rep_name }}</strong></td>
              <td>{{ d.training_type_name }}<span v-if="d.is_mandatory" class="muted"> · mandatory</span></td>
              <td>{{ d.location }}</td>
              <td>{{ d.expires_on ? fmtDate(d.expires_on) : 'Never completed' }}</td>
              <td>
                <span class="badge" :class="d.days_left === null || d.days_left < 0 ? 'badge--danger' : 'badge--warning'">
                  {{ d.days_left === null ? 'Not completed' : d.days_left < 0 ? `${-d.days_left} days overdue` : `${d.days_left} days` }}
                </span>
              </td>
              <td>{{ d.next_scheduled_start ? fmtDateTime(d.next_scheduled_start) : '—' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!due.length" class="empty">Nothing due in the next {{ days }} days.</div>
      </div>
    </div>

    <div class="card" style="margin-top: 1.25rem">
      <div class="card__head"><h2>Certification status</h2></div>
      <div v-if="certsLoading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Rep</th><th>Aircraft type</th><th>Certified</th><th>Expires</th><th>Status</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in certRows" :key="`${c.rep_id}-${c.aircraft_type_id}`">
              <td><strong>{{ reference.repName(c.rep_id) }}</strong></td>
              <td>{{ reference.aircraftName(c.aircraft_type_id) }}</td>
              <td>{{ fmtDate(c.certified_on) }}</td>
              <td>{{ fmtDate(c.expires_on) }}</td>
              <td><span class="badge" :class="`badge--${CERT_TONE[c.status]}`">{{ titleCase(c.status) }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-if="!certRows.length" class="empty">No certifications on file.</div>
      </div>
    </div>

    <BaseModal v-if="rejecting" title="Reject training dates" @close="rejecting = null">
      <form id="reject-form" @submit.prevent="reject">
        <p>
          {{ reference.repName(rejecting.rep_id) }} · {{ typeName(rejecting.training_type_id) }},
          {{ fmtDateTime(rejecting.scheduled_start) }} to {{ fmtDateTime(rejecting.scheduled_end) }}
        </p>
        <label class="field">
          <span>Note for the training department</span>
          <textarea v-model="rejectNote" maxlength="400" placeholder="Falls mid-rotation; move to the first or last day, or a day off" />
        </label>
      </form>
      <template #footer>
        <button class="btn btn--ghost" @click="rejecting = null">Cancel</button>
        <button class="btn btn--primary" form="reject-form" :disabled="busy">Reject</button>
      </template>
    </BaseModal>
  </div>
</template>
