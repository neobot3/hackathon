<script setup>
import { computed } from 'vue'
import { api } from '@/api'
import { useResource } from '@/composables/useResource'
import { useReferenceStore } from '@/stores/reference'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { fmtDate } from '@/utils/format'

const auth = useAuthStore()
const reference = useReferenceStore()
const { data: active } = useResource(() => api.cba.activeRules().catch(() => null), { initial: null })
const { data: patterns } = useResource(() => api.cba.shiftPatterns())

const activeReps = computed(() => reference.reps.filter((r) => r.active).length)
const uncertified = computed(() => reference.reps.filter((r) => r.active && !r.certified_aircraft_type_ids.length))
const recentReps = computed(() => [...reference.reps].sort((a, b) => b.id - a.id).slice(0, 6))
const coverage = computed(() =>
  reference.aircraftTypes.map((t) => ({
    ...t,
    count: reference.reps.filter((r) => r.active && r.certified_aircraft_type_ids.includes(t.id)).length,
  })),
)
const maxCoverage = computed(() => Math.max(1, ...coverage.value.map((c) => c.count)))
</script>

<template>
  <div>
    <PageHeader :title="`Welcome, ${auth.user.name.split(' ')[0]}`" subtitle="Reference data and rules that drive every schedule.">
      <RouterLink to="/admin/reps" class="btn btn--primary">+ Add tech rep</RouterLink>
    </PageHeader>

    <div class="grid grid-4">
      <div class="card stat">
        <div class="stat__label">Active reps</div>
        <div class="stat__value">{{ activeReps }}</div>
        <div class="stat__hint">{{ reference.reps.length }} total</div>
      </div>
      <div class="card stat">
        <div class="stat__label">Aircraft types</div>
        <div class="stat__value">{{ reference.aircraftTypes.length }}</div>
        <div class="stat__hint">Certification targets</div>
      </div>
      <div class="card stat">
        <div class="stat__label">MRO locations</div>
        <div class="stat__value">{{ reference.mros.length }}</div>
        <div class="stat__hint">Facilities served</div>
      </div>
      <div class="card stat">
        <div class="stat__label">Shift patterns</div>
        <div class="stat__value">{{ patterns.length }}</div>
        <div class="stat__hint">Defined in the CBA</div>
      </div>
    </div>

    <div class="grid grid-2" style="margin-top: 1.25rem">
      <div class="card">
        <div class="card__head">
          <h2>Active CBA rule set</h2>
          <RouterLink to="/admin/cba-rules" class="btn btn--ghost btn--sm">Edit rules</RouterLink>
        </div>
        <div v-if="active" class="card__body rules">
          <div class="rules__name">
            <strong>{{ active.name }}</strong>
            <span class="muted">{{ fmtDate(active.effective_from) }} → {{ active.effective_to ? fmtDate(active.effective_to) : 'open-ended' }}</span>
          </div>
          <dl>
            <div><dt>Min rest</dt><dd>{{ active.min_rest_hours }} h</dd></div>
            <div><dt>Max consecutive days</dt><dd>{{ active.max_consecutive_worked_days }}</dd></div>
            <div><dt>Avg weekly hours</dt><dd>{{ active.avg_weekly_hours }}</dd></div>
            <div><dt>Max field duty</dt><dd>{{ active.max_field_duty_hours }} h</dd></div>
            <div><dt>Voluntary OT</dt><dd>×{{ active.ot_rate_voluntary }}</dd></div>
            <div><dt>Max banked OT</dt><dd>{{ active.max_banked_ot_hours }} h</dd></div>
          </dl>
        </div>
        <div v-else class="empty">No rule set is in effect today.</div>
      </div>

      <div class="card">
        <div class="card__head"><h2>Certification coverage</h2></div>
        <div class="card__body">
          <div v-if="!coverage.length" class="empty">No aircraft types yet.</div>
          <div v-for="c in coverage" :key="c.id" class="bar">
            <span class="bar__label">{{ c.model_name }}</span>
            <span class="bar__track"><span class="bar__fill" :style="{ width: `${(c.count / maxCoverage) * 100}%` }" /></span>
            <span class="bar__count">{{ c.count }}</span>
          </div>
          <p v-if="uncertified.length" class="muted" style="margin: 1rem 0 0; font-size: 0.85rem">
            {{ uncertified.length }} active rep(s) have no certifications.
          </p>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top: 1.25rem">
      <div class="card__head">
        <h2>Recently added reps</h2>
        <RouterLink to="/admin/reps" class="btn btn--ghost btn--sm">View all</RouterLink>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Name</th><th>Home base</th><th>Classification</th><th>Certifications</th><th>Status</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in recentReps" :key="r.id">
              <td><strong>{{ r.name }}</strong></td>
              <td>{{ r.home_base }}</td>
              <td>{{ r.classification || '—' }}</td>
              <td>{{ r.certified_aircraft_type_ids.map(reference.aircraftName).join(', ') || '—' }}</td>
              <td><StatusBadge :value="r.active" /></td>
            </tr>
          </tbody>
        </table>
        <div v-if="!recentReps.length" class="empty">No reps yet.</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rules__name {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  margin-bottom: 1rem;
}
.rules__name strong {
  font-size: 1.1rem;
}
dl {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.9rem;
  margin: 0;
}
dt {
  font-size: 0.75rem;
  color: var(--muted);
}
dd {
  margin: 0.15rem 0 0;
  font-weight: 700;
  font-family: var(--font-display);
  font-size: 1.15rem;
}
.bar {
  display: grid;
  grid-template-columns: 130px 1fr 32px;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0;
  font-size: 0.85rem;
}
.bar__track {
  height: 10px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  overflow: hidden;
}
.bar__fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--primary), var(--accent));
  transition: width 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.bar__count {
  text-align: right;
  font-weight: 700;
}
</style>
