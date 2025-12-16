'use client';

import { useEffect, useState } from 'react';
import { Shell } from '@/components/Shell';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { 
  Grid, 
  Card, 
  Text, 
  Title, 
  Badge, 
  Stack,
  Group,
  Table,
  Button,
  Select,
  ThemeIcon,
  Progress,
  RingProgress,
  Paper,
  SimpleGrid,
  Center,
  Box
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { 
  IconCash, 
  IconAlertCircle, 
  IconCheck,
  IconClock,
  IconTrendingUp,
  IconTrendingDown,
  IconUsers,
  IconReceipt,
  IconCalendar,
  IconChartBar
} from '@tabler/icons-react';
import api from '@/lib/api';
import { formatCurrency, MONTHS } from '@/lib/constants';
import { useRouter } from 'next/navigation';

function DashboardContent() {
  const router = useRouter();
  const currentDate = new Date();
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [month, setMonth] = useState(String(currentDate.getMonth() + 1));
  const [year, setYear] = useState(String(currentDate.getFullYear()));
  const [competencies, setCompetencies] = useState<any[]>([]);
  const [stats, setStats] = useState({
    totalEmployees: 0,
    totalPayments: 0,
    averagePayment: 0
  });
  const [expensesTotal, setExpensesTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCompetencies();
    loadStats();
    loadExpenses();
  }, [month, year]);

  const loadExpenses = async () => {
    try {
      const startDate = `${year}-${month.padStart(2, '0')}-01`;
      const lastDay = new Date(parseInt(year), parseInt(month), 0).getDate();
      const endDate = `${year}-${month.padStart(2, '0')}-${lastDay}`;
      
      const { data } = await api.get(`/expenses?start_date=${startDate}&end_date=${endDate}`);
      const total = data.reduce((acc: number, curr: any) => acc + parseFloat(curr.amount), 0);
      setExpensesTotal(total);
    } catch (error) {
      console.error('Erro ao carregar despesas:', error);
    }
  };

  const loadStats = async () => {
    try {
      const { data: employees } = await api.get('/employees');
      const activeEmployees = employees.filter((e: any) => e.active);
      setStats(prev => ({
        ...prev,
        totalEmployees: activeEmployees.length
      }));
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error);
    }
  };

  const loadCompetencies = async () => {
    try {
      setLoading(true);
      const { data } = await api.get(`/competencies?month=${month}&year=${year}`);
      
      // Carregar resumos e dados do colaborador
      const competenciesWithData = await Promise.all(
        data.map(async (comp: any) => {
          try {
            const [summaryRes, employeeRes] = await Promise.all([
              api.get(`/competencies/${comp.id}/summary`),
              api.get(`/employees/${comp.employee_id}`)
            ]);
            return { 
              ...comp, 
              summary: summaryRes.data,
              employee_name: employeeRes.data.name 
            };
          } catch {
            return comp;
          }
        })
      );
      
      setCompetencies(competenciesWithData);
      
      // Calcular estatísticas
      if (competenciesWithData.length > 0) {
        const totalPaid = competenciesWithData.reduce((sum, c) => 
          sum + (Number(c.summary?.total_pago) || 0), 0
        );
        setStats(prev => ({
          ...prev,
          totalPayments: competenciesWithData.length,
          averagePayment: totalPaid / competenciesWithData.length
        }));
      }
    } catch (error) {
      console.error('Erro ao carregar competências:', error);
    } finally {
      setLoading(false);
    }
  };

  // Calcular totais gerais
  const totals = competencies.reduce((acc, comp) => {
    const summary = comp.summary || {};
    return {
      previsto: acc.previsto + (Number(summary.total_previsto) || 0),
      pago: acc.pago + (Number(summary.total_pago) || 0),
      pendente: acc.pendente + (Number(summary.total_pendente) || 0),
      excecoes: acc.excecoes + (Number(summary.total_excecoes) || 0),
    };
  }, { previsto: 0, pago: 0, pendente: 0, excecoes: 0 });

  const percentagePaid = totals.previsto > 0 ? (totals.pago / totals.previsto) * 100 : 0;

  return (
    <Shell>
      <Stack gap={isMobile ? 'sm' : 'lg'}>
        {/* Header */}
        <Paper p={isMobile ? 'sm' : 'md'} radius="md" withBorder>
          <Stack gap="sm">
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Box>
                <Title order={1} size={isMobile ? 'h3' : 'h2'} mb={4}>
                  Dashboard
                </Title>
                <Text c="dimmed" size={isMobile ? 'xs' : 'sm'}>
                  Visão geral dos pagamentos
                </Text>
              </Box>
            </Group>
            <Group gap="xs" justify={isMobile ? 'stretch' : 'flex-end'} grow={isMobile}>
              <Select
                leftSection={<IconCalendar size={16} />}
                value={month}
                onChange={(val) => setMonth(val || '1')}
                data={MONTHS.map(m => ({ value: String(m.value), label: m.label }))}
                style={{ width: isMobile ? '100%' : 150 }}
                size={isMobile ? 'md' : 'sm'}
              />
              <Select
                value={year}
                onChange={(val) => setYear(val || String(currentDate.getFullYear()))}
                data={[
                  { value: '2024', label: '2024' },
                  { value: '2025', label: '2025' },
                  { value: '2026', label: '2026' },
                ]}
                style={{ width: isMobile ? '100%' : 100 }}
                size={isMobile ? 'md' : 'sm'}
              />
            </Group>
          </Stack>
        </Paper>

        {/* KPIs - Cards principais */}
        <SimpleGrid cols={isMobile ? 1 : 4} spacing={isMobile ? 'sm' : 'lg'}>
          <Card shadow="md" padding={isMobile ? 'md' : 'lg'} radius="md" withBorder style={{ 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white'
          }}>
            <Group justify="space-between" mb="md" wrap="nowrap">
              <ThemeIcon size={isMobile ? 40 : 50} radius="md" variant="white" color="violet">
                <IconCash size={isMobile ? 22 : 28} />
              </ThemeIcon>
              <div style={{ textAlign: 'right' }}>
                <Text size="xs" opacity={0.9} mb={4}>Total Previsto</Text>
                <Text size={isMobile ? 'lg' : 'xl'} fw={900}>{formatCurrency(totals.previsto)}</Text>
              </div>
            </Group>
            <Progress value={100} size="sm" radius="xl" color="white" />
          </Card>

          <Card shadow="md" padding="lg" radius="md" withBorder style={{ 
            background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
            color: 'white'
          }}>
            <Group justify="space-between" mb="md">
              <ThemeIcon size={50} radius="md" variant="white" color="teal">
                <IconCheck size={28} />
              </ThemeIcon>
              <div style={{ textAlign: 'right' }}>
                <Text size="xs" opacity={0.9} mb={4}>Total Pago</Text>
                <Text size="xl" fw={900}>{formatCurrency(totals.pago)}</Text>
              </div>
            </Group>
            <Progress value={percentagePaid} size="sm" radius="xl" color="white" />
          </Card>

          <Card shadow="md" padding="lg" radius="md" withBorder style={{ 
            background: 'linear-gradient(135deg, #FF512F 0%, #DD2476 100%)',
            color: 'white'
          }}>
            <Group justify="space-between" mb="md">
              <ThemeIcon size={50} radius="md" variant="white" color="red">
                <IconTrendingDown size={28} />
              </ThemeIcon>
              <div style={{ textAlign: 'right' }}>
                <Text size="xs" opacity={0.9} mb={4}>Total Despesas</Text>
                <Text size="xl" fw={900}>{formatCurrency(expensesTotal)}</Text>
              </div>
            </Group>
            <Progress value={100} size="sm" radius="xl" color="white" />
          </Card>

          <Card shadow="md" padding="lg" radius="md" withBorder style={{ 
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            color: 'white'
          }}>
            <Group justify="space-between" mb="md">
              <ThemeIcon size={50} radius="md" variant="white" color="orange">
                <IconClock size={28} />
              </ThemeIcon>
              <div style={{ textAlign: 'right' }}>
                <Text size="xs" opacity={0.9} mb={4}>Pendências</Text>
                <Text size="xl" fw={900}>{totals.pendente}</Text>
              </div>
            </Group>
            <Progress value={(totals.pendente / (competencies.length || 1)) * 100} size="sm" radius="xl" color="white" />
          </Card>

          <Card shadow="md" padding="lg" radius="md" withBorder style={{ 
            background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            color: 'white'
          }}>
            <Group justify="space-between" mb="md">
              <ThemeIcon size={50} radius="md" variant="white" color="blue">
                <IconUsers size={28} />
              </ThemeIcon>
              <div style={{ textAlign: 'right' }}>
                <Text size="xs" opacity={0.9} mb={4}>Colaboradores Ativos</Text>
                <Text size="xl" fw={900}>{stats.totalEmployees}</Text>
              </div>
            </Group>
            <Progress value={100} size="sm" radius="xl" color="white" />
          </Card>
        </SimpleGrid>

        {/* Estatísticas Rápidas */}
        <Grid>
          <Grid.Col span={isMobile ? 12 : 8}>
            <Card shadow="sm" padding="lg" radius="md" withBorder h="100%">
              <Group justify="space-between" mb="md">
                <Title order={3}>
                  <IconReceipt size={24} style={{ verticalAlign: 'middle', marginRight: 8 }} />
                  Competências do Período
                </Title>
                <Badge size="lg" variant="gradient" gradient={{ from: 'blue', to: 'cyan' }}>
                  {competencies.length} registros
                </Badge>
              </Group>
              
              {loading ? (
                <Center h={200}>
                  <Text c="dimmed">Carregando...</Text>
                </Center>
              ) : competencies.length === 0 ? (
                <Center h={200}>
                  <Stack align="center">
                    <IconAlertCircle size={48} color="gray" />
                    <Text c="dimmed">Nenhuma competência encontrada</Text>
                    <Button 
                      variant="light" 
                      leftSection={<IconCalendar size={16} />}
                      onClick={() => router.push('/colaboradores')}
                    >
                      Cadastrar Colaboradores
                    </Button>
                  </Stack>
                </Center>
              ) : (
                <Table striped highlightOnHover withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Colaborador</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Previsto</Table.Th>
                      <Table.Th>Pago</Table.Th>
                      <Table.Th>Saldo</Table.Th>
                      <Table.Th>Ações</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {competencies.map((comp) => {
                      const previsto = Number(comp.summary?.total_previsto) || 0;
                      const pago = Number(comp.summary?.total_pago) || 0;
                      const saldo = Number(comp.summary?.saldo_a_pagar) || 0;
                      const percentPaid = previsto > 0 ? (pago / previsto) * 100 : 0;
                      
                      return (
                      <Table.Tr key={comp.id}>
                        <Table.Td>
                          <Group gap="sm">
                            <ThemeIcon size="md" radius="xl" variant="light">
                              <IconUsers size={16} />
                            </ThemeIcon>
                            <Text fw={500}>{comp.employee_name || `Colaborador #${comp.employee_id}`}</Text>
                          </Group>
                        </Table.Td>
                        <Table.Td>
                          <Badge 
                            variant="gradient"
                            gradient={comp.status === 'aberta' ? 
                              { from: 'blue', to: 'cyan' } : 
                              { from: 'gray', to: 'dark' }
                            }
                          >
                            {comp.status}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text fw={600}>{formatCurrency(previsto)}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <Text c="green" fw={600}>{formatCurrency(pago)}</Text>
                            {percentPaid > 0 && (
                              <Badge size="xs" variant="light" color="green">
                                {percentPaid.toFixed(0)}%
                              </Badge>
                            )}
                          </Group>
                        </Table.Td>
                        <Table.Td>
                          <Text c="orange" fw={600}>{formatCurrency(saldo)}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Button 
                            size="xs" 
                            variant="gradient"
                            gradient={{ from: 'indigo', to: 'cyan' }}
                            onClick={() => router.push(`/competencias/${comp.id}`)}
                            leftSection={<IconChartBar size={14} />}
                          >
                            Detalhes
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Grid.Col>

          <Grid.Col span={isMobile ? 12 : 4}>
            <Stack gap="md">
              {/* Ring Progress - Taxa de Pagamento */}
              <Card shadow="sm" padding="lg" radius="md" withBorder>
                <Title order={4} mb="md">Taxa de Pagamento</Title>
                <Center>
                  <RingProgress
                    size={180}
                    thickness={16}
                    label={
                      <Center>
                        <div style={{ textAlign: 'center' }}>
                          <Text size="xl" fw={700}>
                            {percentagePaid.toFixed(1)}%
                          </Text>
                          <Text size="xs" c="dimmed">
                            concluído
                          </Text>
                        </div>
                      </Center>
                    }
                    sections={[
                      { value: percentagePaid, color: 'teal', tooltip: 'Pago' },
                      { value: 100 - percentagePaid, color: 'gray', tooltip: 'Pendente' },
                    ]}
                  />
                </Center>
              </Card>

              {/* Resumo Financeiro */}
              <Card shadow="sm" padding="lg" radius="md" withBorder>
                <Title order={4} mb="md">Resumo Financeiro</Title>
                <Stack gap="sm">
                  <div>
                    <Group justify="space-between" mb={4}>
                      <Text size="sm" c="dimmed">Média por Colaborador</Text>
                      <Text size="sm" fw={600}>{formatCurrency(stats.averagePayment)}</Text>
                    </Group>
                    <Progress 
                      value={stats.averagePayment > 0 ? 100 : 0} 
                      size="sm" 
                      color="blue" 
                      radius="xl"
                    />
                  </div>
                  
                  <div>
                    <Group justify="space-between" mb={4}>
                      <Text size="sm" c="dimmed">Exceções</Text>
                      <Badge color={totals.excecoes > 0 ? 'red' : 'green'}>
                        {totals.excecoes}
                      </Badge>
                    </Group>
                    <Progress 
                      value={totals.excecoes > 0 ? 100 : 0} 
                      size="sm" 
                      color="red" 
                      radius="xl"
                    />
                  </div>
                </Stack>
              </Card>

              {/* Ações Rápidas */}
              <Card shadow="sm" padding="lg" radius="md" withBorder>
                <Title order={4} mb="md">Ações Rápidas</Title>
                <Stack gap="xs">
                  <Button 
                    fullWidth 
                    variant="light" 
                    leftSection={<IconUsers size={16} />}
                    onClick={() => router.push('/colaboradores')}
                  >
                    Gerenciar Colaboradores
                  </Button>
                  <Button 
                    fullWidth 
                    variant="light" 
                    leftSection={<IconReceipt size={16} />}
                    onClick={() => router.push('/rubricas')}
                  >
                    Gerenciar Rubricas
                  </Button>
                  <Button 
                    fullWidth 
                    variant="light" 
                    leftSection={<IconChartBar size={16} />}
                    onClick={() => router.push('/relatorios')}
                  >
                    Ver Relatórios
                  </Button>
                </Stack>
              </Card>
            </Stack>
          </Grid.Col>
        </Grid>
      </Stack>
    </Shell>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
