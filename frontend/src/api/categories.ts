import api from "./client";
import type { Category } from "@/types";

export const categoriesApi = {
  tree: () => api.get<Category[]>("/categories").then((r) => r.data),
  flat: () => api.get<Category[]>("/categories/flat").then((r) => r.data),
  seed: () => api.post<{ seeded: number }>("/categories/seed").then((r) => r.data),
  create: (data: Partial<Category>) =>
    api.post<Category>("/categories", data).then((r) => r.data),
  update: (id: number, data: Partial<Category>) =>
    api.put<Category>(`/categories/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/categories/${id}`),
};
