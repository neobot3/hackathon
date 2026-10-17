const pad = (n) => String(n).padStart(2, '0')

export function fmtDateTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

// Date-only strings ("2026-10-17") are parsed as local dates to avoid a UTC day shift.
export function fmtDate(value) {
  if (!value) return '—'
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

// <input type="datetime-local"> value -> timezone-aware ISO string for the API.
export function toIso(localValue) {
  return localValue ? new Date(localValue).toISOString() : null
}

export function toLocalInput(date) {
  const d = new Date(date)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function toDateInput(date) {
  const d = new Date(date)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function addDays(date, days) {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

export function startOfDay(date = new Date()) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return d
}

export function hoursBetween(start, end) {
  return (new Date(end) - new Date(start)) / 36e5
}

export function num(value, digits = 1) {
  return Number(value ?? 0).toFixed(digits)
}

export function titleCase(value) {
  return String(value ?? '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// Returns only the keys whose values differ from the original, with "" mapped to null.
export function diff(original, edited) {
  const out = {}
  for (const [key, value] of Object.entries(edited)) {
    const v = value === '' ? null : value
    if (JSON.stringify(v) !== JSON.stringify(original[key] ?? null)) out[key] = v
  }
  return out
}
