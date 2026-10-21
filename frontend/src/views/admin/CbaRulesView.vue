<script setup>
import { computed, reactive, ref } from 'vue'
import { api } from '@/api'
import { useResource, useSubmit } from '@/composables/useResource'
import BaseModal from '@/components/BaseModal.vue'
import PageHeader from '@/components/PageHeader.vue'
import { diff, fmtDate } from '@/utils/format'

// type: n = number, i = integer, d = date
const GROUPS = [
  {
    title: 'Rest & days off',
    fields: [
      ['min_rest_hours', 'Min rest between shifts', 'n', 'h'],
      ['min_rest_hours_trade', 'Min rest on shift trade', 'n', 'h'],
      ['max_consecutive_scheduled_days', 'Max consecutive scheduled days', 'i'],
      ['max_consecutive_worked_days', 'Max consecutive worked days', 'i'],
      ['min_hours_off_per_set', 'Min hours off per set', 'n', 'h'],
      ['three_days_off_window_days', '3-days-off window', 'i', 'days'],
      ['consecutive_days_off_required', 'Consecutive days off required', 'i'],
    ],
  },
  {
    title: 'Hours averaging',
    fields: [
      ['avg_weekly_hours', 'Average weekly hours', 'n', 'h'],
      ['averaging_weeks_major_base', 'Averaging weeks (major base)', 'i', 'wks'],
      ['averaging_weeks_other_base', 'Averaging weeks (other base)', 'i', 'wks'],
      ['averaging_anchor_date', 'Averaging anchor date', 'd'],
    ],
  },
  {
    title: 'Field service & AOG',
    fields: [
      ['max_field_duty_hours', 'Max field duty', 'n', 'h'],
      ['post_field_rest_hours', 'Post-field rest', 'n', 'h'],
      ['base_coverage_notice_hours', 'Base coverage notice', 'i', 'h'],
      ['max_vehicle_travel_km', 'Max vehicle travel', 'i', 'km'],
      ['field_service_rate', 'Field service rate', 'n', '×'],
      ['aog_pay_buffer_hours', 'AOG pay buffer', 'n', 'h'],
    ],
  },
  {
    title: 'Overtime & premiums',
    fields: [
      ['ot_rate_voluntary', 'Voluntary OT rate', 'n', '×'],
      ['ot_voluntary_tier_hours', 'Voluntary OT tier', 'n', 'h'],
      ['ot_rate_voluntary_over_tier', 'Voluntary OT over tier', 'n', '×'],
      ['ot_rate_mandatory', 'Mandatory OT rate', 'n', '×'],
      ['max_banked_ot_hours', 'Max banked OT', 'n', 'h'],
      ['stat_holiday_rate', 'Stat holiday rate', 'n', '×'],
    ],
  },
  {
    title: 'Scheduling',
    fields: [
      ['schedule_publish_days', 'Schedule plotted ahead', 'i', 'days'],
      ['max_reps_off_per_week', 'Max reps on vacation per week', 'i'],
    ],
  },
]

const { data: rules, reload } = useResource(() => api.cba.rules())
const { data: active } = useResource(() => api.cba.activeRules().catch(() => null), { initial: null })
const { data: patterns } = useResource(() => api.cba.shiftPatterns())

const sorted = computed(() => [...rules.value].sort((a, b) => b.effective_from.localeCompare(a.effective_from)))

const editing = ref(null)
const form = reactive({})
const save = useSubmit()

function open(rule) {
  editing.value = rule
  for (const key of Object.keys(form)) delete form[key]
  Object.assign(form, {
    name: rule.name,
    effective_from: rule.effective_from,
    effective_to: rule.effective_to ?? '',
    major_bases: rule.major_bases.join(', '),
  })
  for (const g of GROUPS) for (const [key] of g.fields) form[key] = rule[key] ?? ''
  save.error.value = ''
}

async function submit() {
  const body = { ...form, major_bases: form.major_bases.split(',').map((s) => s.trim()).filter(Boolean) }
  for (const g of GROUPS) {
    for (const [key, , type] of g.fields) {
      if (type !== 'd') body[key] = Number(body[key])
    }
  }
  const changes = diff(editing.value, body)
  if (!Object.keys(changes).length) return (editing.value = null)
  if (await save.run(() => api.cba.updateRules(editing.value.id, changes), 'CBA rules updated')) {
    editing.value = null
    reload()
  }
}

const fmtTime = (t) => t.slice(0, 5)
</script>

<template>
  <div>
    <PageHeader title="CBA rules" subtitle="Work/rest, averaging and pay rules the scheduler enforces. Each run uses the set in effect for its window." />

    <div class="stack">
      <article v-for="r in sorted" :key="r.id" class="card">
        <div class="card__head">
          <div>
            <h2>
              {{ r.name }}
              <span v-if="active?.id === r.id" class="badge badge--success" style="margin-left: 0.5rem">In effect</span>
            </h2>
            <span class="muted" style="font-size: 0.85rem">
              {{ fmtDate(r.effective_from) }} → {{ r.effective_to ? fmtDate(r.effective_to) : 'open-ended' }} · Major bases:
              {{ r.major_bases.join(', ') || '—' }}
            </span>
          </div>
          <button class="btn btn--primary btn--sm" @click="open(r)">Edit rules</button>
        </div>
        <div class="card__body groups">
          <section v-for="g in GROUPS" :key="g.title">
            <h4>{{ g.title }}</h4>
            <dl>
              <div v-for="[key, label, type, unit] in g.fields" :key="key">
                <dt>{{ label }}</dt>
                <dd>{{ type === 'd' ? fmtDate(r[key]) : r[key] }} <small v-if="unit">{{ unit }}</small></dd>
              </div>
            </dl>
          </section>
        </div>
      </article>
      <div v-if="!rules.length" class="card empty">No CBA rule sets found.</div>

      <div class="card">
        <div class="card__head"><h2>Shift patterns</h2></div>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr><th>Code</th><th>Description</th><th>Cycle</th><th>Hours</th><th>Paid meals</th><th>Start windows</th><th>CBA ref</th></tr>
            </thead>
            <tbody>
              <tr v-for="p in patterns" :key="p.code">
                <td><span class="badge badge--info mono">{{ p.code }}</span></td>
                <td>{{ p.description }}</td>
                <td class="mono">{{ p.cycle }}</td>
                <td>{{ p.shift_hours }}</td>
                <td>{{ p.paid_meal_breaks }}</td>
                <td>
                  <div v-for="w in p.start_windows" :key="w.shift_name" style="font-size: 0.82rem">
                    {{ w.shift_name }}: {{ fmtTime(w.earliest_start) }}–{{ fmtTime(w.latest_start) }}
                  </div>
                </td>
                <td class="muted">{{ p.cba_reference || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <BaseModal v-if="editing" :title="`Edit ${editing.name}`" wide @close="editing = null">
      <form id="cba-form" class="stack" @submit.prevent="submit">
        <section>
          <h4 class="group-title">General</h4>
          <div class="grid grid-4">
            <label class="field span-2"><span>Name *</span><input v-model="form.name" required maxlength="100" /></label>
            <label class="field"><span>Effective from *</span><input v-model="form.effective_from" type="date" required /></label>
            <label class="field"><span>Effective to</span><input v-model="form.effective_to" type="date" /></label>
            <label class="field span-all">
              <span>Major bases</span>
              <input v-model="form.major_bases" placeholder="Comma-separated, e.g. Calgary, Toronto" />
            </label>
          </div>
        </section>
        <section v-for="g in GROUPS" :key="g.title">
          <h4 class="group-title">{{ g.title }}</h4>
          <div class="grid grid-4">
            <label v-for="[key, label, type, unit] in g.fields" :key="key" class="field">
              <span>{{ label }}<template v-if="unit"> ({{ unit }})</template></span>
              <input v-if="type === 'd'" v-model="form[key]" type="date" />
              <input v-else v-model="form[key]" type="number" min="0" :step="type === 'i' ? 1 : 0.01" required />
            </label>
          </div>
        </section>
        <p v-if="save.error.value" class="form-error">{{ save.error.value }}</p>
      </form>
      <template #footer>
        <button class="btn btn--ghost" @click="editing = null">Cancel</button>
        <button class="btn btn--primary" form="cba-form" :disabled="save.busy.value">Save rules</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.groups {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
}
@media (max-width: 1100px) {
  .groups {
    grid-template-columns: repeat(2, 1fr);
  }
}
h4,
.group-title {
  margin: 0 0 0.75rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--primary);
}
dl {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
dl > div {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.85rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px dashed var(--border);
}
dt {
  color: var(--muted);
}
dd {
  margin: 0;
  font-weight: 700;
  white-space: nowrap;
}
dd small {
  font-weight: 500;
  color: var(--muted);
}
</style>
