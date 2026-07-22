import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const client = axios.create({ baseURL: `${BASE_URL}/api` });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function extractError(err, fallback = "Something went wrong. Please try again.") {
  return err?.response?.data?.error || fallback;
}

export default client;