<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { MotionPathPlugin } from 'gsap/MotionPathPlugin'
import { SplitText } from 'gsap/SplitText'
import { useAuthStore } from '@/stores/auth'

gsap.registerPlugin(ScrollTrigger, MotionPathPlugin, SplitText)

const auth = useAuthStore()
const root = ref(null)
let ctx
let mm

const airports = [
  { code: 'YVR', x: 70, y: 210 },
  { code: 'YYC', x: 210, y: 190 },
  { code: 'YEG', x: 235, y: 105 },
  { code: 'YWG', x: 360, y: 200 },
  { code: 'YYZ', x: 495, y: 280 },
  { code: 'YUL', x: 555, y: 215 },
]

const routes = [
  'M210,190 Q140,130 70,210',
  'M70,210 Q290,30 495,280',
  'M235,105 Q300,140 360,200',
  'M360,200 Q470,150 555,215',
  'M210,190 Q370,340 495,280',
]

const stats = [
  { value: 366, suffix: '-day', label: 'Planning horizon per run' },
  { value: 10, prefix: '<', suffix: 's', label: 'Typical CP-SAT solve time' },
  { value: 20, suffix: '+', label: 'CBA work/rest rules enforced' },
  { value: 24, suffix: '/7', label: 'AOG response coverage' },
]

const features = [
  {
    title: 'Optimization engine',
    text: 'Google OR-Tools CP-SAT turns demand, people and rules into a schedule in seconds instead of spreadsheet hours.',
    icon: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
  },
  {
    title: 'CBA compliance built in',
    text: 'Minimum rest, consecutive-day caps, averaging periods and days-off windows are hard constraints, never afterthoughts.',
    icon: 'M9 12l2 2 4-4M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z',
  },
  {
    title: 'AOG first',
    text: 'Aircraft-on-ground requests are prioritised, with travel time and field-duty limits accounted for automatically.',
    icon: 'M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z',
  },
  {
    title: 'Certification matching',
    text: 'Only reps certified on the aircraft type are considered, with expiry dates tracked per rep.',
    icon: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z',
  },
  {
    title: 'Leave & availability',
    text: 'Vacation, training, sick and union leave block assignments the moment they are approved.',
    icon: 'M3 8h18M7 3v4M17 3v4M4 5h16v16H4zM9 15l2 2 4-4',
  },
  {
    title: 'Overtime awareness',
    text: 'Voluntary vs mandatory OT, banked hours and premium rates are calculated on every proposed assignment.',
    icon: 'M12 6v6l4 2M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
]

const steps = [
  { title: 'Capture demand', text: 'MRO base coverage and AOG requests with aircraft type, window and head count.' },
  { title: 'Check availability', text: 'Leave, rest windows, certifications and rep responses are pulled in automatically.' },
  { title: 'Solve', text: 'CP-SAT proposes the lowest-cost compliant schedule and flags anything it cannot fill.' },
  { title: 'Review & confirm', text: 'Schedulers accept, override or re-run, then confirm assignments to the team.' },
]

const rules = [
  'Minimum rest between shifts',
  'Max consecutive scheduled & worked days',
  'Weekly hour averaging by base',
  'Consecutive days off per set',
  'Field-duty limit & post-field rest',
  'Overtime tiers and banked-hour cap',
  'Statutory holiday premiums',
]

function tilt(e) {
  const card = e.currentTarget
  const r = card.getBoundingClientRect()
  const x = (e.clientX - r.left) / r.width - 0.5
  const y = (e.clientY - r.top) / r.height - 0.5
  gsap.to(card, { rotateY: x * 8, rotateX: -y * 8, duration: 0.4, ease: 'power2.out' })
}
function untilt(e) {
  gsap.to(e.currentTarget, { rotateX: 0, rotateY: 0, duration: 0.6, ease: 'elastic.out(1, 0.5)' })
}

onMounted(() => {
  mm = gsap.matchMedia()
  ctx = gsap.context(() => {
    mm.add('(prefers-reduced-motion: no-preference)', () => {
      // Hero entrance
      const split = SplitText.create('.hero__title', { type: 'words', mask: 'words' })
      gsap
        .timeline({ defaults: { ease: 'power4.out' } })
        .from('.hero__eyebrow', { y: 20, opacity: 0, duration: 0.6 })
        .from(split.words, { yPercent: 110, duration: 0.9, stagger: 0.05 }, '-=0.3')
        .from('.hero__lead', { y: 20, opacity: 0, duration: 0.7 }, '-=0.5')
        .from('.hero__cta > *', { y: 16, opacity: 0, duration: 0.5, stagger: 0.1 }, '-=0.4')
        .from('.hero__map', { scale: 0.92, opacity: 0, duration: 1.1 }, 0.2)
        .from('.route', { strokeDashoffset: 600, duration: 1.6, stagger: 0.15, ease: 'power2.inOut' }, 0.4)
        .from('.airport', { scale: 0, transformOrigin: 'center', duration: 0.5, stagger: 0.08, ease: 'back.out(3)' }, 0.6)
        .from('.float-card', { y: 30, opacity: 0, duration: 0.8, stagger: 0.2 }, 1)

      // Planes flying the routes, staggered along their paths
      const planes = root.value.querySelectorAll('.plane')
      gsap.utils.toArray('.route').forEach((path, i) => {
        gsap.set(planes[i], { opacity: 1 })
        gsap
          .to(planes[i], {
            motionPath: { path, align: path, alignOrigin: [0.5, 0.5], autoRotate: true },
            duration: 6 + i * 1.3,
            repeat: -1,
            ease: 'none',
          })
          .progress(i / routes.length)
      })

      gsap.to('.airport__pulse', {
        scale: 2.6,
        opacity: 0,
        transformOrigin: 'center',
        duration: 1.8,
        stagger: { each: 0.3, repeat: -1 },
        ease: 'power1.out',
      })
      gsap.to('.float-card', { y: '-=10', duration: 2.6, yoyo: true, repeat: -1, ease: 'sine.inOut', stagger: 0.6 })
      gsap.to('.orb', { x: 'random(-60, 60)', y: 'random(-40, 40)', duration: 8, repeat: -1, yoyo: true, ease: 'sine.inOut', stagger: 1 })

      // Parallax on hero as you scroll away
      gsap.to('.hero__map', { yPercent: 18, ease: 'none', scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true } })

      // Stats counters
      gsap.utils.toArray('.stat-num').forEach((el) => {
        const obj = { v: 0 }
        el.textContent = '0'
        gsap.to(obj, {
          v: Number(el.dataset.value),
          duration: 1.6,
          ease: 'power2.out',
          snap: { v: 1 },
          onUpdate: () => (el.textContent = obj.v),
          scrollTrigger: { trigger: el, start: 'top 85%', once: true },
        })
      })

      // Section reveals
      gsap.utils.toArray('.reveal').forEach((el) => {
        gsap.from(el, { y: 40, opacity: 0, duration: 0.9, ease: 'power3.out', scrollTrigger: { trigger: el, start: 'top 85%' } })
      })
      gsap.from('.feature', {
        y: 60,
        opacity: 0,
        duration: 0.8,
        stagger: 0.12,
        ease: 'power3.out',
        scrollTrigger: { trigger: '.features__grid', start: 'top 80%' },
      })

      // Workflow progress line + step activation
      gsap.fromTo(
        '.workflow__bar',
        { scaleX: 0 },
        { scaleX: 1, ease: 'none', scrollTrigger: { trigger: '.workflow__track', start: 'top 75%', end: 'bottom 45%', scrub: 0.6 } },
      )
      gsap.utils.toArray('.step').forEach((step, i) => {
        gsap.from(step, {
          y: 50,
          opacity: 0,
          duration: 0.7,
          ease: 'back.out(1.6)',
          scrollTrigger: { trigger: '.workflow__track', start: `top+=${i * 60} 75%` },
        })
      })

      // Compliance checklist ticks in sequence
      gsap
        .timeline({ scrollTrigger: { trigger: '.checklist', start: 'top 75%' } })
        .from('.checklist li', { x: -30, opacity: 0, duration: 0.5, stagger: 0.12, ease: 'power3.out' })
        .from('.checklist .tick', { scale: 0, duration: 0.4, stagger: 0.12, ease: 'back.out(3)' }, 0.3)

      gsap.from('.role-card', {
        y: 60,
        opacity: 0,
        rotateX: 12,
        duration: 0.9,
        stagger: 0.15,
        ease: 'power3.out',
        scrollTrigger: { trigger: '.roles', start: 'top 75%' },
      })
    })
  }, root.value)
})

onBeforeUnmount(() => {
  mm?.revert()
  ctx?.revert()
})
</script>

<template>
  <div ref="root" class="home">
    <!-- HERO -->
    <section class="hero">
      <div class="hero__bg">
        <span class="orb orb--1" />
        <span class="orb orb--2" />
        <span class="orb orb--3" />
        <div class="hero__grid" />
      </div>

      <div class="hero__inner">
        <div class="hero__copy">
          <span class="hero__eyebrow"><span class="dot" /> CBA-aware scheduling · Powered by CP-SAT</span>
          <h1 class="hero__title">Put the right tech rep on every aircraft, <span class="hl">right on time.</span></h1>
          <p class="hero__lead">
            Replace spreadsheets and phone trees with an optimization engine that respects every work/rest rule,
            certification and leave request &mdash; from routine base coverage to AOG emergencies.
          </p>
          <div class="hero__cta">
            <RouterLink v-if="auth.isAuthenticated" :to="auth.homeRoute" class="btn btn--accent btn--lg">Open workspace &rarr;</RouterLink>
            <RouterLink v-else to="/login" class="btn btn--accent btn--lg">Sign in to start &rarr;</RouterLink>
            <a href="#features" class="btn btn--ghost btn--lg hero__ghost">Explore features</a>
          </div>
        </div>

        <div class="hero__map">
          <svg viewBox="0 0 620 400" class="map" aria-hidden="true">
            <defs>
              <linearGradient id="routeGrad" x1="0" x2="1">
                <stop offset="0" stop-color="#22d3ee" />
                <stop offset="1" stop-color="#818cf8" />
              </linearGradient>
            </defs>
            <path
              v-for="(d, i) in routes"
              :key="i"
              class="route"
              :d="d"
              fill="none"
              stroke="url(#routeGrad)"
              stroke-width="1.6"
              stroke-dasharray="600"
              stroke-dashoffset="0"
              stroke-linecap="round"
            />
            <g v-for="a in airports" :key="a.code" class="airport">
              <circle class="airport__pulse" :cx="a.x" :cy="a.y" r="6" fill="#22d3ee" opacity="0.6" />
              <circle :cx="a.x" :cy="a.y" r="5" fill="#0b1224" stroke="#22d3ee" stroke-width="2" />
              <text :x="a.x" :y="a.y - 14" text-anchor="middle" class="airport__code">{{ a.code }}</text>
            </g>
            <g v-for="(d, i) in routes" :key="`p${i}`" class="plane">
              <path
                d="M12,0 C12,-1 10,-1.5 8,-1.5 L2,-1.5 L-3,-9 L-5.5,-9 L-2,-1.5 L-8,-1.5 L-10,-4.5 L-12,-4.5 L-10.5,0 L-12,4.5 L-10,4.5 L-8,1.5 L-2,1.5 L-5.5,9 L-3,9 L2,1.5 L8,1.5 C10,1.5 12,1 12,0 Z"
                fill="#fff"
              />
            </g>
          </svg>

          <div class="float-card float-card--a">
            <span class="badge badge--danger">AOG</span>
            <div>
              <strong>B737 MAX · YYZ</strong>
              <small>Rep assigned in 2.1s</small>
            </div>
          </div>
          <div class="float-card float-card--b">
            <span class="tick-icon">&#10003;</span>
            <div>
              <strong>Rest rule satisfied</strong>
              <small>10h minimum · 21-2.04</small>
            </div>
          </div>
          <div class="float-card float-card--c">
            <span class="badge badge--info">Proposed</span>
            <div>
              <strong>14 / 15 demands filled</strong>
              <small>1 needs mandatory OT</small>
            </div>
          </div>
        </div>
      </div>

      <a href="#stats" class="hero__scroll" aria-label="Scroll down"><span /></a>
    </section>

    <!-- STATS -->
    <section id="stats" class="stats">
      <div class="container stats__grid">
        <div v-for="s in stats" :key="s.label" class="stats__item">
          <div class="stats__value">
            <span v-if="s.prefix">{{ s.prefix }}</span><span class="stat-num" :data-value="s.value">{{ s.value }}</span><span>{{ s.suffix }}</span>
          </div>
          <p>{{ s.label }}</p>
        </div>
      </div>
    </section>

    <!-- FEATURES -->
    <section id="features" class="section">
      <div class="container">
        <header class="section__head reveal">
          <span class="kicker">Features</span>
          <h2>Everything a tech rep schedule needs, in one place</h2>
          <p>Built around the realities of MRO operations and the collective agreement.</p>
        </header>
        <div class="features__grid">
          <article v-for="f in features" :key="f.title" class="feature" @mousemove="tilt" @mouseleave="untilt">
            <span class="feature__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path :d="f.icon" />
              </svg>
            </span>
            <h3>{{ f.title }}</h3>
            <p>{{ f.text }}</p>
          </article>
        </div>
      </div>
    </section>

    <!-- WORKFLOW -->
    <section id="workflow" class="section section--dark">
      <div class="container">
        <header class="section__head reveal">
          <span class="kicker">How it works</span>
          <h2>From request to confirmed crew in four steps</h2>
        </header>
        <div class="workflow__track">
          <div class="workflow__line"><div class="workflow__bar" /></div>
          <div class="workflow__steps">
            <div v-for="(s, i) in steps" :key="s.title" class="step">
              <span class="step__num">{{ String(i + 1).padStart(2, '0') }}</span>
              <h3>{{ s.title }}</h3>
              <p>{{ s.text }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- COMPLIANCE -->
    <section id="compliance" class="section">
      <div class="container compliance">
        <div class="reveal">
          <span class="kicker">Compliance</span>
          <h2>The collective agreement, encoded</h2>
          <p class="muted">
            Admins maintain the active CBA rule set, shift patterns, holidays and pay periods. Every scheduler run reads
            the rules in effect for that window, so proposals are compliant by construction &mdash; and any warning is
            surfaced before anything is confirmed.
          </p>
        </div>
        <ul class="checklist card">
          <li v-for="r in rules" :key="r">
            <span class="tick">&#10003;</span>
            {{ r }}
          </li>
        </ul>
      </div>
    </section>

    <!-- ROLES -->
    <section class="section section--tint">
      <div class="container">
        <header class="section__head reveal">
          <span class="kicker">Workspaces</span>
          <h2>Two roles, one source of truth</h2>
        </header>
        <div class="roles">
          <article class="role-card">
            <span class="role-card__tag">Admin</span>
            <h3>Configure the operation</h3>
            <ul>
              <li>Onboard tech reps and manage certifications</li>
              <li>Maintain aircraft types, MRO locations and travel times</li>
              <li>Edit CBA rules, holidays and pay periods</li>
            </ul>
            <RouterLink :to="auth.isAdmin ? '/admin' : '/login'" class="btn btn--primary">Admin workspace</RouterLink>
          </article>
          <article class="role-card role-card--alt">
            <span class="role-card__tag">Scheduler</span>
            <h3>Run the schedule</h3>
            <ul>
              <li>Log MRO demand and AOG requests</li>
              <li>Record leave and rep responses</li>
              <li>Run the optimizer, review and confirm assignments</li>
            </ul>
            <RouterLink :to="auth.isScheduler ? '/scheduler' : '/login'" class="btn btn--accent">Scheduler workspace</RouterLink>
          </article>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta">
      <div class="container cta__inner reveal">
        <h2>Ready to retire the spreadsheet?</h2>
        <RouterLink :to="auth.isAuthenticated ? auth.homeRoute : '/login'" class="btn btn--accent btn--lg">Get started</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home {
  overflow-x: hidden;
}
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

/* HERO */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding: calc(var(--nav-height) + 2rem) 1.5rem 4rem;
  color: #fff;
  background: radial-gradient(1200px 600px at 70% 20%, #1e1b4b 0%, transparent 60%), linear-gradient(180deg, #070b1a 0%, #0b1224 100%);
  overflow: hidden;
}
.hero__bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.hero__grid {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse at center, #000 30%, transparent 75%);
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.55;
}
.orb--1 {
  width: 420px;
  height: 420px;
  background: #4f46e5;
  top: -120px;
  right: 10%;
}
.orb--2 {
  width: 340px;
  height: 340px;
  background: #06b6d4;
  bottom: -100px;
  left: 5%;
  opacity: 0.35;
}
.orb--3 {
  width: 220px;
  height: 220px;
  background: #f59e0b;
  top: 40%;
  right: -60px;
  opacity: 0.2;
}
.hero__inner {
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: 3rem;
  align-items: center;
}
.hero__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.8);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 12px var(--accent);
}
.hero__title {
  font-size: clamp(2.4rem, 5vw, 4.1rem);
  font-weight: 700;
  margin: 1.25rem 0 1.25rem;
}
.hl {
  color: var(--accent);
  text-shadow: 0 0 40px rgba(34, 211, 238, 0.35);
}
.hero__lead {
  font-size: 1.1rem;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.7);
  max-width: 560px;
}
.hero__cta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  margin-top: 2rem;
}
.hero__ghost {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.25);
}
.hero__map {
  position: relative;
  aspect-ratio: 620 / 400;
  border-radius: 24px;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.02));
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 40px 100px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
}
.map {
  width: 100%;
  height: 100%;
}
.airport__code {
  fill: rgba(255, 255, 255, 0.75);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  font-family: var(--font-display);
}
.plane {
  opacity: 0;
}
.plane path {
  filter: drop-shadow(0 0 6px rgba(34, 211, 238, 0.8));
}
.float-card {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.7rem 0.95rem;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
  font-size: 0.85rem;
}
.float-card div {
  display: flex;
  flex-direction: column;
}
.float-card small {
  color: rgba(255, 255, 255, 0.55);
  font-size: 0.72rem;
}
.float-card--a {
  top: -18px;
  right: 8%;
}
.float-card--b {
  bottom: 18%;
  left: -28px;
}
.float-card--c {
  bottom: -22px;
  right: 14%;
}
.tick-icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
  font-weight: 700;
}
.hero__scroll {
  position: absolute;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  width: 26px;
  height: 42px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-radius: 14px;
}
.hero__scroll span {
  position: absolute;
  top: 8px;
  left: 50%;
  width: 4px;
  height: 8px;
  margin-left: -2px;
  border-radius: 2px;
  background: #fff;
  animation: scrollHint 1.6s infinite;
}
@keyframes scrollHint {
  to {
    transform: translateY(14px);
    opacity: 0;
  }
}

/* STATS */
.stats {
  background: #0b1224;
  color: #fff;
  padding: 3rem 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.stats__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 2rem;
  text-align: center;
}
.stats__value {
  font-family: var(--font-display);
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 700;
  background: linear-gradient(120deg, #22d3ee, #a5b4fc);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.stats p {
  margin: 0.3rem 0 0;
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.9rem;
}

/* SECTIONS */
.section {
  padding: 6rem 0;
}
.section--dark {
  background: linear-gradient(180deg, #0b1224, #111a33);
  color: #fff;
}
.section--tint {
  background: linear-gradient(180deg, #eef2ff, #f4f6fb);
}
.section__head {
  text-align: center;
  max-width: 720px;
  margin: 0 auto 3.5rem;
}
.section__head h2,
.compliance h2 {
  font-size: clamp(1.8rem, 3.4vw, 2.6rem);
  margin: 0.6rem 0;
}
.section__head p {
  color: var(--muted);
  font-size: 1.05rem;
}
.kicker {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--primary);
}
.section--dark .kicker {
  color: var(--accent);
}

/* FEATURES */
.features__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  perspective: 1000px;
}
.feature {
  padding: 2rem;
  border-radius: 20px;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  transform-style: preserve-3d;
  transition: box-shadow 0.3s;
}
.feature:hover {
  box-shadow: 0 24px 60px rgba(79, 70, 229, 0.16);
}
.feature__icon {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.12), rgba(34, 211, 238, 0.18));
  color: var(--primary);
  margin-bottom: 1.2rem;
  transform: translateZ(30px);
}
.feature__icon svg {
  width: 26px;
  height: 26px;
}
.feature h3 {
  margin: 0 0 0.5rem;
  font-size: 1.2rem;
}
.feature p {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

/* WORKFLOW */
.workflow__track {
  position: relative;
}
.workflow__line {
  position: absolute;
  top: 28px;
  left: 6%;
  right: 6%;
  height: 2px;
  background: rgba(255, 255, 255, 0.1);
}
.workflow__bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #818cf8);
  transform-origin: left;
  box-shadow: 0 0 14px var(--accent);
}
.workflow__steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  position: relative;
}
.step__num {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  font-family: var(--font-display);
  font-weight: 700;
  background: #111a33;
  border: 2px solid var(--accent);
  color: var(--accent);
  box-shadow: 0 0 0 6px #0b1224, 0 0 30px rgba(34, 211, 238, 0.35);
}
.step h3 {
  margin: 1.2rem 0 0.5rem;
}
.step p {
  margin: 0;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.6;
}

/* COMPLIANCE */
.compliance {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4rem;
  align-items: center;
}
.compliance p {
  line-height: 1.7;
  font-size: 1.05rem;
}
.checklist {
  list-style: none;
  margin: 0;
  padding: 1.5rem;
  box-shadow: var(--shadow);
}
.checklist li {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.85rem 0.5rem;
  font-weight: 500;
}
.checklist li + li {
  border-top: 1px dashed var(--border);
}
.tick {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, #10b981, #34d399);
  color: #fff;
  font-size: 0.85rem;
  font-weight: 700;
}

/* ROLES */
.roles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  perspective: 1200px;
}
.role-card {
  padding: 2.25rem;
  border-radius: 24px;
  color: #fff;
  background: linear-gradient(150deg, #312e81, #4f46e5);
  box-shadow: 0 30px 70px rgba(79, 70, 229, 0.3);
}
.role-card--alt {
  background: linear-gradient(150deg, #0e7490, #0b1224);
  box-shadow: 0 30px 70px rgba(14, 116, 144, 0.3);
}
.role-card__tag {
  display: inline-block;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.role-card h3 {
  font-size: 1.6rem;
  margin: 1rem 0;
}
.role-card ul {
  padding-left: 1.1rem;
  margin: 0 0 1.75rem;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.85);
}
.role-card .btn--primary {
  --btn-bg: #fff;
  --btn-fg: var(--primary-600);
}

/* CTA */
.cta {
  padding: 5rem 0;
  background: radial-gradient(800px 300px at 50% 100%, rgba(34, 211, 238, 0.25), transparent), #0b1224;
  color: #fff;
}
.cta__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  text-align: center;
}
.cta h2 {
  font-size: clamp(1.8rem, 3.5vw, 2.8rem);
  margin: 0;
}

@media (max-width: 960px) {
  .hero__inner,
  .compliance,
  .roles {
    grid-template-columns: 1fr;
  }
  .features__grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .workflow__steps,
  .stats__grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .workflow__line {
    display: none;
  }
  .float-card--b {
    left: 8px;
  }
}
@media (max-width: 600px) {
  .features__grid,
  .workflow__steps {
    grid-template-columns: 1fr;
  }
  .float-card {
    display: none;
  }
}
</style>
