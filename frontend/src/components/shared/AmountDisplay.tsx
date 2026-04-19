import { Text } from "@mantine/core";

interface Props {
  amount: number;
  currency?: string;
  txType?: "debit" | "credit";
  size?: string;
  fw?: number;
}

export default function AmountDisplay({ amount, currency = "ARS", txType, size, fw }: Props) {
  const sign = txType === "credit" ? "+" : txType === "debit" ? "-" : "";
  const color = txType === "credit" ? "green" : txType === "debit" ? "red" : undefined;
  const formatted = amount.toLocaleString("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <Text component="span" c={color} size={size as any} fw={fw}>
      {sign}
      {currency === "USD" ? "U$S " : "$ "}
      {formatted}
    </Text>
  );
}
