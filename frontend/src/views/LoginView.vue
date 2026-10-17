<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { gsap } from 'gsap'
import { config } from '@/config'
import { demoAccounts } from '@/auth/localProvider'
import { useAuthStore } from '@/stores/auth'
import AppLogo from '@/components/AppLogo.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = reactive({ username: '', password: '' })
const error = ref('')
const busy = ref(false)
const card = ref(null)
const isAzure = config.authMode === 'azure'

// Only follow same-origin, path-only redirects.
function safeRedirect(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : null
}

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await auth.login(isAzure ? {} : form)
    router.replace(safeRedirect(route.query.redirect) || auth.homeRoute)
  } catch (e) {
    error.value = e.message
    gsap.fromTo(card.value, { x: -10 }, { x: 0, duration: 0.5, ease: 'elastic.out(1, 0.3)' })
  } finally {
    busy.value = false
  }
}

function fill(account) {
  form.username = account.username
  form.password = account.password
}

onMounted(() => {
  gsap.from(card.value, { y: 40, opacity: 0, duration: 0.8, ease: 'power3.out' })
  gsap.from('.login__side > *', { x: -30, opacity: 0, duration: 0.8, stagger: 0.12, ease: 'power3.out', delay: 0.1 })
})
</script>

<template>
  <section class="login">
    <div class="login__bg" />
    <div class="login__inner">
      <div class="login__side">
        <span class="kicker">Welcome back</span>
        <h1>Sign in to your scheduling workspace</h1>
        <p>Admins manage reps, aircraft, MRO locations and CBA rules. Schedulers log demand and run the optimizer.</p>
      </div>

      <form ref="card" class="login__card" @submit.prevent="submit">
        <AppLogo compact class="login__logo" />

        <template v-if="isAzure">
          <p class="muted">Use your organisation account.</p>
          <button class="btn btn--primary btn--lg login__btn" :disabled="busy">
            <svg width="18" height="18" viewBox="0 0 23 23" aria-hidden="true">
              <path fill="#f35325" d="M1 1h10v10H1z" />
              <path fill="#81bc06" d="M12 1h10v10H12z" />
              <path fill="#05a6f0" d="M1 12h10v10H1z" />
              <path fill="#ffba08" d="M12 12h10v10H12z" />
            </svg>
            Sign in with Microsoft
          </button>
        </template>

        <template v-else>
          <label class="field">
            <span>Username</span>
            <input v-model="form.username" autocomplete="username" required autofocus />
          </label>
          <label class="field">
            <span>Password</span>
            <input v-model="form.password" type="password" autocomplete="current-password" required />
          </label>
          <button class="btn btn--primary btn--lg login__btn" :disabled="busy">
            <span v-if="busy" class="spinner" />
            Sign in
          </button>

          <div class="login__demo">
            <small>Demo accounts (temporary until Azure SSO)</small>
            <div class="row">
              <button v-for="a in demoAccounts" :key="a.username" type="button" class="chip" @click="fill(a)">
                {{ a.username }} · {{ a.roles.join(', ') }}
              </button>
            </div>
          </div>
        </template>

        <p v-if="error" class="form-error">{{ error }}</p>
      </form>
    </div>
  </section>
</template>

<style scoped>
.login {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: calc(var(--nav-height) + 2rem) 1.5rem 3rem;
  background: linear-gradient(180deg, #070b1a, #0b1224);
  overflow: hidden;
}
.login__bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(600px 400px at 20% 30%, rgba(79, 70, 229, 0.45), transparent 70%),
    radial-gradient(500px 400px at 85% 80%, rgba(34, 211, 238, 0.3), transparent 70%);
}
.login__inner {
  position: relative;
  width: min(1040px, 100%);
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 4rem;
  align-items: center;
}
.login__side {
  color: #fff;
}
.login__side .kicker {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
}
.login__side h1 {
  font-size: clamp(2rem, 4vw, 3rem);
  margin: 0.8rem 0 1rem;
}
.login__side p {
  color: rgba(255, 255, 255, 0.65);
  line-height: 1.7;
  max-width: 460px;
}
.login__card {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  padding: 2.25rem;
  border-radius: 22px;
  background: var(--surface);
  box-shadow: 0 40px 100px rgba(0, 0, 0, 0.45);
}
.login__logo {
  margin-bottom: 0.5rem;
  color: var(--text);
}
.login__btn {
  width: 100%;
}
.login__demo {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 1rem;
  border-top: 1px dashed var(--border);
}
.login__demo small {
  color: var(--muted);
}
@media (max-width: 860px) {
  .login__inner {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
}
</style>
