import { Route, Routes } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import Dashboard from "@/pages/Dashboard";
import Transactions from "@/pages/Transactions";
import Categories from "@/pages/Categories";
import Analytics from "@/pages/Analytics";
import NetWorth from "@/pages/NetWorth";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/categories" element={<Categories />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/net-worth" element={<NetWorth />} />
      </Routes>
    </AppShell>
  );
}
