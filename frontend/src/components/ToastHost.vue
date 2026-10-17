<script setup>
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
</script>

<template>
  <div class="toasts" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="t in toast.toasts" :key="t.id" class="toast" :class="`toast--${t.type}`" @click="toast.dismiss(t.id)">
        {{ t.message }}
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed;
  right: 1.25rem;
  bottom: 1.25rem;
  z-index: 200;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  max-width: min(420px, calc(100vw - 2.5rem));
}
.toast {
  padding: 0.85rem 1.1rem;
  border-radius: 12px;
  color: #fff;
  font-size: 0.9rem;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.25);
  cursor: pointer;
  border-left: 4px solid transparent;
  background: #0f172a;
}
.toast--success {
  border-left-color: var(--success);
}
.toast--error {
  border-left-color: var(--danger);
}
.toast--info {
  border-left-color: var(--accent);
}
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
