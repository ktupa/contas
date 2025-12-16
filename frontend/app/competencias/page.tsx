'use client';

import { useEffect, useState } from 'react';
import { Shell } from '@/components/Shell';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { 
  Title, 
  Button, 
  Table,
  Badge,
  Stack,
  Group,
  Card,
  Text,
  Modal,
  Select,
  ThemeIcon,
  SimpleGrid,
  Center,
  Progress,
  Paper,
  ActionIcon,
  Tooltip
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconCalendar, 
  IconPlus, 
  IconChartBar, 
  IconUsers,
  IconCash,
  IconCheck,
  IconEdit,
  IconTrash
} from '@tabler/icons-react';
import api from '@/lib/api';
import { formatCurrency, MONTHS } from '@/lib/constants';
import { useRouter } from 'next/navigation';

function CompetenciasContent() {
  const router = useRouter();
  const currentDate = new Date();
  const [month, setMonth] = useState(String(currentDate.getMonth() + 1));
  const [year, setYear] = useState(String(currentDate.getFullYear()));
  const [competencies, setCompetencies] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpened, setModalOpened] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string>('aberta');
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    loadCompetencies();
    loadEmployees();
  }, [month, year]);

  const loadEmployees = async () => {
    try {
      const { data } = await api.get('/employees');
      setEmployees(data.filter((e: any) => e.active));
    } catch (error) {
      console.error('Erro ao carregar colaboradores:', error);
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
              api.get(`/competencies/${comp.id}/summary`).catch(() => ({ data: {} })),
              api.get(`/employees/${comp.employee_id}`).catch(() => ({ data: { name: `Colaborador #${comp.employee_id}` } }))
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
    } catch (error) {
      console.error('Erro ao carregar competências:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCreate = () => {
    setEditingId(null);
    setSelectedEmployee(null);
    setSelectedStatus('aberta');
    setModalOpened(true);
  };

  const handleOpenEdit = (comp: any) => {
    setEditingId(comp.id);
    setSelectedEmployee(String(comp.employee_id));
    setSelectedStatus(comp.status);
    setModalOpened(true);
  };

  const handleSubmit = async () => {
    if (!selectedEmployee) {
      notifications.show({
        title: 'Atenção',
        message: 'Selecione um colaborador',
        color: 'yellow',
      });
      return;
    }

    setCreating(true);
    try {
      if (editingId) {
        await api.put(`/competencies/${editingId}`, {
          status: selectedStatus
        });
        notifications.show({
          title: 'Sucesso',
          message: 'Competência atualizada com sucesso!',
          color: 'green',
        });
      } else {
        await api.post('/competencies', {
          employee_id: parseInt(selectedEmployee),
          month: parseInt(month),
          year: parseInt(year),
          status: selectedStatus
        });
        notifications.show({
          title: 'Sucesso',
          message: 'Competência criada com sucesso!',
          color: 'green',
        });
      }

      setModalOpened(false);
      setSelectedEmployee(null);
      setEditingId(null);
      loadCompetencies();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao salvar competência',
        color: 'red',
      });
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Deseja realmente excluir esta competência?')) return;
    
    try {
      await api.delete(`/competencies/${id}`);
      notifications.show({
        title: 'Sucesso',
        message: 'Competência excluída com sucesso!',
        color: 'green',
      });
      loadCompetencies();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao excluir competência',
        color: 'red',
      });
    }
  };

  // Calcular totais
  const totals = competencies.reduce((acc, comp) => {
    const summary = comp.summary || {};
    return {
      previsto: acc.previsto + (Number(summary.total_previsto) || 0),
      pago: acc.pago + (Number(summary.total_pago) || 0),
    };
  }, { previsto: 0, pago: 0 });

  const percentagePaid = totals.previsto > 0 ? (totals.pago / totals.previsto) * 100 : 0;

  return (
    <Shell>
      <Stack gap="lg">
        {/* Header */}
        <Paper p="md" radius="md" withBorder>
          <Group justify="space-between" align="center">
            <div>
              <Title order={2}>Competências</Title>
              <Text c="dimmed" size="sm">
                Gerencie as competências mensais dos colaboradores
              </Text>
            </div>
            <Group>
              <Select
                leftSection={<IconCalendar size={16} />}
                value={month}
                onChange={(val) => setMonth(val || '1')}
                data={MONTHS.map(m => ({ value: String(m.value), label: m.label }))}
                style={{ width: 150 }}
              />
              <Select
                value={year}
                onChange={(val) => setYear(val || String(currentDate.getFullYear()))}
                data={[
                  { value: '2024', label: '2024' },
                  { value: '2025', label: '2025' },
                  { value: '2026', label: '2026' },
                ]}
                style={{ width: 100 }}
              />
              <Button 
                leftSection={<IconPlus size={16} />}
                variant="gradient"
                gradient={{ from: 'violet', to: 'purple' }}
                onClick={handleOpenCreate}
              >
                Nova Competência
              </Button>
            </Group>
          </Group>
        </Paper>

        {/* KPIs */}
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Text size="sm" c="dimmed">Total Competências</Text>
                <Text size="xl" fw={700}>{competencies.length}</Text>
              </div>
              <ThemeIcon size={50} radius="md" variant="light" color="blue">
                <IconCalendar size={28} />
              </ThemeIcon>
            </Group>
          </Card>

          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Text size="sm" c="dimmed">Total Previsto</Text>
                <Text size="xl" fw={700}>{formatCurrency(totals.previsto)}</Text>
              </div>
              <ThemeIcon size={50} radius="md" variant="light" color="violet">
                <IconCash size={28} />
              </ThemeIcon>
            </Group>
          </Card>

          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Text size="sm" c="dimmed">Total Pago</Text>
                <Text size="xl" fw={700} c="green">{formatCurrency(totals.pago)}</Text>
              </div>
              <ThemeIcon size={50} radius="md" variant="light" color="green">
                <IconCheck size={28} />
              </ThemeIcon>
            </Group>
            <Progress value={percentagePaid} size="sm" mt="md" color="green" radius="xl" />
          </Card>
        </SimpleGrid>

        {/* Tabela */}
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          {loading ? (
            <Center h={200}>
              <Text c="dimmed">Carregando...</Text>
            </Center>
          ) : competencies.length === 0 ? (
            <Center h={200}>
              <Stack align="center">
                <IconCalendar size={48} color="gray" />
                <Text c="dimmed">Nenhuma competência encontrada para este período</Text>
                <Button 
                  variant="light" 
                  leftSection={<IconPlus size={16} />}
                  onClick={handleOpenCreate}
                >
                  Criar Primeira Competência
                </Button>
              </Stack>
            </Center>
          ) : (
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Colaborador</Table.Th>
                  <Table.Th>Período</Table.Th>
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
                  
                  return (
                    <Table.Tr key={comp.id}>
                      <Table.Td>
                        <Group gap="sm">
                          <ThemeIcon size="sm" radius="xl" variant="light">
                            <IconUsers size={14} />
                          </ThemeIcon>
                          <Text fw={500}>{comp.employee_name || `Colaborador #${comp.employee_id}`}</Text>
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        <Badge variant="light">
                          {String(comp.month).padStart(2, '0')}/{comp.year}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Badge 
                          variant="gradient"
                          gradient={comp.status === 'aberta' ? 
                            { from: 'blue', to: 'cyan' } : 
                            comp.status === 'fechada' ?
                            { from: 'green', to: 'teal' } :
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
                        <Group gap={4}>
                          <Text c="green" fw={600}>{formatCurrency(Math.abs(pago))}</Text>
                          {previsto > 0 && pago > 0 && (
                            <Badge size="xs" color="green" variant="light">
                              {Math.round((Math.abs(pago) / Math.abs(previsto)) * 100)}%
                            </Badge>
                          )}
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        <Stack gap={4}>
                          <Group gap="xs">
                            <Text c={saldo > 0 ? 'orange' : 'green'} fw={700}>
                              {formatCurrency(Math.abs(saldo))}
                            </Text>
                            {saldo === 0 && (
                              <Badge size="xs" color="green" variant="filled">✓ Pago</Badge>
                            )}
                          </Group>
                          {previsto > 0 && (
                            <Progress 
                              value={(Math.abs(pago) / Math.abs(previsto)) * 100} 
                              size="xs" 
                              color={saldo === 0 ? 'green' : 'orange'}
                              radius="xl"
                            />
                          )}
                        </Stack>
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Tooltip label="Gerenciar Valores e Rubricas">
                            <ActionIcon 
                              color="violet" 
                              variant="gradient"
                              gradient={{ from: 'violet', to: 'purple' }}
                              onClick={() => router.push(`/competencias/${comp.id}`)}
                            >
                              <IconCash size={16} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Ver Detalhes">
                            <ActionIcon 
                              color="indigo" 
                              variant="light"
                              onClick={() => router.push(`/competencias/${comp.id}`)}
                            >
                              <IconChartBar size={16} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Editar">
                            <ActionIcon 
                              color="blue" 
                              variant="light"
                              onClick={() => handleOpenEdit(comp)}
                            >
                              <IconEdit size={16} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Excluir">
                            <ActionIcon 
                              color="red" 
                              variant="light"
                              onClick={() => handleDelete(comp.id)}
                            >
                              <IconTrash size={16} />
                            </ActionIcon>
                          </Tooltip>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          )}
        </Card>

        {/* Modal Nova/Editar Competência */}
        <Modal
          opened={modalOpened}
          onClose={() => { setModalOpened(false); setEditingId(null); }}
          title={editingId ? 'Editar Competência' : 'Nova Competência'}
          size="md"
        >
          <Stack>
            <Text size="sm" c="dimmed">
              {editingId 
                ? 'Altere o status da competência'
                : `Criar nova competência para ${MONTHS.find(m => m.value === parseInt(month))?.label}/${year}`
              }
            </Text>

            {!editingId && (
              <Select
                label="Colaborador"
                placeholder="Selecione um colaborador"
                data={employees.map(e => ({ value: String(e.id), label: e.name }))}
                value={selectedEmployee}
                onChange={setSelectedEmployee}
                searchable
                required
              />
            )}

            <Select
              label="Status"
              data={[
                { value: 'aberta', label: 'Aberta' },
                { value: 'fechada', label: 'Fechada' },
                { value: 'cancelada', label: 'Cancelada' },
              ]}
              value={selectedStatus}
              onChange={(val) => setSelectedStatus(val || 'aberta')}
              required
            />

            <Group justify="flex-end" mt="md">
              <Button variant="light" onClick={() => { setModalOpened(false); setEditingId(null); }}>
                Cancelar
              </Button>
              <Button 
                variant="gradient"
                gradient={{ from: 'violet', to: 'purple' }}
                onClick={handleSubmit}
                loading={creating}
              >
                {editingId ? 'Salvar Alterações' : 'Criar Competência'}
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Shell>
  );
}

export default function CompetenciasPage() {
  return (
    <ProtectedRoute>
      <CompetenciasContent />
    </ProtectedRoute>
  );
}
