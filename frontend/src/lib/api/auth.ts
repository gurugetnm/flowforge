import { api } from "@/lib/api";
import type { User } from "@/lib/types";

export interface Credentials {
  email: string;
  password: string;
}

export interface RegistrationDetails extends Credentials {
  name: string;
}

export const authApi = {
  me: () => api.get<User>("/api/auth/me"),
  login: (credentials: Credentials) => api.post<User>("/api/auth/login", credentials),
  register: (details: RegistrationDetails) => api.post<User>("/api/auth/register", details),
  logout: () => api.post<void>("/api/auth/logout"),
};
