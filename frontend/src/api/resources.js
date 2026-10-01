import client from "./client";

export const authApi = {
  login: (username, password) =>
    client.post("/auth/login/", { username, password }).then((r) => r.data),
  register: (payload) => client.post("/auth/register/", payload).then((r) => r.data),
  me: () => client.get("/auth/me/").then((r) => r.data),
  institutions: () => client.get("/auth/institutions/").then((r) => r.data),
};

export const postingsApi = {
  list: (params) => client.get("/postings/", { params }).then((r) => r.data),
  get: (id) => client.get(`/postings/${id}/`).then((r) => r.data),
  create: (payload) => client.post("/postings/", payload).then((r) => r.data),
  mine: (institutionId) =>
    client
      .get("/postings/", { params: { institution: institutionId } })
      .then((r) => r.data),
};

export const applicationsApi = {
  list: (params) => client.get("/applications/", { params }).then((r) => r.data),
  get: (id) => client.get(`/applications/${id}/`).then((r) => r.data),
  apply: (postingId, coverNote) =>
    client
      .post("/applications/", { posting: postingId, cover_note: coverNote })
      .then((r) => r.data),
  transition: (id, action, note = "") =>
    client.post(`/applications/${id}/transition/`, { action, note }).then((r) => r.data),
};

export const notificationsApi = {
  list: () => client.get("/notifications/").then((r) => r.data),
  markRead: (id) => client.post(`/notifications/${id}/mark_read/`).then((r) => r.data),
  markAllRead: () => client.post("/notifications/mark-all-read/").then((r) => r.data),
};

export const anumatiApi = {
  status: () => client.get("/anumati/status/").then((r) => r.data),
  oauthStart: () => client.get("/anumati/oauth/start/").then((r) => r.data),
  linkStudent: (anumati_username, locker_name, anumati_password) =>
    client
      .post("/anumati/link-student-locker/", {
        anumati_username,
        locker_name,
        ...(anumati_password ? { anumati_password } : {}),
      })
      .then((r) => r.data),
  unlinkStudent: () => client.post("/anumati/unlink-student-locker/").then((r) => r.data),
  linkInstitution: (anumati_username, anumati_password, locker_name) =>
    client
      .post("/anumati/link-institution-locker/", {
        anumati_username,
        anumati_password,
        locker_name,
      })
      .then((r) => r.data),
};

export const agentsApi = {
  catalog: () => client.get("/agents/").then((r) => r.data),
  parseProfile: (text) =>
    client.post("/agents/profile-parser/", { text }).then((r) => r.data),
  matchOpportunities: (profile, limit = 8) =>
    client.post("/agents/opportunity-matcher/", { profile, limit }).then((r) => r.data),
  writeSop: (profile, postingId, constraints = "") =>
    client
      .post("/agents/sop-writer/", { profile, posting_id: postingId, constraints })
      .then((r) => r.data),
  learningMap: (profile, postingId) =>
    client.post("/agents/learning-map/", { profile, posting_id: postingId }).then((r) => r.data),
  verify: (profile, result, purpose = "research-development") =>
    client.post("/agents/verify/", { profile, result, purpose }).then((r) => r.data),
  coordinationPlan: (payload) =>
    client.post("/agents/coordination-plan/", payload).then((r) => r.data),
  orchestrate: (payload) =>
    client.post("/agents/orchestrate/", payload).then((r) => r.data),
};
