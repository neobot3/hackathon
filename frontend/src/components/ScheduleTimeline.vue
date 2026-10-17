<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { gsap } from 'gsap'
import { useReferenceStore } from '@/stores/reference'
import { fmtDateTime } from '@/utils/format'

const props = defineProps({
  // [{ key, rep_id, mro_id, start_time, end_time, tone, title }]
  items: { type: Array, required: true },
  start: { type: [String, Date], required: true },
  end: { type: [String, Date], required: true },
})

const reference = useReferenceStore()
const root = ref(null)

const startMs = computed(() => new Date(props.start).getTime())
const endMs = computed(() => new Date(props.end).getTime())
const span = computed(() => Math.max(1, endMs.value - startMs.value))

const days = computed(() => {
  const out = []
  const d = new Date(startMs.value)
  d.setHours(0, 0, 0, 0)
  while (d.getTime() < endMs.value) {
    if (d.getTime() >= startMs.value) out.push(new Date(d))
    d.setDate(d.getDate() + 1)
  }
  return out
})
const tickEvery = computed(() => Math.ceil(days.value.length / 14))

const rows = computed(() => {
  const byRep = new Map()
  for (const item of props.items) {
    if (!byRep.has(item.rep_id)) byRep.set(item.rep_id, [])
    byRep.get(item.rep_id).push(item)
  }
  return [...byRep.entries()]
    .map(([repId, items]) => ({ repId, name: reference.repName(repId), items }))
    .sort((a, b) => a.name.localeCompare(b.name))
})

function pos(ms) {
  return `${Math.min(100, Math.max(0, ((ms - startMs.value) / span.value) * 100))}%`
}
function barStyle(item) {
  const s = Math.max(new Date(item.start_time).getTime(), startMs.value)
  const e = Math.min(new Date(item.end_time).getTime(), endMs.value)
  return { left: pos(s), width: `max(6px, ${((e - s) / span.value) * 100}%)` }
}

watch(
  () => props.items,
  async () => {
    await nextTick()
    if (!root.value || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    gsap.from(root.value.querySelectorAll('.tl__bar'), {
      scaleX: 0,
      transformOrigin: 'left center',
      duration: 0.6,
      stagger: 0.02,
      ease: 'power3.out',
    })
  },
  { immediate: true },
)
</script>

<template>
  <div ref="root" class="tl">
    <div class="tl__head">
      <div class="tl__label" />
      <div class="tl__scale">
        <span v-for="(d, i) in days" v-show="i % tickEvery === 0" :key="d.getTime()" class="tl__tick" :style="{ left: pos(d.getTime()) }">
          {{ d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }}
        </span>
      </div>
    </div>
    <div v-for="row in rows" :key="row.repId" class="tl__row">
      <div class="tl__label" :title="row.name">{{ row.name }}</div>
      <div class="tl__lane">
        <span v-for="d in days" :key="d.getTime()" class="tl__grid" :style="{ left: pos(d.getTime()) }" />
        <div
          v-for="item in row.items"
          :key="item.key"
          class="tl__bar"
          :class="`tl__bar--${item.tone || 'info'}`"
          :style="barStyle(item)"
          :title="`${item.title || reference.mroName(item.mro_id)}\n${fmtDateTime(item.start_time)} → ${fmtDateTime(item.end_time)}`"
        >
          {{ reference.mroCode(item.mro_id) }}
        </div>
      </div>
    </div>
    <div v-if="!rows.length" class="empty">Nothing to show in this window.</div>
  </div>
</template>

<style scoped>
.tl {
  font-size: 0.8rem;
  overflow-x: auto;
}
.tl__head,
.tl__row {
  display: grid;
  grid-template-columns: 160px minmax(600px, 1fr);
}
.tl__head {
  position: sticky;
  top: 0;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
}
.tl__scale {
  position: relative;
  height: 34px;
}
.tl__tick {
  position: absolute;
  top: 10px;
  transform: translateX(-50%);
  white-space: nowrap;
  color: var(--muted);
  font-weight: 600;
  font-size: 0.72rem;
}
.tl__label {
  padding: 0.6rem 1rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-right: 1px solid var(--border);
}
.tl__row {
  border-bottom: 1px solid var(--border);
}
.tl__row:hover {
  background: #f8faff;
}
.tl__lane {
  position: relative;
  min-height: 40px;
}
.tl__grid {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--border);
  opacity: 0.6;
}
.tl__bar {
  position: absolute;
  top: 8px;
  height: 24px;
  border-radius: 7px;
  padding: 0 0.45rem;
  display: flex;
  align-items: center;
  overflow: hidden;
  white-space: nowrap;
  color: #fff;
  font-weight: 700;
  font-size: 0.7rem;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15);
  cursor: default;
}
.tl__bar--info {
  background: linear-gradient(90deg, #6366f1, #818cf8);
}
.tl__bar--success {
  background: linear-gradient(90deg, #059669, #10b981);
}
.tl__bar--warning {
  background: linear-gradient(90deg, #d97706, #f59e0b);
}
.tl__bar--danger {
  background: linear-gradient(90deg, #dc2626, #f87171);
}
.tl__bar--muted {
  background: #94a3b8;
}
</style>
