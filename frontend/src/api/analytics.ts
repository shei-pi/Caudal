import api from "./client";
import type {
  MonthlySummaryResponse,
  NetWorthResponse,
  SpendingByCategoryResponse,
} from "@/types";

export const analyticsApi = {
  spendingByCategory: (dateFrom?: string, dateTo?: string, accountId?: number) =>
    api
      .get<SpendingByCategoryResponse>("/analytics/spending-by-category", {
        params: { date_from: dateFrom, date_to: dateTo, account_id: accountId },
      })
      .then((r) => r.data),
  monthlySummary: (months = 12) =>
    api
      .get<MonthlySummaryResponse>("/analytics/monthly-summary", { params: { months } })
      .then((r) => r.data),
  netWorth: () => api.get<NetWorthResponse>("/analytics/net-worth").then((r) => r.data),
};
