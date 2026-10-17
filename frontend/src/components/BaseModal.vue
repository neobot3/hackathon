<script setup>
import { onBeforeUnmount, onMounted } from 'vue'

defineProps({
  title: { type: String, required: true },
  wide: Boolean,
})
const emit = defineEmits(['close'])

function onKey(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div class="modal" @mousedown.self="emit('close')">
      <div class="modal__panel" :class="{ 'modal__panel--wide': wide }" role="dialog" aria-modal="true" :aria-label="title">
        <header class="modal__head">
          <h2>{{ title }}</h2>
          <button class="modal__close" aria-label="Close" @click="emit('close')">&times;</button>
        </header>
        <div class="modal__body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="modal__foot">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: rgba(8, 13, 31, 0.55);
  backdrop-filter: blur(4px);
  animation: fade 0.2s ease;
}
.modal__panel {
  width: min(560px, 100%);
  max-height: calc(100vh - 3rem);
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border-radius: 18px;
  box-shadow: 0 30px 80px rgba(8, 13, 31, 0.35);
  animation: pop 0.25s cubic-bezier(0.2, 0.9, 0.3, 1.2);
}
.modal__panel--wide {
  width: min(920px, 100%);
}
.modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.2rem 1.5rem;
  border-bottom: 1px solid var(--border);
}
.modal__head h2 {
  margin: 0;
  font-size: 1.15rem;
}
.modal__close {
  border: 0;
  background: none;
  font-size: 1.6rem;
  line-height: 1;
  cursor: pointer;
  color: var(--muted);
}
.modal__body {
  padding: 1.5rem;
  overflow-y: auto;
}
.modal__foot {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
}
@keyframes fade {
  from {
    opacity: 0;
  }
}
@keyframes pop {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.97);
  }
}
</style>
