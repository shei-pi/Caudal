import api from "./client";
import type { Account } from "@/types";

export const accountsApi = {
  list: () => api.get<Account[]>("/accounts").then((r) => r.data),
  get: (id: number) => api.get<Account>(`/accounts/${id}`).then((r) => r.data),
  create: (data: Partial<Account>) =>
    api.post<Account>("/accounts", data).then((r) => r.data),
  update: (id: number, data: Partial<Account>) =>
    api.put<Account>(`/accounts/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/accounts/${id}`),
};
