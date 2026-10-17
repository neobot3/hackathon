<script setup>
import { computed, reactive, ref } from 'vue'
import { api } from '@/api'
import { useResource, useSubmit } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useToastStore } from '@/stores/toast'
import BaseModal from '@/components/BaseModal.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { diff, fmtDate, num } from '@/utils/format'

const reference = useReferenceStore()
const toast = useToastStore()
const { data: patterns } = useResource(() => api.cba.shiftPatterns())

const search = ref('')
const statusFilter = ref('active')

const reps = computed(() => {
  const q = search.value.trim().toLowerCase()
  return reference.reps.filter((r) => {
    if (statusFilter.value === 'active' && !r.active) return false
    if (statusFilter.value === 'inactive' && r.active) return false
    return !q || [r.name, r.email, r.home_base, r.classification].some((v) => v?.toLowerCase().includes(q))
  })
})
const homeBases = computed(() => [...new Set(reference.reps.map((r) => r.home_base))].sort())

// ---------- Create / edit ----------
const EMPTY = {
  name: '',
  email: '',
  home_base: '',
  classification: '',
  cba_group: '',
  union_seniority_date: '',
  shift_pattern_code: '',
  shift_cycle_start: '',
  banked_ot_hours: 0,
  certified_aircraft_type_ids: [],
}
const editing = ref(null)
const showForm = ref(false)
const form = reactive({ ...EMPTY })
const save = useSubmit()

function openCreate() {
  editing.value = null
  Object.assign(form, { ...EMPTY, certified_aircraft_type_ids: [] })
  save.error.value = ''
  showForm.value = true
}

function openEdit(rep) {
  editing.value = rep
  Object.assign(form, EMPTY, Object.fromEntries(Object.keys(EMPTY).map((k) => [k, rep[k] ?? EMPTY[k]])))
  save.error.value = ''
  showForm.value = true
}

function toggleType(id) {
  const ids = form.certified_aircraft_type_ids
  form.certified_aircraft_type_ids = ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]
}

function payload() {
  const body = { ...form, cba_group: form.cba_group === '' ? null : Number(form.cba_group), banked_ot_hours: Number(form.banked_ot_hours) }
  for (const k of ['email', 'classification', 'union_seniority_date', 'shift_pattern_code', 'shift_cycle_start']) {
    if (body[k] === '') body[k] = null
  }
  return body
}

async function submit() {
  const body = payload()
  let ok
  if (editing.value) {
    const { certified_aircraft_type_ids: _ignored, ...rest } = body
    const changes = diff(editing.value, rest)
    if (!Object.keys(changes).length) return (showForm.value = false)
    ok = await save.run(() => api.reps.update(editing.value.id, changes), 'Rep updated')
  } else {
    ok = await save.run(() => api.reps.create(body), 'Rep added')
  }
  if (ok) {
    showForm.value = false
    reference.load(true)
  }
}

async function toggleActive(rep) {
  try {
    await api.reps.update(rep.id, { active: !rep.active })
    toast.success(`${rep.name} ${rep.active ? 'deactivated' : 'reactivated'}`)
    reference.load(true)
  } catch (e) {
    toast.error(e.message)
  }
}

// ---------- Certifications ----------
const certRep = ref(null)
const certs = ref([])
const certForm = reactive({ aircraft_type_id: '', certified_on: '', expires_on: '' })
const certSave = useSubmit()

async function openCerts(rep) {
  certRep.value = rep
  Object.assign(certForm, { aircraft_type_id: '', certified_on: '', expires_on: '' })
  certSave.error.value = ''
  await loadCerts()
}

async function loadCerts() {
  try {
    certs.value = await api.reps.certifications(certRep.value.id)
  } catch (e) {
    toast.error(e.message)
  }
}

function editCert(c) {
  Object.assign(certForm, { aircraft_type_id: c.aircraft_type_id, certified_on: c.certified_on || '', expires_on: c.expires_on || '' })
}

async function saveCert() {
  const ok = await certSave.run(
    () =>
      api.reps.upsertCertification(certRep.value.id, certForm.aircraft_type_id, {
        certified_on: certForm.certified_on || null,
        expires_on: certForm.expires_on || null,
      }),
    'Certification saved',
  )
  if (ok) {
    Object.assign(certForm, { aircraft_type_id: '', certified_on: '', expires_on: '' })
    await loadCerts()
    reference.load(true)
  }
}

async function removeCert(c) {
  if (!confirm(`Remove ${reference.aircraftName(c.aircraft_type_id)} certification?`)) return
  const ok = await certSave.run(() => api.reps.deleteCertification(certRep.value.id, c.aircraft_type_id), 'Certification removed')
  if (ok) {
    await loadCerts()
    reference.load(true)
  }
}

const isExpired = (c) => c.expires_on && new Date(c.expires_on) < new Date()
</script>

<template>
  <div>
    <PageHeader title="Tech reps" subtitle="Onboard reps, set their CBA profile and manage aircraft certifications.">
      <button class="btn btn--primary" @click="openCreate">+ Add tech rep</button>
    </PageHeader>

    <div class="card">
      <div class="filters">
        <label class="field" style="flex: 1">
          <span>Search</span>
          <input v-model="search" placeholder="Name, email, base…" />
        </label>
        <label class="field">
          <span>Status</span>
          <select v-model="statusFilter">
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="all">All</option>
          </select>
        </label>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Home base</th>
              <th>Classification</th>
              <th>Group</th>
              <th>Shift</th>
              <th>Aircraft</th>
              <th>Banked OT</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in reps" :key="r.id">
              <td>
                <strong>{{ r.name }}</strong>
                <div class="muted" style="font-size: 0.8rem">{{ r.email || '—' }}</div>
              </td>
              <td>{{ r.home_base }}</td>
              <td>{{ r.classification || '—' }}</td>
              <td>{{ r.cba_group ?? '—' }}</td>
              <td class="mono">{{ r.shift_pattern_code || '—' }}</td>
              <td>
                <div class="chips">
                  <span v-for="id in r.certified_aircraft_type_ids" :key="id" class="badge badge--info">{{ reference.aircraftName(id) }}</span>
                  <span v-if="!r.certified_aircraft_type_ids.length" class="muted">—</span>
                </div>
              </td>
              <td>{{ num(r.banked_ot_hours) }} h</td>
              <td><StatusBadge :value="r.active" /></td>
              <td class="actions">
                <button class="btn btn--ghost btn--sm" @click="openEdit(r)">Edit</button>
                <button class="btn btn--ghost btn--sm" @click="openCerts(r)">Certs</button>
                <button class="btn btn--sm" :class="r.active ? 'btn--danger' : 'btn--ghost'" @click="toggleActive(r)">
                  {{ r.active ? 'Deactivate' : 'Activate' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!reps.length" class="empty">No reps match.</div>
      </div>
    </div>

    <BaseModal v-if="showForm" :title="editing ? `Edit ${editing.name}` : 'Add tech rep'" wide @close="showForm = false">
      <form id="rep-form" class="grid grid-3" @submit.prevent="submit">
        <label class="field span-2"><span>Full name *</span><input v-model="form.name" required maxlength="200" /></label>
        <label class="field"><span>Email</span><input v-model="form.email" type="email" maxlength="254" /></label>
        <label class="field">
          <span>Home base *</span>
          <input v-model="form.home_base" list="home-bases" required maxlength="200" />
          <datalist id="home-bases"><option v-for="b in homeBases" :key="b" :value="b" /></datalist>
        </label>
        <label class="field"><span>Classification</span><input v-model="form.classification" maxlength="60" /></label>
        <label class="field">
          <span>CBA group</span>
          <select v-model="form.cba_group">
            <option value="">—</option>
            <option v-for="g in 5" :key="g" :value="g">Group {{ g }}</option>
          </select>
        </label>
        <label class="field"><span>Union seniority date</span><input v-model="form.union_seniority_date" type="date" /></label>
        <label class="field">
          <span>Shift pattern</span>
          <select v-model="form.shift_pattern_code">
            <option value="">—</option>
            <option v-for="p in patterns" :key="p.code" :value="p.code">{{ p.code }} · {{ p.description }}</option>
          </select>
        </label>
        <label class="field"><span>Shift cycle start</span><input v-model="form.shift_cycle_start" type="date" /></label>
        <label class="field">
          <span>Banked OT hours</span>
          <input v-model="form.banked_ot_hours" type="number" min="0" max="80" step="0.5" />
        </label>
        <div v-if="!editing" class="field span-all">
          <span>Certified aircraft types</span>
          <div class="chips">
            <button
              v-for="t in reference.aircraftTypes"
              :key="t.id"
              type="button"
              class="chip"
              :class="{ 'chip--on': form.certified_aircraft_type_ids.includes(t.id) }"
              @click="toggleType(t.id)"
            >
              {{ t.model_name }}
            </button>
          </div>
          <small>Add dates later from the Certs action.</small>
        </div>
        <p v-if="save.error.value" class="form-error span-all">{{ save.error.value }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" @click="showForm = false">Cancel</button>
        <button class="btn btn--primary" form="rep-form" :disabled="save.busy.value">{{ editing ? 'Save changes' : 'Add rep' }}</button>
      </template>
    </BaseModal>

    <BaseModal v-if="certRep" :title="`Certifications · ${certRep.name}`" wide @close="certRep = null">
      <div class="table-wrap card" style="margin-bottom: 1.25rem">
        <table class="table">
          <thead>
            <tr><th>Aircraft type</th><th>Certified on</th><th>Expires on</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="c in certs" :key="c.aircraft_type_id">
              <td><strong>{{ reference.aircraftName(c.aircraft_type_id) }}</strong></td>
              <td>{{ fmtDate(c.certified_on) }}</td>
              <td>
                {{ fmtDate(c.expires_on) }}
                <span v-if="isExpired(c)" class="badge badge--danger">Expired</span>
              </td>
              <td class="actions">
                <button class="btn btn--ghost btn--sm" @click="editCert(c)">Edit</button>
                <button class="btn btn--danger btn--sm" @click="removeCert(c)">Remove</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!certs.length" class="empty">No certifications yet.</div>
      </div>

      <form class="grid grid-4" @submit.prevent="saveCert">
        <label class="field">
          <span>Aircraft type *</span>
          <select v-model="certForm.aircraft_type_id" required>
            <option value="" disabled>Select…</option>
            <option v-for="t in reference.aircraftTypes" :key="t.id" :value="t.id">{{ t.model_name }}</option>
          </select>
        </label>
        <label class="field"><span>Certified on</span><input v-model="certForm.certified_on" type="date" /></label>
        <label class="field"><span>Expires on</span><input v-model="certForm.expires_on" type="date" /></label>
        <div class="field" style="justify-content: flex-end">
          <button class="btn btn--primary" :disabled="certSave.busy.value">Save certification</button>
        </div>
        <p v-if="certSave.error.value" class="form-error span-all">{{ certSave.error.value }}</p>
      </form>
    </BaseModal>
  </div>
</template>
