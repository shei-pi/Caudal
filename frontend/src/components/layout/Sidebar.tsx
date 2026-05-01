import { NavLink, Stack } from "@mantine/core";
import {
  IconBuildingBank,
  IconChartBar,
  IconHome,
  IconLayoutDashboard,
  IconList,
  IconTag,
  IconWallet,
} from "@tabler/icons-react";
import { useNavigate, useLocation } from "react-router-dom";

interface Props {
  onNavigate?: () => void;
}

const NAV_ITEMS = [
  { path: "/", label: "Dashboard", icon: IconLayoutDashboard },
  { path: "/accounts", label: "Cuentas", icon: IconBuildingBank },
  { path: "/transactions", label: "Movimientos", icon: IconList },
  { path: "/categories", label: "Categorías", icon: IconTag },
  { path: "/analytics", label: "Análisis", icon: IconChartBar },
  { path: "/net-worth", label: "Patrimonio", icon: IconWallet },
];

export default function Sidebar({ onNavigate }: Props) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Stack gap={4}>
      {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
        <NavLink
          key={path}
          label={label}
          leftSection={<Icon size={18} />}
          active={location.pathname === path}
          onClick={() => {
            navigate(path);
            onNavigate?.();
          }}
          styles={{ root: { borderRadius: 8 } }}
        />
      ))}
    </Stack>
  );
}
