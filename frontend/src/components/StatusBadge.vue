<script setup>
import { computed } from 'vue'
import { titleCase } from '@/utils/format'

const props = defineProps({ value: { type: [String, Boolean], required: true } })

const TONES = {
  open: 'info',
  requested: 'info',
  proposed: 'info',
  confirmed: 'success',
  approved: 'success',
  filled: 'success',
  completed: 'success',
  accepted: 'success',
  in_progress: 'warning',
  aog: 'danger',
  denied: 'danger',
  declined: 'danger',
  cancelled: 'muted',
  base_coverage: 'muted',
  available: 'success',
  assigned: 'info',
  on_leave: 'warning',
  critical: 'danger',
  warning: 'warning',
  info: 'info',
  true: 'success',
  false: 'muted',
}

const tone = computed(() => TONES[String(props.value)] || 'muted')
const label = computed(() => {
  if (props.value === true) return 'Active'
  if (props.value === false) return 'Inactive'
  return props.value === 'aog' ? 'AOG' : titleCase(props.value)
})
</script>

<template>
  <span class="badge" :class="`badge--${tone}`">{{ label }}</span>
</template>
