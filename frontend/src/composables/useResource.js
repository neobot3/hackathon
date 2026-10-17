import { ref } from 'vue'
import { useToastStore } from '@/stores/toast'

export function useResource(loader, { initial = [], immediate = true } = {}) {
  const toast = useToastStore()
  const data = ref(initial)
  const loading = ref(false)

  async function reload() {
    loading.value = true
    try {
      data.value = await loader()
    } catch (e) {
      toast.error(e.message)
    } finally {
      loading.value = false
    }
  }

  if (immediate) reload()
  return { data, loading, reload }
}

// Wraps a mutating API call with busy/error state and a success toast.
export function useSubmit() {
  const toast = useToastStore()
  const busy = ref(false)
  const error = ref('')

  async function run(fn, successMessage) {
    busy.value = true
    error.value = ''
    try {
      const result = await fn()
      if (successMessage) toast.success(successMessage)
      return result ?? true
    } catch (e) {
      error.value = e.message
      return false
    } finally {
      busy.value = false
    }
  }

  return { busy, error, run }
}
