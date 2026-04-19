import {
  Badge,
  Card,
  Divider,
  Grid,
  Group,
  Skeleton,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/api/analytics";
import AmountDisplay from "@/components/shared/AmountDisplay";

export default function NetWorth() {
  const { data, isLoading } = useQuery({
    queryKey: ["net-worth"],
    queryFn: analyticsApi.netWorth,
  });

  if (isLoading) return <Skeleton height={400} />;

  const assets = data?.accounts.filter((a) => !a.is_liability) ?? [];
  const liabilities = data?.accounts.filter((a) => a.is_liability) ?? [];

  return (
    <Stack gap="md">
      <Title order={2}>Patrimonio</Title>

      <Grid>
        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Card withBorder bg="teal.0">
            <Text size="sm" c="dimmed">
              Activos
            </Text>
            <AmountDisplay amount={data?.total_assets_ars ?? 0} currency="ARS" size="xl" fw={700} />
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Card withBorder bg="red.0">
            <Text size="sm" c="dimmed">
              Pasivos
            </Text>
            <AmountDisplay
              amount={data?.total_liabilities_ars ?? 0}
              currency="ARS"
              txType="debit"
              size="xl"
              fw={700}
            />
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Card withBorder>
            <Text size="sm" c="dimmed">
              Patrimonio neto
            </Text>
            <AmountDisplay amount={data?.net_worth_ars ?? 0} currency="ARS" size="xl" fw={700} />
          </Card>
        </Grid.Col>
      </Grid>

      <Card withBorder>
        <Title order={4} mb="md">
          Cuentas
        </Title>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Nombre</Table.Th>
              <Table.Th>Tipo</Table.Th>
              <Table.Th ta="right">Saldo</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            <Table.Tr>
              <Table.Td colSpan={3}>
                <Text size="xs" fw={600} c="teal" tt="uppercase">
                  Activos
                </Text>
              </Table.Td>
            </Table.Tr>
            {assets.map((acc) => (
              <Table.Tr key={acc.id}>
                <Table.Td>{acc.name}</Table.Td>
                <Table.Td>
                  <Badge size="xs" variant="light">
                    {acc.account_type}
                  </Badge>
                </Table.Td>
                <Table.Td ta="right">
                  <AmountDisplay amount={acc.balance} currency={acc.currency} />
                </Table.Td>
              </Table.Tr>
            ))}
            {liabilities.length > 0 && (
              <>
                <Table.Tr>
                  <Table.Td colSpan={3}>
                    <Text size="xs" fw={600} c="red" tt="uppercase" mt="xs">
                      Pasivos
                    </Text>
                  </Table.Td>
                </Table.Tr>
                {liabilities.map((acc) => (
                  <Table.Tr key={acc.id}>
                    <Table.Td>{acc.name}</Table.Td>
                    <Table.Td>
                      <Badge size="xs" variant="light" color="red">
                        {acc.account_type}
                      </Badge>
                    </Table.Td>
                    <Table.Td ta="right">
                      <AmountDisplay amount={Math.abs(acc.balance)} currency={acc.currency} txType="debit" />
                    </Table.Td>
                  </Table.Tr>
                ))}
              </>
            )}
          </Table.Tbody>
        </Table>
      </Card>

      {(data?.holdings_total_ars ?? 0) > 0 && (
        <Card withBorder>
          <Group justify="space-between">
            <Title order={4}>Instrumentos financieros</Title>
            <AmountDisplay amount={data!.holdings_total_ars} currency="ARS" fw={600} />
          </Group>
        </Card>
      )}
    </Stack>
  );
}
