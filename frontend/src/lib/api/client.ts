import axios from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

// Request interceptor: attach officer token from localStorage
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("officer_token");
      if (token && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: normalize errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        const officerToken = localStorage.getItem("officer_token");
        const requestToken = error.config?.headers?.Authorization?.toString();
        if (officerToken && requestToken === `Bearer ${officerToken}`) {
          localStorage.removeItem("officer_token");
          window.location.href = "/officer/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
