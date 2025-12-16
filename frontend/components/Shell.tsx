'use client';

import { AppShell, Burger, Group, NavLink, Text, Avatar, Menu, Stack, Divider, Box, ActionIcon } from '@mantine/core';
import { useDisclosure, useMediaQuery } from '@mantine/hooks';
import { 
  IconHome, 
  IconUsers, 
  IconReceipt, 
  IconCalendar,
  IconFileAnalytics,
  IconSignature,
  IconLogout,
  IconUser,
  IconCash,
  IconBuildingStore,
  IconCreditCard,
  IconWallet,
  IconFileText,
  IconCertificate,
  IconChevronDown
} from '@tabler/icons-react';
import { useAuthStore } from '@/lib/store';
import { useRouter } from 'next/navigation';
import { SessionMonitor } from './SessionMonitor';

export function Shell({ children }: { children: React.ReactNode }) {
  const [opened, { toggle, close }] = useDisclosure();
  const { user, logout } = useAuthStore();
  const router = useRouter();
  const isMobile = useMediaQuery('(max-width: 768px)');

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const handleNavigation = (path: string) => {
    router.push(path);
    if (isMobile) {
      close();
    }
  };

  return (
    <AppShell
      header={{ height: isMobile ? 60 : 70 }}
      navbar={{ 
        width: isMobile ? '100%' : 280, 
        breakpoint: 'sm', 
        collapsed: { mobile: !opened, desktop: false } 
      }}
      padding={isMobile ? 'xs' : 'md'}
    >
      <AppShell.Header>
        <Group h="100%" px={isMobile ? 'sm' : 'md'} justify="space-between">
          <Group gap={isMobile ? 'xs' : 'sm'}>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Group gap="xs">
              <IconCash size={isMobile ? 24 : 28} color="#667eea" />
              <Text size={isMobile ? 'md' : 'xl'} fw={700}>Financeiro Pro</Text>
            </Group>
          </Group>
          
          <Menu shadow="md" width={200} position="bottom-end">
            <Menu.Target>
              <Group style={{ cursor: 'pointer' }} gap="xs">
                <Avatar color="violet" radius="xl" size={isMobile ? 'sm' : 'md'}>
                  {user?.name?.charAt(0)}
                </Avatar>
                <Box visibleFrom="sm">
                  <Text size="sm" fw={500}>{user?.name}</Text>
                  <Text size="xs" c="dimmed">{user?.role}</Text>
                </Box>
              </Group>
            </Menu.Target>

            <Menu.Dropdown>
              <Menu.Item leftSection={<IconUser size={14} />}>
                Perfil
              </Menu.Item>
              <Menu.Divider />
              <Menu.Item 
                leftSection={<IconLogout size={14} />}
                onClick={handleLogout}
                color="red"
              >
                Sair
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p={isMobile ? 'xs' : 'md'}>
        <Stack gap="xs">
          {isMobile && (
            <>
              <Group px="sm" py="md" style={{ borderBottom: '1px solid #dee2e6' }}>
                <Avatar color="violet" radius="xl" size="md">
                  {user?.name?.charAt(0)}
                </Avatar>
                <div>
                  <Text size="sm" fw={600}>{user?.name}</Text>
                  <Text size="xs" c="dimmed">{user?.role}</Text>
                </div>
              </Group>
            </>
          )}
          
          <NavLink
            label="Dashboard"
            leftSection={<IconHome size="1.2rem" />}
            onClick={() => handleNavigation('/dashboard')}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
          />
          <NavLink
            label="Colaboradores"
            leftSection={<IconUsers size="1.2rem" />}
            onClick={() => handleNavigation('/colaboradores')}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
          />
          <NavLink
            label="Folha de Pagamento"
            leftSection={<IconWallet size="1.2rem" />}
            onClick={() => handleNavigation('/folha')}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
          />
          <NavLink
            label="Empresas"
            leftSection={<IconBuildingStore size="1.2rem" />}
            onClick={() => handleNavigation('/empresas')}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
          />
          <NavLink
            label="Despesas"
            leftSection={<IconCreditCard size="1.2rem" />}
            onClick={() => handleNavigation('/despesas')}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
          />
          <NavLink
            label="Rubricas"
            leftSection={<IconReceipt size="1.2rem" />}
            onClick={() => handleNavigation('/rubricas')}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
          />
          <NavLink
            label="Competências"
            leftSection={<IconCalendar size="1.2rem" />}
            onClick={() => handleNavigation('/competencias')}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
          />
          <NavLink
            label="Relatórios"
            leftSection={<IconFileAnalytics size="1.2rem" />}
            onClick={() => handleNavigation('/relatorios')}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
          />
          <NavLink
            label="Assinaturas"
            leftSection={<IconSignature size="1.2rem" />}
            onClick={() => handleNavigation('/assinaturas')}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
          />
          
          <NavLink
            label="Fiscal"
            leftSection={<IconFileText size="1.2rem" />}
            defaultOpened={false}
            style={{ borderRadius: 8, padding: isMobile ? '12px' : '10px' }}
            childrenOffset={20}
          >
            <NavLink
              label="Certificados"
              leftSection={<IconCertificate size="1rem" />}
              onClick={() => handleNavigation('/fiscal/certificados')}
              style={{ borderRadius: 8 }}
            />
            <NavLink
              label="Notas Fiscais"
              leftSection={<IconFileText size="1rem" />}
              onClick={() => handleNavigation('/fiscal/notas')}
              style={{ borderRadius: 8 }}
            />
          </NavLink>
          
          {isMobile && (
            <>
              <Divider my="sm" />
              <NavLink
                label="Sair"
                leftSection={<IconLogout size="1.2rem" />}
                onClick={handleLogout}
                color="red"
                style={{ borderRadius: 8, padding: '12px' }}
              />
            </>
          )}
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>
        <SessionMonitor />
        {children}
      </AppShell.Main>
    </AppShell>
  );
}
