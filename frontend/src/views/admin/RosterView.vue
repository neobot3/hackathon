<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '@/api'
import { useResource } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import PageHeader from '@/components/PageHeader.vue'
import { addDays, fmtDateTime, toDateInput } from '@/utils/format'

const PALETTE = [
  '#f4b993', '#9fd4c9', '#f0d78c', '#b9d8a6', '#d4b5dc', '#f0aaa0', '#c6e09f', '#f7c59f',
  '#a7cdd4', '#d9c4bc', '#f2a9b3', '#acd0c2', '#f5b5d2', '#a9cdf0', '#c4b5e6', '#f5d97e',
]
const LEAVE = {
  vacation: { code: 'VAC', color: '#9fcdf2', label: 'Vacation' },
  training: { code: 'TR', color: '#a8dca8', label: 'Training' },
  sick: { code: 'SICK', color: '#f2aec3', label: 'Sick' },
  other: { code: 'AB', color: '#dcb8b2', label: 'Absent (other leave)' },
}
const DOW = ['S', 'M', 'T', 'W', 'T', 'F', 'S']

const reference = useReferenceStore()

const now = new Date()
const month = ref(toDateInput(now).slice(0, 7))
const mroFilter = ref('')
const search = ref('')
const tip = ref(null)

function showTip(e) {
  const el = e.target.closest('[data-tip]')
  if (!el?.dataset.tip) {
    tip.value = null
    return
  }
  const r = el.getBoundingClientRect()
  const below = r.bottom + 120 < window.innerHeight
  tip.value = { text: el.dataset.tip, x: r.left + r.width / 2, y: below ? r.bottom + 6 : r.top - 6, below }
}

const first = computed(() => {
  const [y, m] = month.value.split('-').map(Number)
  return new Date(y, m - 1, 1)
})
const next = computed(() => new Date(first.value.getFullYear(), first.value.getMonth() + 1, 1))
const days = computed(() => {
  const n = new Date(next.value - 1).getDate()
  return Array.from({ length: n }, (_, i) => new Date(first.value.getFullYear(), first.value.getMonth(), i + 1))
})
const title = computed(() =>
  first.value.toLocaleDateString(undefined, { month: 'short', year: '2-digit' }).toUpperCase().replace(' ', '-'),
)
const todayKey = toDateInput(now)

function shiftMonth(delta) {
  month.value = toDateInput(new Date(first.value.getFullYear(), first.value.getMonth() + delta, 1)).slice(0, 7)
}

const { data, loading, reload } = useResource(
  async () => {
    const window = { start: first.value.toISOString(), end: next.value.toISOString() }
    const [assignments, leave, events, patterns] = await Promise.all([
      api.assignments.list(window),
      api.unavailability.list({ ...window, status: 'approved' }),
      api.maintenanceEvents.list({ start: toDateInput(first.value), end: toDateInput(addDays(next.value, -1)) }),
      api.cba.shiftPatterns(),
    ])
    return {
      assignments: assignments.filter((a) => a.status !== 'cancelled'),
      leave,
      events: events.filter((e) => e.status !== 'cancelled'),
      cycles: Object.fromEntries(patterns.map((p) => [p.code, p.cycle])),
    }
  },
  { initial: { assignments: [], leave: [], events: [], cycles: {} } },
)
watch(month, reload)

// Day columns of this month that [start, end) touches, in browser local time.
function dayIndexes(start, end) {
  const s = new Date(start)
  const e = new Date(end)
  return days.value.flatMap((d, i) => (s < addDays(d, 1) && d < e ? [i] : []))
}

const parseDate = (value) => {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, m - 1, d)
}

const mroColor = computed(() => {
  const sorted = [...reference.mros].sort((a, b) => a.id - b.id)
  return Object.fromEntries(sorted.map((m, i) => [m.id, PALETTE[i % PALETTE.length]]))
})

function homeMro(rep) {
  const home = rep.home_base.trim().toLowerCase()
  return reference.mros.find((m) => [m.location, m.airport_code].some((v) => v?.trim().toLowerCase() === home))
}

// e.g. "KFH · Hamilton, ON (YHM)"
function mroLabel(id) {
  const m = reference.mros.find((x) => x.id === id)
  if (!m) return reference.mroName(id)
  const airport = m.airport_code && m.airport_code !== m.facility_name ? ` (${m.airport_code})` : ''
  return `${m.facility_name} · ${m.location}${airport}`
}

function isPatternDay(rep, day) {
  const cycle = data.value.cycles[rep.shift_pattern_code]
  if (!cycle || !rep.shift_cycle_start) return false
  const start = parseDate(rep.shift_cycle_start)
  const offset = Math.round((Date.UTC(day.getFullYear(), day.getMonth(), day.getDate()) - Date.UTC(start.getFullYear(), start.getMonth(), start.getDate())) / 864e5)
  return cycle[((offset % cycle.length) + cycle.length) % cycle.length] === 'W'
}

const cellsByRep = computed(() => {
  const grid = new Map()
  const cell = (repId, i) => {
    if (!grid.has(repId)) grid.set(repId, days.value.map(() => ({})))
    return grid.get(repId)[i]
  }
  for (const u of data.value.leave) {
    for (const i of dayIndexes(u.start_time, u.end_time)) cell(u.rep_id, i).leave = u
  }
  for (const a of data.value.assignments) {
    for (const i of dayIndexes(a.start_time, a.end_time)) cell(a.rep_id, i).assignment ??= a
  }
  return grid
})

const rows = computed(() => {
  const q = search.value.trim().toLowerCase()
  const mro = reference.mros.find((m) => m.id === mroFilter.value)
  return reference.reps
    .filter((r) => r.active)
    .filter((r) => !q || r.name.toLowerCase().includes(q))
    .filter(
      (r) =>
        !mro ||
        homeMro(r)?.id === mro.id ||
        (cellsByRep.value.get(r.id) || []).some((c) => c.assignment?.mro_id === mro.id),
    )
    .sort((a, b) => (a.seniority_rank ?? Infinity) - (b.seniority_rank ?? Infinity) || a.id - b.id)
    .map((rep) => ({
      rep,
      color: mroColor.value[homeMro(rep)?.id],
      cells: days.value.map((day, i) => describe(rep, day, cellsByRep.value.get(rep.id)?.[i] || {})),
    }))
})

function describe(rep, day, { assignment, leave }) {
  const kind = leave && (LEAVE[leave.reason] || LEAVE.other)
  if (assignment) {
    const ot = assignment.overtime_type !== 'none'
    return {
      code: reference.mroCode(assignment.mro_id),
      color: mroColor.value[assignment.mro_id],
      ot,
      conflict: !!leave,
      title: [
        `${mroLabel(assignment.mro_id)}${assignment.aircraft_type_id == null ? '' : ` · ${reference.aircraftName(assignment.aircraft_type_id)}`}`,
        `${fmtDateTime(assignment.start_time)} – ${fmtDateTime(assignment.end_time)}`,
        `Status: ${assignment.status}${ot ? ` · ${assignment.overtime_type} overtime` : ''}`,
        leave ? `Conflicts with approved ${leave.reason}` : '',
      ].filter(Boolean).join('\n'),
    }
  }
  if (kind) return { code: kind.code, color: kind.color, title: `${kind.label}${leave.notes ? ` · ${leave.notes}` : ''}` }
  return { on: isPatternDay(rep, day), title: isPatternDay(rep, day) ? `${rep.shift_pattern_code} work day, unassigned` : '' }
}

// One row per aircraft type with inductions (IN) and returns to service (RTS) this month.
const eventRows = computed(() => {
  const byType = new Map()
  for (const e of data.value.events) {
    if (!byType.has(e.aircraft_type_id)) byType.set(e.aircraft_type_id, days.value.map(() => ({ events: [] })))
    const cells = byType.get(e.aircraft_type_id)
    const induction = toDateInput(parseDate(e.induction_date))
    const rts = toDateInput(parseDate(e.rts_date))
    days.value.forEach((d, i) => {
      const key = toDateInput(d)
      if (key < induction || key > rts) return
      const c = cells[i]
      c.events.push(e)
      if (key === induction) c.code = 'IN'
      if (key === rts) c.code = c.code ? 'IN/RTS' : 'RTS'
    })
  }
  return [...byType.entries()].map(([typeId, cells]) => ({
    label: `${reference.aircraftName(typeId)} inductions/RTS`,
    cells: cells.map((c) => ({
      ...c,
      title: c.events.map((e) => `${e.tail_number} ${e.event_type} · ${e.induction_date} → ${e.rts_date}`).join('\n'),
    })),
  }))
})

const legend = computed(() => {
  const used = new Set(data.value.assignments.map((a) => a.mro_id))
  return [
    ...[...used].map((id) => ({ code: reference.mroCode(id), color: mroColor.value[id], label: mroLabel(id) })),
    ...Object.values(LEAVE),
  ]
})
</script>

<template>
  <div>
    <PageHeader title="Roster" subtitle="Monthly schedule by rep, in seniority order, with aircraft inductions and returns to service.">
      <div class="month-nav">
        <button class="btn btn--ghost btn--sm" @click="shiftMonth(-1)">&larr; Prev</button>
        <input v-model="month" type="month" class="input" aria-label="Month" />
        <button class="btn btn--ghost btn--sm" @click="shiftMonth(1)">Next &rarr;</button>
      </div>
    </PageHeader>

    <div class="card">
      <div class="filters">
        <label class="field">
          <span>Location</span>
          <select v-model="mroFilter">
            <option value="">All locations</option>
            <option v-for="m in reference.mros" :key="m.id" :value="m.id">{{ m.facility_name }}</option>
          </select>
        </label>
        <label class="field"><span>Rep</span><input v-model="search" type="search" placeholder="Search by name" /></label>
      </div>

      <div v-if="loading" class="loading"><span class="spinner" /> Loading…</div>
      <div v-else class="roster">
        <div class="roster__scroll" @scroll="tip = null">
          <table class="roster__grid" @mouseover="showTip" @mouseleave="tip = null">
            <thead>
              <tr v-for="row in eventRows" :key="row.label" class="roster__event">
                <th colspan="4" class="sticky">{{ row.label }}</th>
                <td v-for="(c, i) in row.cells" :key="i" :class="{ 'is-event': c.events.length }" :data-tip="c.title">{{ c.code }}</td>
              </tr>
              <tr>
                <th class="sticky col-emp" rowspan="2">Emp #</th>
                <th class="sticky col-sen" rowspan="2">Sen.</th>
                <th class="sticky col-contact" rowspan="2">Contact #</th>
                <th class="sticky col-name roster__month" rowspan="2">{{ title }}</th>
                <th v-for="d in days" :key="d.getDate()" :class="{ weekend: d.getDay() % 6 === 0, today: toDateInput(d) === todayKey }">
                  {{ d.getDate() }}
                </th>
              </tr>
              <tr>
                <th v-for="d in days" :key="d.getDate()" :class="{ weekend: d.getDay() % 6 === 0, today: toDateInput(d) === todayKey }">
                  {{ DOW[d.getDay()] }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.rep.id">
                <td class="sticky col-emp">{{ row.rep.id }}</td>
                <td class="sticky col-sen">{{ row.rep.seniority_rank ?? '—' }}</td>
                <td class="sticky col-contact" :data-tip="row.rep.email">{{ row.rep.phone || '—' }}</td>
                <td class="sticky col-name" :style="{ background: row.color }" :data-tip="homeMro(row.rep) ? `Home base: ${mroLabel(homeMro(row.rep).id)}` : row.rep.home_base">{{ row.rep.name }}</td>
                <td
                  v-for="(c, i) in row.cells"
                  :key="i"
                  :class="{ on: c.on, ot: c.ot, conflict: c.conflict, weekend: days[i].getDay() % 6 === 0 && !c.code }"
                  :style="c.color ? { background: c.color } : null"
                  :data-tip="c.title"
                >
                  {{ c.code }}
                </td>
              </tr>
            </tbody>
          </table>
          <div
            v-if="tip"
            class="roster__tip"
            :class="{ 'roster__tip--above': !tip.below }"
            :style="{ left: `${tip.x}px`, top: `${tip.y}px` }"
            role="tooltip"
          >{{ tip.text }}</div>
          <div v-if="!rows.length" class="empty">No active reps match.</div>
        </div>

        <aside class="roster__legend">
          <h3>Legend</h3>
          <div v-for="item in legend" :key="item.code" class="legend__item">
            <span class="legend__swatch" :style="{ background: item.color }">{{ item.code }}</span>
            <span>{{ item.label }}</span>
          </div>
          <div class="legend__item"><span class="legend__swatch on" /> <span>Pattern work day, unassigned</span></div>
          <div class="legend__item"><span class="legend__swatch ot">OT</span> <span>Overtime</span></div>
          <div class="legend__item"><span class="legend__swatch conflict">!</span> <span>Assigned during leave</span></div>
        </aside>
      </div>
    </div>
  </div>
</template>

<style scoped>
.roster {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}
.roster__scroll {
  flex: 1;
  overflow: auto;
  max-height: 75vh;
  border: 1px solid var(--border);
}
/* Separate borders keep cell widths exact, so the sticky column offsets line up. */
.roster__grid {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.7rem;
  white-space: nowrap;
}
.roster__grid th,
.roster__grid td {
  box-sizing: border-box;
  border: solid var(--border);
  border-width: 0 1px 1px 0;
  min-width: 34px;
  height: 22px;
  padding: 0 3px;
  text-align: center;
  font-weight: 600;
}
.roster__grid thead th {
  position: sticky;
  top: 0;
  background: var(--surface-2);
  z-index: 2;
}
.sticky {
  position: sticky;
  background: var(--surface);
  z-index: 1;
  text-align: left !important;
}
thead .sticky {
  z-index: 3;
}
.roster__grid .col-emp {
  left: 0;
  width: 48px;
  min-width: 48px;
  max-width: 48px;
}
.roster__grid .col-sen {
  left: 48px;
  width: 40px;
  min-width: 40px;
  max-width: 40px;
}
.roster__grid .col-contact {
  left: 88px;
  width: 120px;
  min-width: 120px;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.roster__grid .col-name {
  left: 208px;
  width: 160px;
  min-width: 160px;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.month-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.roster__month {
  background: #a8dcb3 !important;
  color: #1f4d2b;
  font-size: 0.95rem;
  text-align: center !important;
}
.weekend {
  background: #fbf1c4;
}
.today {
  outline: 2px solid var(--primary);
  outline-offset: -2px;
}
td.on {
  background: #d6cbeb;
}
td.ot {
  box-shadow: inset 0 0 0 2px #4f9a62;
}
td.conflict {
  box-shadow: inset 0 0 0 2px var(--danger);
}
.roster__event th,
.roster__event td {
  background: #e2e6ec;
}
.roster__event th.sticky {
  left: 0;
}
.roster__event td.is-event {
  background: #aab7c8;
  color: #334155;
}
.roster__tip {
  position: fixed;
  z-index: 50;
  transform: translateX(-50%);
  max-width: 320px;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  background: #1f2937;
  color: #f9fafb;
  font-size: 0.75rem;
  line-height: 1.4;
  white-space: pre-line;
  box-shadow: 0 4px 12px rgb(0 0 0 / 0.18);
  pointer-events: none;
}
.roster__tip--above {
  transform: translate(-50%, -100%);
}
.roster__legend {
  width: 210px;
  font-size: 0.75rem;
}
.roster__legend h3 {
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
}
.legend__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}
.legend__swatch {
  display: inline-block;
  min-width: 46px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  font-weight: 700;
  border: 1px solid var(--border);
}
.legend__swatch.on {
  background: #d6cbeb;
}
.legend__swatch.ot {
  box-shadow: inset 0 0 0 2px #4f9a62;
}
.legend__swatch.conflict {
  box-shadow: inset 0 0 0 2px var(--danger);
}
@media (max-width: 900px) {
  .roster {
    flex-direction: column;
  }
}
</style>
