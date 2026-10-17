<script setup>
import { computed, reactive, ref } from 'vue'
import { api } from '@/api'
import { useSubmit } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import BaseModal from '@/components/BaseModal.vue'
import PageHeader from '@/components/PageHeader.vue'
import { diff } from '@/utils/format'

const reference = useReferenceStore()
const save = useSubmit()

const rows = computed(() =>
  reference.aircraftTypes.map((t) => ({
    ...t,
    reps: reference.reps.filter((r) => r.active && r.certified_aircraft_type_ids.includes(t.id)).length,
  })),
)

const editing = ref(null)
const showForm = ref(false)
const form = reactive({ model_name: '', manufacturer: '' })

function open(type = null) {
  editing.value = type
  Object.assign(form, { model_name: type?.model_name ?? '', manufacturer: type?.manufacturer ?? '' })
  save.error.value = ''
  showForm.value = true
}

async function submit() {
  const body = { model_name: form.model_name.trim(), manufacturer: form.manufacturer.trim() || null }
  const ok = editing.value
    ? await save.run(() => api.aircraftTypes.update(editing.value.id, diff(editing.value, body)), 'Aircraft type updated')
    : await save.run(() => api.aircraftTypes.create(body), 'Aircraft type added')
  if (ok) {
    showForm.value = false
    reference.load(true)
  }
}
</script>

<template>
  <div>
    <PageHeader title="Aircraft types" subtitle="Fleet types reps can be certified on and demand can request.">
      <button class="btn btn--primary" @click="open()">+ Add aircraft type</button>
    </PageHeader>

    <div class="grid grid-3">
      <article v-for="t in rows" :key="t.id" class="card type">
        <div class="type__icon">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 00-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" /></svg>
        </div>
        <div class="type__body">
          <h3>{{ t.model_name }}</h3>
          <p class="muted">{{ t.manufacturer || 'Unknown manufacturer' }}</p>
          <span class="badge badge--info">{{ t.reps }} certified active rep{{ t.reps === 1 ? '' : 's' }}</span>
        </div>
        <button class="btn btn--ghost btn--sm" @click="open(t)">Edit</button>
      </article>
    </div>
    <div v-if="!rows.length" class="card empty">No aircraft types yet.</div>

    <BaseModal v-if="showForm" :title="editing ? 'Edit aircraft type' : 'Add aircraft type'" @close="showForm = false">
      <form id="type-form" class="stack" @submit.prevent="submit">
        <label class="field"><span>Model name *</span><input v-model="form.model_name" required maxlength="100" placeholder="e.g. B737 MAX 8" /></label>
        <label class="field"><span>Manufacturer</span><input v-model="form.manufacturer" maxlength="100" placeholder="e.g. Boeing" /></label>
        <p v-if="save.error.value" class="form-error">{{ save.error.value }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" @click="showForm = false">Cancel</button>
        <button class="btn btn--primary" form="type-form" :disabled="save.busy.value">Save</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.type {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.25rem;
  transition: transform 0.2s, box-shadow 0.2s;
}
.type:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow);
}
.type__icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  flex-shrink: 0;
  color: #fff;
  background: linear-gradient(135deg, var(--primary), var(--accent));
}
.type__icon svg {
  width: 24px;
  height: 24px;
}
.type__body {
  flex: 1;
}
.type__body h3 {
  margin: 0;
}
.type__body p {
  margin: 0.2rem 0 0.6rem;
  font-size: 0.85rem;
}
</style>
