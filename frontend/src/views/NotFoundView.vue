<template>
  <section class="nf">
    <h1>404</h1>
    <p>This page took a different flight.</p>
    <RouterLink to="/" class="btn btn--accent">Back to home</RouterLink>
  </section>
</template>

<style scoped>
.nf {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: #fff;
  background: linear-gradient(180deg, #070b1a, #0b1224);
}
h1 {
  font-size: 7rem;
  margin: 0;
  background: linear-gradient(120deg, #22d3ee, #818cf8);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
p {
  color: rgba(255, 255, 255, 0.6);
}
</style>
