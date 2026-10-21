<script setup>
import { computed, reactive, ref } from 'vue'
import { api } from '@/api'
import { useSubmit } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useToastStore } from '@/stores/toast'
import BaseModal from '@/components/BaseModal.vue'
import PageHeader from '@/components/PageHeader.vue'
import { diff } from '@/utils/format'

const reference = useReferenceStore()
const toast = useToastStore()
const save = useSubmit()

const timezones = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : []
const homeBases = computed(() => [...new Set(reference.reps.map((r) => r.home_base))].sort())

// ---------- Create / edit ----------
const editing = ref(null)
const showForm = ref(false)
const form = reactive({ facility_name: '', location: '', airport_code: '', timezone: 'UTC', covering_base: '' })

function open(mro = null) {
  editing.value = mro
  Object.assign(form, {
    facility_name: mro?.facility_name ?? '',
    location: mro?.location ?? '',
    airport_code: mro?.airport_code ?? '',
    timezone: mro?.timezone ?? 'America/Edmonton',
    covering_base: mro?.covering_base ?? '',
  })
  save.error.value = ''
  showForm.value = true
}

async function submit() {
  const body = {
    facility_name: form.facility_name.trim(),
    location: form.location.trim(),
    airport_code: form.airport_code.trim().toUpperCase() || null,
    timezone: form.timezone,
    covering_base: form.covering_base.trim() || null,
  }
  const ok = editing.value
    ? await save.run(() => api.mroLocations.update(editing.value.id, diff(editing.value, body)), 'MRO location updated')
    : await save.run(() => api.mroLocations.create(body), 'MRO location added')
  if (ok) {
    showForm.value = false
    reference.load(true)
  }
}

// ---------- Travel times ----------
const travelMro = ref(null)
const travel = ref([])
const travelForm = reactive({ home_base: '', travel_hours: '', distance_km: '' })
const travelSave = useSubmit()

async function openTravel(mro) {
  travelMro.value = mro
  Object.assign(travelForm, { home_base: '', travel_hours: '', distance_km: '' })
  travelSave.error.value = ''
  await loadTravel()
}

async function loadTravel() {
  try {
    travel.value = await api.mroLocations.travelTimes(travelMro.value.id)
  } catch (e) {
    toast.error(e.message)
  }
}

function editTravel(t) {
  Object.assign(travelForm, { home_base: t.home_base, travel_hours: t.travel_hours, distance_km: t.distance_km ?? '' })
}

async function saveTravel() {
  const ok = await travelSave.run(
    () =>
      api.mroLocations.upsertTravelTime(travelMro.value.id, travelForm.home_base.trim(), {
        travel_hours: Number(travelForm.travel_hours),
        distance_km: travelForm.distance_km === '' ? null : Number(travelForm.distance_km),
      }),
    'Travel time saved',
  )
  if (ok) {
    Object.assign(travelForm, { home_base: '', travel_hours: '', distance_km: '' })
    loadTravel()
  }
}

async function removeTravel(t) {
  if (!confirm(`Remove travel time from ${t.home_base}?`)) return
  if (await travelSave.run(() => api.mroLocations.deleteTravelTime(travelMro.value.id, t.home_base), 'Travel time removed')) loadTravel()
}
</script>

<template>
  <div>
    <PageHeader title="MRO locations" subtitle="Facilities that raise demand, their timezone and travel time from each home base.">
      <button class="btn btn--primary" @click="open()">+ Add MRO location</button>
    </PageHeader>

    <div class="card table-wrap">
      <table class="table">
        <thead>
          <tr><th>Facility</th><th>Code</th><th>Location</th><th>Timezone</th><th>Covered by</th><th /></tr>
        </thead>
        <tbody>
          <tr v-for="m in reference.mros" :key="m.id">
            <td><strong>{{ m.facility_name }}</strong></td>
            <td><span v-if="m.airport_code" class="badge badge--info mono">{{ m.airport_code }}</span><span v-else class="muted">—</span></td>
            <td>{{ m.location }}</td>
            <td class="mono">{{ m.timezone }}</td>
            <td>{{ m.covering_base || '—' }}</td>
            <td class="actions">
              <button class="btn btn--ghost btn--sm" @click="open(m)">Edit</button>
              <button class="btn btn--ghost btn--sm" @click="openTravel(m)">Travel times</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!reference.mros.length" class="empty">No MRO locations yet.</div>
    </div>

    <BaseModal v-if="showForm" :title="editing ? 'Edit MRO location' : 'Add MRO location'" @close="showForm = false">
      <form id="mro-form" class="grid grid-2" @submit.prevent="submit">
        <label class="field span-all"><span>Facility name *</span><input v-model="form.facility_name" required maxlength="200" /></label>
        <label class="field"><span>Location *</span><input v-model="form.location" required maxlength="200" placeholder="City, Province" /></label>
        <label class="field">
          <span>Airport code</span>
          <input v-model="form.airport_code" maxlength="3" pattern="[A-Za-z]{3}" placeholder="YYC" style="text-transform: uppercase" />
        </label>
        <label class="field span-all">
          <span>Timezone *</span>
          <input v-model="form.timezone" list="tz-list" required maxlength="64" />
          <datalist id="tz-list"><option v-for="tz in timezones" :key="tz" :value="tz" /></datalist>
        </label>
        <label class="field span-all">
          <span>Covering team (home base)</span>
          <input v-model="form.covering_base" maxlength="200" placeholder="YYC" />
        </label>
        <p v-if="save.error.value" class="form-error span-all">{{ save.error.value }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" @click="showForm = false">Cancel</button>
        <button class="btn btn--primary" form="mro-form" :disabled="save.busy.value">Save</button>
      </template>
    </BaseModal>

    <BaseModal v-if="travelMro" :title="`Travel times to ${travelMro.facility_name}`" wide @close="travelMro = null">
      <div class="card table-wrap" style="margin-bottom: 1.25rem">
        <table class="table">
          <thead>
            <tr><th>Home base</th><th>One-way hours</th><th>Distance</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="t in travel" :key="t.home_base">
              <td><strong>{{ t.home_base }}</strong></td>
              <td>{{ t.travel_hours }} h</td>
              <td>{{ t.distance_km != null ? `${t.distance_km} km` : '—' }}</td>
              <td class="actions">
                <button class="btn btn--ghost btn--sm" @click="editTravel(t)">Edit</button>
                <button class="btn btn--danger btn--sm" @click="removeTravel(t)">Remove</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!travel.length" class="empty">No travel times recorded.</div>
      </div>
      <form class="grid grid-4" @submit.prevent="saveTravel">
        <label class="field">
          <span>Home base *</span>
          <input v-model="travelForm.home_base" list="travel-bases" required maxlength="200" />
          <datalist id="travel-bases"><option v-for="b in homeBases" :key="b" :value="b" /></datalist>
          <small>Must match a rep's home base.</small>
        </label>
        <label class="field"><span>Travel hours *</span><input v-model="travelForm.travel_hours" type="number" min="0" max="24" step="0.25" required /></label>
        <label class="field"><span>Distance (km)</span><input v-model="travelForm.distance_km" type="number" min="0" step="1" /></label>
        <div class="field" style="justify-content: center">
          <button class="btn btn--primary" :disabled="travelSave.busy.value">Save</button>
        </div>
        <p v-if="travelSave.error.value" class="form-error span-all">{{ travelSave.error.value }}</p>
      </form>
    </BaseModal>
  </div>
</template>
