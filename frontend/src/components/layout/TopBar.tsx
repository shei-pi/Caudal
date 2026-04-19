import { Badge, Group, Skeleton, Text } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { exchangeRatesApi } from "@/api/exchangeRates";

function RateBadge({ label, rate }: { label: string; rate: number | undefined }) {
  if (!rate) return null;
  return (
    <Group gap={4}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Badge size="sm" variant="light" color="teal">
        ${rate.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
      </Badge>
    </Group>
  );
}

export default function TopBar() {
  const { data, isLoading } = useQuery({
    queryKey: ["exchange-rates-latest"],
    queryFn: exchangeRatesApi.latest,
    refetchInterval: 5 * 60 * 1000,
  });

  if (isLoading) return <Skeleton height={24} width={200} />;
  if (!data) return null;

  return (
    <Group gap="md" visibleFrom="sm">
      <RateBadge label="Blue" rate={data.blue?.sell_rate ?? undefined} />
      <RateBadge label="MEP" rate={data.mep?.sell_rate ?? undefined} />
      <RateBadge label="CCL" rate={data.ccl?.sell_rate ?? undefined} />
    </Group>
  );
}
