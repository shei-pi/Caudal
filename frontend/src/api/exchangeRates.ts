import api from "./client";
import type { ExchangeRate, ExchangeRateLatest } from "@/types";

export const exchangeRatesApi = {
  latest: () => api.get<ExchangeRateLatest>("/exchange-rates/latest").then((r) => r.data),
  history: (rateType = "blue", dateFrom?: string, dateTo?: string) =>
    api
      .get<ExchangeRate[]>("/exchange-rates/history", {
        params: { rate_type: rateType, date_from: dateFrom, date_to: dateTo },
      })
      .then((r) => r.data),
  refresh: () => api.post<{ stored: number }>("/exchange-rates/refresh").then((r) => r.data),
};
