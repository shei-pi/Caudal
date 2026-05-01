import {
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { Controller, useForm, useWatch } from "react-hook-form";
import { accountsApi } from "@/api/accounts";
import { categoriesApi } from "@/api/categories";
import { transactionsApi } from "@/api/transactions";
import type { Transaction } from "@/types";
import dayjs from "dayjs";

const schema = z
  .object({
    account_id: z.number({ required_error: "Requerido" }),
    transaction_date: z.date({ required_error: "Requerido" }),
    description: z.string().min(1, "Requerido"),
    amount: z.number({ required_error: "Requerido" }).positive("Debe ser positivo"),
    tx_type: z.enum(["debit", "credit", "transfer"]),
    to_account_id: z.number().optional(),
    currency: z.string().default("ARS"),
    category_id: z.number().nullable().optional(),
    notes: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.tx_type === "transfer" && !data.to_account_id) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Requerido",
        path: ["to_account_id"],
      });
    }
  });

type FormValues = z.infer<typeof schema>;

interface Props {
  opened: boolean;
  onClose: () => void;
  transaction?: Transaction;
}

export default function TransactionForm({ opened, onClose, transaction }: Props) {
  const qc = useQueryClient();
  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
  });
  const { data: categories = [] } = useQuery({
    queryKey: ["categories-flat"],
    queryFn: categoriesApi.flat,
  });

  const { control, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: transaction
      ? {
          account_id: transaction.account_id,
          transaction_date: new Date(transaction.transaction_date),
          description: transaction.description,
          amount: transaction.amount,
          tx_type: transaction.tx_type as "debit" | "credit" | "transfer",
          currency: transaction.currency,
          category_id: transaction.category_id,
          notes: transaction.notes ?? undefined,
        }
      : {
          tx_type: "debit",
          currency: "ARS",
        },
  });

  const txType = useWatch({ control, name: "tx_type" });
  const selectedAccountId = useWatch({ control, name: "account_id" });
  const isTransfer = txType === "transfer";

  const createMutation = useMutation({
    mutationFn: (data: Partial<Transaction> & { to_account_id?: number }) =>
      transactionsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["spending-by-category"] });
      qc.invalidateQueries({ queryKey: ["monthly-summary"] });
      notifications.show({ message: "Movimiento creado", color: "teal" });
      reset();
      onClose();
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.detail ?? "Error al crear";
      notifications.show({ message: msg, color: "red" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Transaction>) => transactionsApi.update(transaction!.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      notifications.show({ message: "Movimiento actualizado", color: "teal" });
      onClose();
    },
  });

  const onSubmit = (values: FormValues) => {
    const payload = {
      ...values,
      transaction_date: dayjs(values.transaction_date).format("YYYY-MM-DD"),
    };
    if (transaction) {
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate(payload);
    }
  };

  const accountOptions = accounts.map((a) => ({
    value: String(a.id),
    label: `${a.name} (${a.currency})`,
  }));

  const destAccountOptions = accounts
    .filter((a) => a.id !== selectedAccountId)
    .map((a) => ({
      value: String(a.id),
      label: `${a.name} (${a.currency})`,
    }));

  const categoryOptions = [
    { value: "", label: "Sin categoría" },
    ...categories.map((c) => ({ value: String(c.id), label: c.name })),
  ];

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={transaction ? "Editar movimiento" : "Nuevo movimiento"}
      size="md"
    >
      <form onSubmit={handleSubmit(onSubmit)}>
        <Stack gap="sm">
          <Controller
            name="account_id"
            control={control}
            render={({ field }) => (
              <Select
                label={isTransfer ? "Cuenta origen" : "Cuenta"}
                data={accountOptions}
                value={field.value ? String(field.value) : null}
                onChange={(v) => field.onChange(v ? Number(v) : undefined)}
                error={errors.account_id?.message}
                required
              />
            )}
          />
          <Controller
            name="tx_type"
            control={control}
            render={({ field }) => (
              <Select
                label="Tipo"
                data={[
                  { value: "debit", label: "Débito (gasto)" },
                  { value: "credit", label: "Crédito (ingreso)" },
                  { value: "transfer", label: "Transferencia" },
                ]}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          {isTransfer && (
            <Controller
              name="to_account_id"
              control={control}
              render={({ field }) => (
                <Select
                  label="Cuenta destino"
                  data={destAccountOptions}
                  value={field.value ? String(field.value) : null}
                  onChange={(v) => field.onChange(v ? Number(v) : undefined)}
                  error={errors.to_account_id?.message}
                  required
                />
              )}
            />
          )}
          <Controller
            name="transaction_date"
            control={control}
            render={({ field }) => (
              <DateInput
                label="Fecha"
                value={field.value}
                onChange={field.onChange}
                error={errors.transaction_date?.message}
                valueFormat="DD/MM/YYYY"
                locale="es"
                required
              />
            )}
          />
          <Controller
            name="description"
            control={control}
            render={({ field }) => (
              <TextInput label="Descripción" {...field} error={errors.description?.message} required />
            )}
          />
          <Group grow>
            <Controller
              name="amount"
              control={control}
              render={({ field }) => (
                <NumberInput
                  label="Importe"
                  value={field.value}
                  onChange={(v) => field.onChange(Number(v))}
                  error={errors.amount?.message}
                  min={0}
                  decimalScale={2}
                  thousandSeparator="."
                  decimalSeparator=","
                  required
                />
              )}
            />
            <Controller
              name="currency"
              control={control}
              render={({ field }) => (
                <Select
                  label="Moneda"
                  data={["ARS", "USD", "USDT"]}
                  value={field.value}
                  onChange={field.onChange}
                />
              )}
            />
          </Group>
          {!isTransfer && (
            <Controller
              name="category_id"
              control={control}
              render={({ field }) => (
                <Select
                  label="Categoría"
                  data={categoryOptions}
                  value={field.value ? String(field.value) : ""}
                  onChange={(v) => field.onChange(v ? Number(v) : null)}
                  clearable
                  searchable
                />
              )}
            />
          )}
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
              {transaction ? "Guardar" : "Crear"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
