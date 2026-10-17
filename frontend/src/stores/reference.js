import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'

// Shared lookup data used to show names instead of ids across pages.
export const useReferenceStore = defineStore('reference', () => {
  const reps = ref([])
  const aircraftTypes = ref([])
  const mros = ref([])
  const loaded = ref(false)
  let pending = null

  async function load(force = false) {
    if (loaded.value && !force) return
    pending ??= Promise.all([api.reps.list(), api.aircraftTypes.list(), api.mroLocations.list()])
      .then(([r, a, m]) => {
        reps.value = r
        aircraftTypes.value = a
        mros.value = m
        loaded.value = true
      })
      .finally(() => {
        pending = null
      })
    return pending
  }

  const repName = (id) => reps.value.find((r) => r.id === id)?.name ?? `Rep #${id}`
  const aircraftName = (id) => (id == null ? '—' : aircraftTypes.value.find((a) => a.id === id)?.model_name ?? `#${id}`)
  const mroName = (id) => mros.value.find((m) => m.id === id)?.facility_name ?? `MRO #${id}`
  const mroCode = (id) => {
    const m = mros.value.find((x) => x.id === id)
    return m?.airport_code || m?.facility_name || `#${id}`
  }

  return { reps, aircraftTypes, mros, loaded, load, repName, aircraftName, mroName, mroCode }
})
