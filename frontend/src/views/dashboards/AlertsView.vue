<script setup>
import { computed, reactive } from 'vue'
import { api } from '@/api'
import { useResource, useSubmit } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useToastStore } from '@/stores/toast'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { fmtDateTime, titleCase } from '@/utils/format'

const TYPES = [
  'coverage_gap',
  'no_qualified_rep',
  'shortage',
  'date_conflict',
  'training_due',
  'training_expired',
  'training_conflict',
  'vacation_limit',
  'sick_limit',
  'rest',
  'shift_pattern',
  'qualification',
  'seniority',
  'no_aircraft',
  'schedule_horizon',
  'vacation_unused',
]

const reference = useReferenceStore()
const toast = useToastStore()

const filters = reactive({ mro_id: '', alert_type: '', severity: '', acknowledged: 'false' })
const { data: alerts, loading, reload } = useResource(() => api.alerts.list(filters))
const critical = computed(() => alerts.value.filter((a) => a.severity === 'critical' && !a.acknowledged).length)

const action = useSubmit()
async function acknowledge(alert) {
  if (await action.run(() => api.alerts.acknowledge(alert.id), 'Alert acknowledged')) reload()
}
async function scan() {
  const result = await action.run(() => api.alerts.scan())
  if (result) {
    toast.success(`${result.created} new alert(s), ${result.resolved} resolved`)
    reload()
  }
}
</script>

<template>
  <div>
    <PageHeader title="Alerts" subtitle="Coverage gaps, qualification and training issues, leave limits, and date changes by location.">
      <button class="btn btn--primary" :disabled="action.busy.value" @click="scan">Check next 90 days</button>
    </PageHeader>

    <div class="card">
      <form class="filters" @submit.prevent="reload">
        <label class="field">
          <span>Location</span>
          <select v-model="filters.mro_id">
            <option value="">All locations</option>
            <option v-for="m in reference.mros" :key="m.id" :value="m.id">{{ m.facility_name }}</option>
          </select>
        </label>
        <label class="field">
          <span>Type</span>
          <select v-model="filters.alert_type">
            <option value="">All types</option>
            <option v-for="t in TYPES" :key="t" :value="t">{{ titleCase(t) }}</option>
          </select>
        </label>
        <label class="field">
          <span>Severity</span>
          <select v-model="filters.severity">
            <option value="">All</option>
            <option v-for="s in ['critical', 'warning', 'info']" :key="s" :value="s">{{ titleCase(s) }}</option>
          </select>
        </label>
        <label class="field">
          <span>Show</span>
          <select v-model="filters.acknowledged">
            <option value="false">Open</option>
            <option value="true">Acknowledged</option>
            <option value="">All</option>
          </select>
        </label>
        <button class="btn btn--ghost">Apply</button>
      </form>
      <p v-if="action.error.value" class="form-error">{{ action.error.value }}</p>
      <p class="muted">{{ alerts.length }} alert(s), {{ critical }} critical and open.</p>

      <div v-if="loading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>When</th><th>Severity</th><th>Type</th><th>Location</th><th>Rep</th><th>Message</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="a in alerts" :key="a.id">
              <td>{{ fmtDateTime(a.created_at) }}</td>
              <td><StatusBadge :value="a.severity" /></td>
              <td>{{ titleCase(a.alert_type) }}</td>
              <td>{{ a.mro_id ? reference.mroCode(a.mro_id) : '—' }}</td>
              <td>{{ a.rep_id ? reference.repName(a.rep_id) : '—' }}</td>
              <td>{{ a.message }}</td>
              <td>
                <button v-if="!a.acknowledged" class="btn btn--ghost btn--sm" :disabled="action.busy.value" @click="acknowledge(a)">
                  Acknowledge
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!alerts.length" class="empty">No alerts match.</div>
      </div>
    </div>
  </div>
</template>
