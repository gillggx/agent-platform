const STORAGE_KEY = 'agent_platform_client_id'

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

export function getClientId(): string {
  let id = localStorage.getItem(STORAGE_KEY)
  if (!id) {
    id = generateUUID()
    localStorage.setItem(STORAGE_KEY, id)
  }
  return id
}

export function resetClientId(): string {
  const id = generateUUID()
  localStorage.setItem(STORAGE_KEY, id)
  return id
}
