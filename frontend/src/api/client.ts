import axios from "axios"

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || error.message || "Request failed"
    console.error("[API]", message)
    return Promise.reject(error)
  }
)

export default client
