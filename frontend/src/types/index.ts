export interface Account {
  id: number;
  name: string;
  institution: string;
  currency: string;
  account_type: string;
  current_balance: number;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: number;
  name: string;
  parent_id: number | null;
  color: string;
  icon: string | null;
  is_income: boolean;
  is_system: boolean;
  created_at: string;
  children?: Category[];
}

export interface CategorizationRule {
  id: number;
  category_id: number;
  pattern: string;
  match_field: string;
  match_type: string;
  priority: number;
  is_active: boolean;
  created_at: string;
}

export interface Transaction {
  id: number;
  account_id: number;
  transaction_date: string;
  description: string;
  description_normalized: string;
  amount: number;
  tx_type: "debit" | "credit" | "transfer";
  currency: string;
  amount_ars: number | null;
  amount_usd: number | null;
  exchange_rate_used: number | null;
  category_id: number | null;
  category: Category | null;
  transfer_id: string | null;
  is_recurring: boolean;
  recurring_group_id: string | null;
  is_anomaly: boolean;
  anomaly_score: number | null;
  source: string;
  import_job_id: number | null;
  hash_fingerprint: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionPage {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ExchangeRate {
  id: number;
  date: string;
  rate_type: string;
  currency_from: string;
  currency_to: string;
  buy_rate: number | null;
  sell_rate: number | null;
  mid_rate: number;
  source: string;
  fetched_at: string;
}

export interface ExchangeRateLatest {
  oficial: ExchangeRate | null;
  blue: ExchangeRate | null;
  mep: ExchangeRate | null;
  ccl: ExchangeRate | null;
  cripto: ExchangeRate | null;
  mayorista: ExchangeRate | null;
  tarjeta: ExchangeRate | null;
}

export interface Instrument {
  id: number;
  ticker: string;
  name: string;
  instrument_type: string;
  currency: string;
  exchange: string | null;
  isin: string | null;
  notes: string | null;
  last_price: number | null;
  last_price_ars: number | null;
  last_price_usd: number | null;
  last_updated: string | null;
}

export interface Holding {
  id: number;
  instrument_id: number;
  account_id: number;
  quantity: number;
  average_buy_price: number;
  average_buy_price_ars: number | null;
  average_buy_price_usd: number | null;
  current_value_ars: number | null;
  current_value_usd: number | null;
  notes: string | null;
  updated_at: string;
  instrument: Instrument | null;
}

export interface ImportJob {
  id: number;
  filename: string;
  file_type: string;
  bank: string | null;
  status: string;
  total_rows: number | null;
  imported_rows: number | null;
  duplicate_rows: number | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface CategorySpend {
  category_id: number | null;
  category_name: string;
  color: string;
  total_ars: number;
  total_usd: number | null;
  transaction_count: number;
  percentage: number;
}

export interface SpendingByCategoryResponse {
  items: CategorySpend[];
  total_ars: number;
  date_from: string;
  date_to: string;
}

export interface MonthlySummaryItem {
  year: number;
  month: number;
  label: string;
  income_ars: number;
  expense_ars: number;
  net_ars: number;
}

export interface MonthlySummaryResponse {
  items: MonthlySummaryItem[];
}

export interface NetWorthResponse {
  total_assets_ars: number;
  total_liabilities_ars: number;
  net_worth_ars: number;
  total_assets_usd: number | null;
  total_liabilities_usd: number | null;
  net_worth_usd: number | null;
  accounts: {
    id: number;
    name: string;
    currency: string;
    balance: number;
    account_type: string;
    is_liability: boolean;
  }[];
  holdings_total_ars: number;
  holdings_total_usd: number | null;
}
