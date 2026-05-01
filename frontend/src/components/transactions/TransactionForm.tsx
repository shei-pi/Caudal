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
import { Controller, useForm } from "react-hook-form";
import { accountsApi } from "@/api/accounts";
import { categoriesApi } from "@/api/categories";
import { transactionsApi } from "@/api/transactions";
import type { Transaction } from "@/types";
import dayjs from "dayjs";

const schema = z.object({
  account_id: z.number({ required_error: "Requerido" }),
  transaction_date: z.date({ required_error: "Requerido" }),
  description: z.string().min(1, "Requerido"),
  amount: z.number({ required_error: "Requerido" }).positive("Debe ser positivo"),
  tx_type: z.enum(["debit", "credit"]),
  currency: z.string().default("ARS"),
  category_id: z.number().nullable().optional(),
  notes: z.string().optional(),
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
          tx_type: transaction.tx_type,
          currency: transaction.currency,
          category_id: transaction.category_id,
          notes: transaction.notes ?? undefined,
        }
      : {
          tx_type: "debit",
          currency: "ARS",
        },
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<Transaction>) => transactionsApi.create(data),
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
                label="Cuenta"
                data={accountOptions}
                value={field.value ? String(field.value) : null}
                onChange={(v) => field.onChange(v ? Number(v) : undefined)}
                error={errors.account_id?.message}
                required
              />
            )}
          />
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
          <Controller
            name="tx_type"
            control={control}
            render={({ field }) => (
              <Select
                label="Tipo"
                data={[
                  { value: "debit", label: "Débito (gasto)" },
                  { value: "credit", label: "Crédito (ingreso)" },
                ]}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
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
