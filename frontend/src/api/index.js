import { del, get, patch, post, put } from './client'

const seg = encodeURIComponent

export const api = {
  health: () => get('/health'),

  reps: {
    list: () => get('/reps'),
    get: (id) => get(`/reps/${id}`),
    create: (body) => post('/reps', body),
    update: (id, body) => patch(`/reps/${id}`, body),
    certifications: (id) => get(`/reps/${id}/certifications`),
    upsertCertification: (id, typeId, body) => put(`/reps/${id}/certifications/${typeId}`, body),
    deleteCertification: (id, typeId) => del(`/reps/${id}/certifications/${typeId}`),
  },

  aircraftTypes: {
    list: () => get('/aircraft-types'),
    create: (body) => post('/aircraft-types', body),
    update: (id, body) => patch(`/aircraft-types/${id}`, body),
  },

  mroLocations: {
    list: () => get('/mro-locations'),
    create: (body) => post('/mro-locations', body),
    update: (id, body) => patch(`/mro-locations/${id}`, body),
    travelTimes: (id) => get(`/mro-locations/${id}/travel-times`),
    upsertTravelTime: (id, homeBase, body) => put(`/mro-locations/${id}/travel-times/${seg(homeBase)}`, body),
    deleteTravelTime: (id, homeBase) => del(`/mro-locations/${id}/travel-times/${seg(homeBase)}`),
  },

  cba: {
    rules: () => get('/cba/rules'),
    activeRules: (on) => get('/cba/rules/active', { on }),
    updateRules: (id, body) => patch(`/cba/rules/${id}`, body),
    shiftPatterns: () => get('/cba/shift-patterns'),
    holidays: (params) => get('/cba/holidays', params),
    createHoliday: (body) => post('/cba/holidays', body),
    payPeriods: (params) => get('/cba/pay-periods', params),
    createPayPeriod: (body) => post('/cba/pay-periods', body),
    deletePayPeriod: (id) => del(`/cba/pay-periods/${id}`),
  },

  unavailability: {
    list: (params) => get('/unavailability', params),
    create: (body) => post('/unavailability', body),
    setStatus: (id, status) => patch(`/unavailability/${id}`, { status }),
  },

  demands: {
    list: (params) => get('/demands', params),
    create: (body) => post('/demands', body),
    setStatus: (id, status) => patch(`/demands/${id}`, { status }),
    responses: (id) => get(`/demands/${id}/responses`),
    setResponse: (id, repId, response) => put(`/demands/${id}/responses/${repId}`, { response }),
    deleteResponse: (id, repId) => del(`/demands/${id}/responses/${repId}`),
  },

  assignments: {
    list: (params) => get('/assignments', params),
    create: (body) => post('/assignments', body),
    setStatus: (id, status) => patch(`/assignments/${id}`, { status }),
  },

  schedule: {
    run: (body) => post('/schedule/run', body),
  },
}
