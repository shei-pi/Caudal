import {
  ActionIcon,
  Badge,
  Button,
  Card,
  ColorSwatch,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconTrash, IconEdit } from "@tabler/icons-react";
import { useState } from "react";
import { categoriesApi } from "@/api/categories";
import { rulesApi } from "@/api/rules";
import type { Category, CategorizationRule } from "@/types";

function RuleRow({ rule, onDelete }: { rule: CategorizationRule; onDelete: () => void }) {
  return (
    <Group justify="space-between" p="xs" style={{ borderBottom: "1px solid var(--mantine-color-gray-2)" }}>
      <Group gap="xs">
        <Badge size="xs" variant="outline">
          {rule.match_type}
        </Badge>
        <Text size="sm" ff="monospace">
          {rule.pattern}
        </Text>
      </Group>
      <ActionIcon size="sm" color="red" variant="subtle" onClick={onDelete}>
        <IconTrash size={12} />
      </ActionIcon>
    </Group>
  );
}

function CategoryCard({ category, rules, allCategories }: {
  category: Category;
  rules: CategorizationRule[];
  allCategories: Category[];
}) {
  const qc = useQueryClient();
  const [rulePattern, setRulePattern] = useState("");
  const [ruleMatchType, setRuleMatchType] = useState("contains");

  const addRuleMutation = useMutation({
    mutationFn: () =>
      rulesApi.create({ category_id: category.id, pattern: rulePattern, match_type: ruleMatchType }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rules"] });
      setRulePattern("");
      notifications.show({ message: "Regla agregada", color: "teal" });
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: (id: number) => rulesApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  const catRules = rules.filter((r) => r.category_id === category.id);

  return (
    <Card withBorder p="sm">
      <Group justify="space-between" mb="xs">
        <Group gap="xs">
          <ColorSwatch color={category.color} size={14} />
          <Text fw={600} size="sm">
            {category.name}
          </Text>
          {category.is_income && (
            <Badge size="xs" color="teal" variant="light">
              Ingreso
            </Badge>
          )}
        </Group>
        <Text size="xs" c="dimmed">
          {catRules.length} regla(s)
        </Text>
      </Group>

      {catRules.map((rule) => (
        <RuleRow
          key={rule.id}
          rule={rule}
          onDelete={() => deleteRuleMutation.mutate(rule.id)}
        />
      ))}

      <Group mt="xs" gap="xs">
        <TextInput
          size="xs"
          placeholder="Nuevo patrón..."
          value={rulePattern}
          onChange={(e) => setRulePattern(e.target.value)}
          style={{ flex: 1 }}
        />
        <Select
          size="xs"
          data={["contains", "startswith", "regex"]}
          value={ruleMatchType}
          onChange={(v) => setRuleMatchType(v ?? "contains")}
          w={120}
        />
        <ActionIcon
          size="sm"
          color="teal"
          onClick={() => addRuleMutation.mutate()}
          disabled={!rulePattern.trim()}
          loading={addRuleMutation.isPending}
        >
          <IconPlus size={12} />
        </ActionIcon>
      </Group>
    </Card>
  );
}

export default function Categories() {
  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["categories-flat"],
    queryFn: categoriesApi.flat,
  });
  const { data: rules = [] } = useQuery({
    queryKey: ["rules"],
    queryFn: rulesApi.list,
  });

  const expenses = categories.filter((c) => !c.is_income);
  const incomes = categories.filter((c) => c.is_income);

  return (
    <Stack gap="md">
      <Title order={2}>Categorías y Reglas</Title>

      <Title order={4}>Gastos</Title>
      <Stack gap="xs">
        {expenses.map((cat) => (
          <CategoryCard key={cat.id} category={cat} rules={rules} allCategories={categories} />
        ))}
      </Stack>

      <Title order={4} mt="sm">
        Ingresos
      </Title>
      <Stack gap="xs">
        {incomes.map((cat) => (
          <CategoryCard key={cat.id} category={cat} rules={rules} allCategories={categories} />
        ))}
      </Stack>
    </Stack>
  );
}
