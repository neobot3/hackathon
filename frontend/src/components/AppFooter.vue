<script setup>
import AppLogo from './AppLogo.vue'

const year = new Date().getFullYear()
</script>

<template>
  <footer class="footer">
    <div class="footer__inner">
      <AppLogo />
      <p>CBA-aware scheduling for MRO technical representatives.</p>
      <small>&copy; {{ year }} TechRep Scheduler</small>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  background: #050914;
  color: rgba(255, 255, 255, 0.7);
  padding: 3rem 1.5rem;
}
.footer__inner {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  color: #fff;
}
.footer p {
  margin: 0;
  color: rgba(255, 255, 255, 0.6);
}
small {
  color: rgba(255, 255, 255, 0.4);
}
</style>
