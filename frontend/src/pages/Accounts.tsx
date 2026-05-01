import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { IconEdit, IconPlus, IconTrash } from "@tabler/icons-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { Controller, useForm } from "react-hook-form";
import { useState } from "react";
import { accountsApi } from "@/api/accounts";
import type { Account } from "@/types";

const ACCOUNT_TYPES = [
  { value: "checking", label: "Cuenta corriente" },
  { value: "savings", label: "Caja de ahorro" },
  { value: "credit_card", label: "Tarjeta de crédito" },
  { value: "investment", label: "Inversión" },
  { value: "cash", label: "Efectivo" },
  { value: "crypto", label: "Cripto" },
];

const CURRENCIES = ["ARS", "USD", "USDT"];

const schema = z.object({
  name: z.string().min(1, "Requerido"),
  institution: z.string().min(1, "Requerido"),
  currency: z.string().default("ARS"),
  account_type: z.string().default("checking"),
  current_balance: z.number().default(0),
  is_active: z.boolean().default(true),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

function AccountForm({
  opened,
  onClose,
  account,
}: {
  opened: boolean;
  onClose: () => void;
  account?: Account;
}) {
  const qc = useQueryClient();
  const { control, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: account
      ? {
          name: account.name,
          institution: account.institution,
          currency: account.currency,
          account_type: account.account_type,
          current_balance: account.current_balance,
          is_active: account.is_active,
          notes: account.notes ?? undefined,
        }
      : { currency: "ARS", account_type: "checking", current_balance: 0, is_active: true },
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<Account>) => accountsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] });
      notifications.show({ message: "Cuenta creada", color: "teal" });
      reset();
      onClose();
    },
    onError: () => notifications.show({ message: "Error al crear", color: "red" }),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Account>) => accountsApi.update(account!.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] });
      notifications.show({ message: "Cuenta actualizada", color: "teal" });
      onClose();
    },
    onError: () => notifications.show({ message: "Error al actualizar", color: "red" }),
  });

  const onSubmit = (values: FormValues) => {
    if (account) {
      updateMutation.mutate(values);
    } else {
      createMutation.mutate(values);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={account ? "Editar cuenta" : "Nueva cuenta"}
      size="md"
    >
      <form onSubmit={handleSubmit(onSubmit)}>
        <Stack gap="sm">
          <Controller
            name="name"
            control={control}
            render={({ field }) => (
              <TextInput label="Nombre" {...field} error={errors.name?.message} required />
            )}
          />
          <Controller
            name="institution"
            control={control}
            render={({ field }) => (
              <TextInput label="Institución" {...field} error={errors.institution?.message} required />
            )}
          />
          <Group grow>
            <Controller
              name="account_type"
              control={control}
              render={({ field }) => (
                <Select
                  label="Tipo"
                  data={ACCOUNT_TYPES}
                  value={field.value}
                  onChange={field.onChange}
                />
              )}
            />
            <Controller
              name="currency"
              control={control}
              render={({ field }) => (
                <Select
                  label="Moneda"
                  data={CURRENCIES}
                  value={field.value}
                  onChange={field.onChange}
                />
              )}
            />
          </Group>
          <Controller
            name="current_balance"
            control={control}
            render={({ field }) => (
              <NumberInput
                label="Saldo inicial"
                value={field.value}
                onChange={(v) => field.onChange(Number(v))}
                decimalScale={2}
                thousandSeparator="."
                decimalSeparator=","
              />
            )}
          />
          <Controller
            name="is_active"
            control={control}
            render={({ field }) => (
              <Switch
                label="Activa"
                checked={field.value}
                onChange={(e) => field.onChange(e.currentTarget.checked)}
              />
            )}
          />
          <Controller
            name="notes"
            control={control}
            render={({ field }) => (
              <Textarea label="Notas" {...field} rows={2} />
            )}
          />
          <Group justify="flex-end" mt="sm">
            <Button variant="subtle" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              type="submit"
              loading={createMutation.isPending || updateMutation.isPending}
            >
              {account ? "Guardar" : "Crear"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export default function Accounts() {
  const qc = useQueryClient();
  const [formOpened, setFormOpened] = useState(false);
  const [editing, setEditing] = useState<Account | undefined>();

  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => accountsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] });
      notifications.show({ message: "Cuenta eliminada", color: "orange" });
    },
    onError: () => notifications.show({ message: "Error al eliminar", color: "red" }),
  });

  const openNew = () => {
    setEditing(undefined);
    setFormOpened(true);
  };

  const openEdit = (account: Account) => {
    setEditing(account);
    setFormOpened(true);
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>Cuentas</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={openNew}>
          Nueva cuenta
        </Button>
      </Group>

      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>Institución</Table.Th>
            <Table.Th>Tipo</Table.Th>
            <Table.Th>Moneda</Table.Th>
            <Table.Th ta="right">Saldo</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {accounts.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={7}>
                <Text c="dimmed" ta="center" py="lg">
                  No hay cuentas. Creá la primera.
                </Text>
              </Table.Td>
            </Table.Tr>
          )}
          {accounts.map((account) => (
            <Table.Tr key={account.id}>
              <Table.Td fw={500}>{account.name}</Table.Td>
              <Table.Td>{account.institution}</Table.Td>
              <Table.Td>
                <Badge size="xs" variant="light">
                  {ACCOUNT_TYPES.find((t) => t.value === account.account_type)?.label ?? account.account_type}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Badge size="xs" color="blue" variant="outline">
                  {account.currency}
                </Badge>
              </Table.Td>
              <Table.Td ta="right">
                {account.current_balance.toLocaleString("es-AR", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </Table.Td>
              <Table.Td>
                <Badge size="xs" color={account.is_active ? "teal" : "gray"}>
                  {account.is_active ? "Activa" : "Inactiva"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Group gap={4} justify="flex-end">
                  <ActionIcon variant="subtle" onClick={() => openEdit(account)}>
                    <IconEdit size={16} />
                  </ActionIcon>
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    onClick={() => deleteMutation.mutate(account.id)}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <AccountForm
        opened={formOpened}
        onClose={() => setFormOpened(false)}
        account={editing}
      />
    </Stack>
  );
}
