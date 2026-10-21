<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import { gsap } from 'gsap'
import { api } from '@/api'
import { useSubmit } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useToastStore } from '@/stores/toast'
import PageHeader from '@/components/PageHeader.vue'
import ScheduleTimeline from '@/components/ScheduleTimeline.vue'
import { addDays, fmtDateTime, num, startOfDay, toIso, toLocalInput } from '@/utils/format'

const reference = useReferenceStore()
const toast = useToastStore()
const run = useSubmit()

const start = addDays(startOfDay(), 1)
const form = reactive({
  start_time: toLocalInput(start),
  end_time: toLocalInput(addDays(start, 7)),
  mro_id: '',
  allow_mandatory: false,
})

const result = ref(null)
const runWindow = ref(null)
const view = ref('timeline')
const results = ref(null)

async function execute(save) {
  const body = {
    start_time: toIso(form.start_time),
    end_time: toIso(form.end_time),
    mro_id: form.mro_id || null,
    allow_mandatory: form.allow_mandatory,
    save,
  }
  const res = await run.run(() => api.schedule.run(body), save ? 'Proposals saved as assignments' : null)
  if (!res) return
  result.value = res
  runWindow.value = { start: body.start_time, end: body.end_time }
  await nextTick()
  gsap.from(results.value.querySelectorAll('.stat'), { y: 20, opacity: 0, duration: 0.5, stagger: 0.07, ease: 'power3.out' })
}

const totals = computed(() => {
  const a = result.value?.assignments ?? []
  return {
    assigned: a.length,
    paid: a.reduce((s, x) => s + x.paid_hours, 0),
    overtime: a.reduce((s, x) => s + x.overtime_hours, 0),
    mandatory: a.filter((x) => x.mandatory).length,
    unfilled: (result.value?.unfilled ?? []).reduce((s, u) => s + u.still_needed, 0),
  }
})

const timelineItems = computed(() =>
  (result.value?.assignments ?? []).map((a, i) => ({
    key: `${a.demand_id}-${a.rep_id}-${i}`,
    rep_id: a.rep_id,
    mro_id: a.mro_id,
    start_time: a.start_time,
    end_time: a.end_time,
    tone: a.mandatory ? 'danger' : a.overtime_hours > 0 ? 'warning' : a.field_service ? 'success' : 'info',
  })),
)

const saved = computed(() => (result.value?.assignments ?? []).filter((a) => a.assignment_id && !a.confirmed))
const confirming = ref(false)

async function confirmAll() {
  confirming.value = true
  const targets = saved.value
  const outcomes = await Promise.allSettled(targets.map((a) => api.assignments.setStatus(a.assignment_id, 'confirmed')))
  confirming.value = false
  outcomes.forEach((o, i) => o.status === 'fulfilled' && (targets[i].confirmed = true))
  const failed = outcomes.filter((o) => o.status === 'rejected')
  if (failed.length) toast.error(`${failed.length} assignment(s) could not be confirmed: ${failed[0].reason.message}`)
  else toast.success(`${outcomes.length} assignment(s) confirmed`)
}
</script>

<template>
  <div>
    <PageHeader title="Run scheduler" subtitle="Preview a CBA-compliant schedule for a window, then save proposals for review." />

    <div class="card run">
      <form class="run__form" @submit.prevent="execute(false)">
        <label class="field"><span>Window start *</span><input v-model="form.start_time" type="datetime-local" required /></label>
        <label class="field"><span>Window end *</span><input v-model="form.end_time" type="datetime-local" required /></label>
        <label class="field">
          <span>MRO location</span>
          <select v-model="form.mro_id">
            <option value="">All locations</option>
            <option v-for="m in reference.mros" :key="m.id" :value="m.id">{{ m.facility_name }}</option>
          </select>
        </label>
        <label class="check run__check">
          <input v-model="form.allow_mandatory" type="checkbox" />
          Allow mandatory assignments
          <small class="muted">(reps who didn't accept)</small>
        </label>
        <div class="run__actions">
          <button class="btn btn--ghost" :disabled="run.busy.value">
            <span v-if="run.busy.value" class="spinner" />
            Preview
          </button>
          <button type="button" class="btn btn--primary" :disabled="run.busy.value" @click="execute(true)">Run &amp; save proposals</button>
        </div>
      </form>
      <p v-if="run.error.value" class="form-error" style="margin: 0 1.25rem 1.25rem">{{ run.error.value }}</p>
      <p class="muted run__hint">Windows are limited to 366 days, so a full year fits in one run. Preview does not change any data.</p>
    </div>

    <div v-if="result" ref="results" class="stack" style="margin-top: 1.5rem">
      <div class="grid grid-4">
        <div class="card stat">
          <div class="stat__label">Solver status</div>
          <div class="stat__value" style="font-size: 1.4rem">{{ result.status }}</div>
          <div class="stat__hint">Rule set #{{ result.cba_rules_id }}</div>
        </div>
        <div class="card stat">
          <div class="stat__label">Assignments</div>
          <div class="stat__value">{{ totals.assigned }}</div>
          <div class="stat__hint">{{ totals.mandatory }} mandatory</div>
        </div>
        <div class="card stat">
          <div class="stat__label">Paid hours</div>
          <div class="stat__value">{{ num(totals.paid, 0) }}</div>
          <div class="stat__hint">{{ num(totals.overtime) }} h overtime</div>
        </div>
        <div class="card stat">
          <div class="stat__label">Unfilled seats</div>
          <div class="stat__value" :style="{ color: totals.unfilled ? 'var(--danger)' : 'var(--success)' }">{{ totals.unfilled }}</div>
          <div class="stat__hint">{{ result.unfilled.length }} demand(s)</div>
        </div>
      </div>

      <div v-if="result.warnings.length" class="card warnings">
        <strong>Warnings</strong>
        <ul>
          <li v-for="w in result.warnings" :key="w">{{ w }}</li>
        </ul>
      </div>

      <div class="card">
        <div class="card__head">
          <h2>Proposed schedule</h2>
          <div class="row">
            <div class="seg">
              <button :class="{ on: view === 'timeline' }" @click="view = 'timeline'">Timeline</button>
              <button :class="{ on: view === 'table' }" @click="view = 'table'">Table</button>
            </div>
            <button v-if="saved.length" class="btn btn--accent btn--sm" :disabled="confirming" @click="confirmAll">
              Confirm all {{ saved.length }}
            </button>
          </div>
        </div>
        <div v-if="!result.assignments.length && !result.unfilled.length" class="empty">
          No open demand in this window, so there is nothing to schedule. Demand comes from maintenance
          events and the Demands page; pick a window that covers them.
        </div>
        <div v-else-if="view === 'timeline'">
          <div class="legend">
            <span><i class="lg lg--info" /> Base coverage</span>
            <span><i class="lg lg--success" /> Field service</span>
            <span><i class="lg lg--warning" /> Overtime</span>
            <span><i class="lg lg--danger" /> Mandatory</span>
          </div>
          <ScheduleTimeline :items="timelineItems" :start="runWindow.start" :end="runWindow.end" />
        </div>
        <div v-else class="table-wrap">
          <table class="table">
            <thead>
              <tr><th>Rep</th><th>MRO</th><th>Demand</th><th>Start</th><th>End</th><th>Travel</th><th>Paid</th><th>OT</th><th>Premium</th><th>Flags</th></tr>
            </thead>
            <tbody>
              <tr v-for="(a, i) in result.assignments" :key="i">
                <td><strong>{{ reference.repName(a.rep_id) }}</strong></td>
                <td>{{ reference.mroName(a.mro_id) }}</td>
                <td class="muted">#{{ a.demand_id }}</td>
                <td>{{ fmtDateTime(a.start_time) }}</td>
                <td>{{ fmtDateTime(a.end_time) }}</td>
                <td>{{ num(a.travel_hours) }} h</td>
                <td>{{ num(a.paid_hours) }} h</td>
                <td>{{ num(a.overtime_hours) }} h</td>
                <td>{{ num(a.premium_hours) }} h</td>
                <td>
                  <div class="chips">
                    <span v-if="a.field_service" class="badge badge--success">Field</span>
                    <span v-if="a.mandatory" class="badge badge--danger">Mandatory</span>
                    <span v-if="a.assignment_id" class="badge badge--info">Saved #{{ a.assignment_id }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!result.assignments.length" class="empty">No assignments proposed.</div>
        </div>
      </div>

      <div v-if="result.unfilled.length" class="card">
        <div class="card__head"><h2>Unfilled demand</h2></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Demand</th><th>Still needed</th><th>Reason</th></tr></thead>
            <tbody>
              <tr v-for="u in result.unfilled" :key="u.demand_id">
                <td><strong>#{{ u.demand_id }}</strong></td>
                <td><span class="badge badge--danger">{{ u.still_needed }}</span></td>
                <td>{{ u.reason }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.run__form {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  padding: 1.25rem;
  align-items: end;
}
.run__check {
  grid-column: span 2;
}
.run__check small {
  font-size: 0.8rem;
}
.run__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
}
.run__hint {
  margin: 0;
  padding: 0 1.25rem 1.25rem;
  font-size: 0.8rem;
}
.warnings {
  padding: 1rem 1.25rem;
  background: #fffbeb;
  border-color: #fde68a;
  color: #92400e;
}
.warnings ul {
  margin: 0.5rem 0 0;
  padding-left: 1.2rem;
}
.seg {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.seg button {
  border: 0;
  background: var(--surface);
  padding: 0.4rem 0.8rem;
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
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  font-size: 0.78rem;
  color: var(--muted);
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.lg {
  width: 12px;
  height: 12px;
  border-radius: 4px;
}
.lg--info {
  background: #6366f1;
}
.lg--success {
  background: #10b981;
}
.lg--warning {
  background: #f59e0b;
}
.lg--danger {
  background: #ef4444;
}
@media (max-width: 900px) {
  .run__form {
    grid-template-columns: 1fr;
  }
  .run__check {
    grid-column: auto;
  }
}
</style>
