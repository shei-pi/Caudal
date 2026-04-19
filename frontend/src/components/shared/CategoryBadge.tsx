import { Badge } from "@mantine/core";
import type { Category } from "@/types";

interface Props {
  category: Category | null | undefined;
}

export default function CategoryBadge({ category }: Props) {
  if (!category) {
    return (
      <Badge color="gray" variant="outline" size="sm">
        Sin categorizar
      </Badge>
    );
  }
  return (
    <Badge
      size="sm"
      style={{ backgroundColor: category.color + "22", color: category.color, border: `1px solid ${category.color}44` }}
    >
      {category.name}
    </Badge>
  );
}
