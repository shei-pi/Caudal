import {
  Alert,
  Badge,
  Card,
  Grid,
  Group,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { BarChart, PieChart } from "@mantine/charts";
import { useQuery } from "@tanstack/react-query";
import { IconAlertTriangle } from "@tabler/icons-react";
import { analyticsApi } from "@/api/analytics";
import { transactionsApi } from "@/api/transactions";
import AmountDisplay from "@/components/shared/AmountDisplay";

export default function Dashboard() {
  const { data: spending, isLoading: loadingSpending } = useQuery({
    queryKey: ["spending-by-category"],
    queryFn: () => analyticsApi.spendingByCategory(),
  });

  const { data: monthly, isLoading: loadingMonthly } = useQuery({
    queryKey: ["monthly-summary"],
    queryFn: () => analyticsApi.monthlySummary(6),
  });

  const { data: netWorth, isLoading: loadingNW } = useQuery({
    queryKey: ["net-worth"],
    queryFn: analyticsApi.netWorth,
  });

  const { data: anomalies } = useQuery({
    queryKey: ["anomalies"],
    queryFn: transactionsApi.listAnomalies,
  });

  const pieData = spending?.items.slice(0, 8).map((item) => ({
    name: item.category_name,
    value: item.total_ars,
    color: item.color,
  })) ?? [];

  const barData =
    monthly?.items.map((item) => ({
      month: item.label,
      Ingresos: item.income_ars,
      Gastos: item.expense_ars,
    })) ?? [];

  return (
    <Stack gap="md">
      <Title order={2}>Dashboard</Title>

      {anomalies && anomalies.length > 0 && (
        <Alert
          icon={<IconAlertTriangle size={16} />}
          title={`${anomalies.length} movimiento(s) anómalo(s) detectado(s)`}
          color="orange"
          variant="light"
        >
          Hay transacciones con patrones inusuales. Revisalos en la sección de Movimientos.
        </Alert>
      )}

      <Grid>
        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Card withBorder>
            <Text size="sm" c="dimmed">
              Patrimonio Neto
            </Text>
            {loadingNW ? (
              <Skeleton height={32} mt={4} />
            ) : (
              <AmountDisplay
                amount={netWorth?.net_worth_ars ?? 0}
                currency="ARS"
                size="xl"
                fw={700}
              />
            )}
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Card withBorder>
            <Text size="sm" c="dimmed">
              Gastos del mes
            </Text>
            {loadingSpending ? (
              <Skeleton height={32} mt={4} />
            ) : (
              <AmountDisplay
                amount={spending?.total_ars ?? 0}
                currency="ARS"
                txType="debit"
                size="xl"
                fw={700}
              />
            )}
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Card withBorder>
            <Text size="sm" c="dimmed">
              Activos totales
            </Text>
            {loadingNW ? (
              <Skeleton height={32} mt={4} />
            ) : (
              <AmountDisplay
                amount={netWorth?.total_assets_ars ?? 0}
                currency="ARS"
                size="xl"
                fw={700}
              />
            )}
          </Card>
        </Grid.Col>
      </Grid>

      <Grid>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card withBorder h={340}>
            <Text fw={600} mb="sm">
              Gastos por categoría (mes actual)
            </Text>
            {loadingSpending ? (
              <Skeleton height={260} />
            ) : pieData.length === 0 ? (
              <Text c="dimmed" ta="center" mt="xl">
                Sin datos
              </Text>
            ) : (
              <PieChart
                data={pieData}
                size={240}
                withTooltip
                tooltipDataSource="segment"
                mx="auto"
              />
            )}
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card withBorder h={340}>
            <Text fw={600} mb="sm">
              Ingresos vs Gastos (últimos 6 meses)
            </Text>
            {loadingMonthly ? (
              <Skeleton height={260} />
            ) : (
              <BarChart
                h={260}
                data={barData}
                dataKey="month"
                series={[
                  { name: "Ingresos", color: "teal.6" },
                  { name: "Gastos", color: "red.5" },
                ]}
                tickLine="y"
              />
            )}
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
