import api from "./client";
import type { CategorizationRule } from "@/types";

export const rulesApi = {
  list: () => api.get<CategorizationRule[]>("/rules").then((r) => r.data),
  create: (data: Partial<CategorizationRule>) =>
    api.post<CategorizationRule>("/rules", data).then((r) => r.data),
  update: (id: number, data: Partial<CategorizationRule>) =>
    api.put<CategorizationRule>(`/rules/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/rules/${id}`),
  test: (pattern: string, matchType: string) =>
    api
      .post<{ matched_count: number; samples: Record<string, unknown>[] }>("/rules/test", {
        pattern,
        match_type: matchType,
      })
      .then((r) => r.data),
};
