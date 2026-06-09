import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // Trigger browser basic-auth prompt or show login modal
      window.dispatchEvent(new CustomEvent('auth:required'))
    }
    return Promise.reject(err)
  }
)

export default client
