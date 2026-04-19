import api from "./client";
import type { Transaction, TransactionPage } from "@/types";

export interface TransactionFilters {
  account_id?: number;
  category_id?: number;
  date_from?: string;
  date_to?: string;
  tx_type?: string;
  is_recurring?: boolean;
  is_anomaly?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export const transactionsApi = {
  list: (params: TransactionFilters = {}) =>
    api.get<TransactionPage>("/transactions", { params }).then((r) => r.data),
  get: (id: number) =>
    api.get<Transaction>(`/transactions/${id}`).then((r) => r.data),
  create: (data: Partial<Transaction>) =>
    api.post<Transaction>("/transactions", data).then((r) => r.data),
  update: (id: number, data: Partial<Transaction>) =>
    api.put<Transaction>(`/transactions/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/transactions/${id}`),
  categorize: (
    id: number,
    categoryId: number,
    createRule = false,
    rulePattern?: string
  ) =>
    api
      .post<Transaction>(`/transactions/${id}/categorize`, {
        category_id: categoryId,
        create_rule: createRule,
        rule_pattern: rulePattern,
      })
      .then((r) => r.data),
  runCategorization: () =>
    api.post<{ updated: number; total_checked: number }>("/transactions/run-categorization").then((r) => r.data),
  runRecurrence: () =>
    api.post<{ flagged: number }>("/transactions/run-recurrence").then((r) => r.data),
  runAnomaly: () =>
    api.post<{ flagged: number }>("/transactions/run-anomaly").then((r) => r.data),
  listAnomalies: () =>
    api.get<Transaction[]>("/transactions/anomalies").then((r) => r.data),
  listRecurring: () =>
    api.get<Transaction[]>("/transactions/recurring").then((r) => r.data),
};
