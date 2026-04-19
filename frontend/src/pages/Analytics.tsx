import {
  Card,
  Grid,
  Group,
  SegmentedControl,
  Select,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { BarChart, PieChart } from "@mantine/charts";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import dayjs from "dayjs";
import { analyticsApi } from "@/api/analytics";

export default function Analytics() {
  const [months, setMonths] = useState("12");

  const { data: spending, isLoading: loadingSpending } = useQuery({
    queryKey: ["spending-by-category", "analytics"],
    queryFn: () => analyticsApi.spendingByCategory(),
  });

  const { data: monthly, isLoading: loadingMonthly } = useQuery({
    queryKey: ["monthly-summary", months],
    queryFn: () => analyticsApi.monthlySummary(Number(months)),
  });

  const pieData =
    spending?.items.slice(0, 10).map((item) => ({
      name: item.category_name,
      value: item.total_ars,
      color: item.color,
    })) ?? [];

  const barData =
    monthly?.items.map((item) => ({
      month: item.label,
      Ingresos: item.income_ars,
      Gastos: item.expense_ars,
      Balance: item.net_ars,
    })) ?? [];

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>Análisis</Title>
        <Select
          data={["3", "6", "12", "24"]}
          value={months}
          onChange={(v) => setMonths(v ?? "12")}
          label="Meses"
          w={90}
          size="sm"
        />
      </Group>

      <Grid>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card withBorder>
            <Text fw={600} mb="sm">
              Gastos por categoría
            </Text>
            {loadingSpending ? (
              <Skeleton height={280} />
            ) : pieData.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">
                Sin datos
              </Text>
            ) : (
              <>
                <PieChart
                  data={pieData}
                  size={260}
                  withTooltip
                  tooltipDataSource="segment"
                  mx="auto"
                />
                <Stack gap={4} mt="md">
                  {spending?.items.slice(0, 10).map((item) => (
                    <Group key={item.category_id ?? "null"} justify="space-between">
                      <Group gap={6}>
                        <div
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: 2,
                            backgroundColor: item.color,
                          }}
                        />
                        <Text size="xs">{item.category_name}</Text>
                      </Group>
                      <Group gap={8}>
                        <Text size="xs" c="dimmed">
                          {item.percentage}%
                        </Text>
                        <Text size="xs" fw={500}>
                          ${item.total_ars.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                        </Text>
                      </Group>
                    </Group>
                  ))}
                </Stack>
              </>
            )}
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card withBorder>
            <Text fw={600} mb="sm">
              Ingresos vs Gastos ({months} meses)
            </Text>
            {loadingMonthly ? (
              <Skeleton height={320} />
            ) : (
              <BarChart
                h={320}
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
