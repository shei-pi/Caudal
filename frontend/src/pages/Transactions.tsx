import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Pagination,
  Paper,
  Select,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDebouncedValue, useDisclosure } from "@mantine/hooks";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import {
  IconEdit,
  IconFilter,
  IconPlus,
  IconRefresh,
  IconRepeat,
  IconTrash,
  IconAlertTriangle,
} from "@tabler/icons-react";
import { useState } from "react";
import dayjs from "dayjs";
import { transactionsApi } from "@/api/transactions";
import { accountsApi } from "@/api/accounts";
import TransactionForm from "@/components/transactions/TransactionForm";
import AmountDisplay from "@/components/shared/AmountDisplay";
import CategoryBadge from "@/components/shared/CategoryBadge";
import type { Transaction } from "@/types";

export default function Transactions() {
  const qc = useQueryClient();
  const [opened, { open, close }] = useDisclosure();
  const [editing, setEditing] = useState<Transaction | undefined>();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [accountFilter, setAccountFilter] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [debouncedSearch] = useDebouncedValue(search, 300);

  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["transactions", page, debouncedSearch, accountFilter, typeFilter],
    queryFn: () =>
      transactionsApi.list({
        page,
        page_size: 50,
        search: debouncedSearch || undefined,
        account_id: accountFilter ? Number(accountFilter) : undefined,
        tx_type: typeFilter ?? undefined,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: transactionsApi.remove,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      notifications.show({ message: "Movimiento eliminado", color: "orange" });
    },
  });

  const runCategorizationMutation = useMutation({
    mutationFn: transactionsApi.runCategorization,
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      notifications.show({
        message: `Categorizados: ${res.updated} de ${res.total_checked}`,
        color: "teal",
      });
    },
  });

  const openCreate = () => {
    setEditing(undefined);
    open();
  };

  const openEdit = (tx: Transaction) => {
    setEditing(tx);
    open();
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>Movimientos</Title>
        <Group>
          <Tooltip label="Re-categorizar sin categoría">
            <ActionIcon
              variant="light"
              color="teal"
              onClick={() => runCategorizationMutation.mutate()}
              loading={runCategorizationMutation.isPending}
            >
              <IconRefresh size={16} />
            </ActionIcon>
          </Tooltip>
          <Button leftSection={<IconPlus size={16} />} onClick={openCreate}>
            Nuevo
          </Button>
        </Group>
      </Group>

      <Group gap="sm">
        <TextInput
          placeholder="Buscar..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          leftSection={<IconFilter size={14} />}
          style={{ flex: 1 }}
        />
        <Select
          placeholder="Cuenta"
          data={[
            { value: "", label: "Todas las cuentas" },
            ...accounts.map((a) => ({ value: String(a.id), label: a.name })),
          ]}
          value={accountFilter}
          onChange={(v) => { setAccountFilter(v || null); setPage(1); }}
          clearable
          w={180}
        />
        <Select
          placeholder="Tipo"
          data={[
            { value: "debit", label: "Débito" },
            { value: "credit", label: "Crédito" },
            { value: "transfer", label: "Transferencia" },
          ]}
          value={typeFilter}
          onChange={(v) => { setTypeFilter(v || null); setPage(1); }}
          clearable
          w={130}
        />
      </Group>

      <Paper withBorder>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Fecha</Table.Th>
              <Table.Th>Descripción</Table.Th>
              <Table.Th>Categoría</Table.Th>
              <Table.Th ta="right">Importe</Table.Th>
              <Table.Th w={80}></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <Table.Tr key={i}>
                    <Table.Td colSpan={5}>
                      <Skeleton height={20} />
                    </Table.Td>
                  </Table.Tr>
                ))
              : data?.items.map((tx) => (
                  <Table.Tr key={tx.id}>
                    <Table.Td>
                      <Text size="sm" style={{ whiteSpace: "nowrap" }}>
                        {dayjs(tx.transaction_date).format("DD/MM/YY")}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Group gap={6}>
                        <Text size="sm" style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {tx.description}
                        </Text>
                        {tx.is_recurring && (
                          <Tooltip label="Recurrente">
                            <IconRepeat size={14} color="var(--mantine-color-teal-6)" />
                          </Tooltip>
                        )}
                        {tx.is_anomaly && (
                          <Tooltip label="Anomalía detectada">
                            <IconAlertTriangle size={14} color="var(--mantine-color-orange-6)" />
                          </Tooltip>
                        )}
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <CategoryBadge category={tx.category} />
                    </Table.Td>
                    <Table.Td ta="right">
                      <AmountDisplay
                        amount={tx.amount}
                        currency={tx.currency}
                        txType={tx.tx_type}
                        size="sm"
                        fw={500}
                      />
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4} justify="flex-end">
                        <ActionIcon variant="subtle" onClick={() => openEdit(tx)}>
                          <IconEdit size={14} />
                        </ActionIcon>
                        <ActionIcon
                          variant="subtle"
                          color="red"
                          onClick={() => deleteMutation.mutate(tx.id)}
                        >
                          <IconTrash size={14} />
                        </ActionIcon>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
          </Table.Tbody>
        </Table>
      </Paper>

      {data && data.pages > 1 && (
        <Pagination
          total={data.pages}
          value={page}
          onChange={setPage}
          mx="auto"
        />
      )}

      <Text size="sm" c="dimmed">
        {data?.total ?? 0} movimiento(s) encontrado(s)
      </Text>

      <TransactionForm opened={opened} onClose={close} transaction={editing} />
    </Stack>
  );
}
