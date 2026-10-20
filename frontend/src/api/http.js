const TOKEN_KEY = 'studyroom_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

const BASE = '/api'

async function request(path, { method = 'GET', body, params } = {}) {
  let url = BASE + path
  if (params) {
    const search = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        search.append(key, value)
      }
    })
    const query = search.toString()
    if (query) url += '?' + query
  }

  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = 'Bearer ' + token
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.status === 204) return null

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    const detail = data && data.detail ? data.detail : '请求失败'
    if (response.status === 401) {
      setToken('')
    }
    throw new ApiError(response.status, typeof detail === 'string' ? detail : '请求失败')
  }

  return data
}

export const http = {
  get: (path, params) => request(path, { params }),
  post: (path, body, params) => request(path, { method: 'POST', body, params }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  delete: (path) => request(path, { method: 'DELETE' }),
}
