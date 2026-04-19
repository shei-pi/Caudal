import {
  AppShell as MantineAppShell,
  Burger,
  Group,
  ScrollArea,
  Text,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import type { ReactNode } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

interface Props {
  children: ReactNode;
}

export default function AppShell({ children }: Props) {
  const [opened, { toggle }] = useDisclosure();

  return (
    <MantineAppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <MantineAppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Text fw={700} size="lg" c="teal">
              Caudal
            </Text>
          </Group>
          <TopBar />
        </Group>
      </MantineAppShell.Header>

      <MantineAppShell.Navbar p="md">
        <ScrollArea>
          <Sidebar onNavigate={opened ? toggle : undefined} />
        </ScrollArea>
      </MantineAppShell.Navbar>

      <MantineAppShell.Main>{children}</MantineAppShell.Main>
    </MantineAppShell>
  );
}
