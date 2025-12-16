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
  Modal,
  TextInput,
  NumberInput,
  Select,
  Switch,
  ActionIcon,
  Tooltip,
  Card,
  Text,
  ThemeIcon,
  Paper,
  SimpleGrid,
  Box
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useMediaQuery } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconEdit, IconTrash, IconUsers, IconPlus, IconUserCheck, IconUserX } from '@tabler/icons-react';
import api from '@/lib/api';
import { REGIME_TYPES } from '@/lib/constants';

function ColaboradoresContent() {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [employees, setEmployees] = useState<any[]>([]);
  const [companies, setCompanies] = useState<{value: string, label: string}[]>([]);
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const form = useForm({
    initialValues: {
      name: '',
      email: '',
      cpf: '',
      role_name: '',
      regime: 'CLT',
      base_salary: null as number | null,
      cost_center: '',
      company_id: null as string | null,
      active: true,
    },
  });

  useEffect(() => {
    loadEmployees();
    loadCompanies();
  }, []);

  const loadCompanies = async () => {
    try {
      const { data } = await api.get('/companies');
      setCompanies(data.map((c: any) => ({ value: String(c.id), label: c.name })));
    } catch (error) {
      console.error('Erro ao carregar empresas:', error);
    }
  };

  const loadEmployees = async () => {
    try {
      const { data } = await api.get('/employees');
      setEmployees(data);
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao carregar colaboradores',
        color: 'red',
      });
    }
  };

  const handleOpenCreate = () => {
    setEditingId(null);
    form.reset();
    setOpened(true);
  };

  const handleOpenEdit = (employee: any) => {
    setEditingId(employee.id);
    form.setValues({
      name: employee.name,
      email: employee.email || '',
      cpf: employee.cpf || '',
      role_name: employee.role_name || '',
      regime: employee.regime || 'CLT',
      base_salary: employee.base_salary || null,
      cost_center: employee.cost_center || '',
      company_id: employee.company_id ? String(employee.company_id) : null,
      active: employee.active,
    });
    setOpened(true);
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      const payload = {
        ...values,
        company_id: values.company_id ? parseInt(values.company_id) : null,
      };
      
      if (editingId) {
        await api.put(`/employees/${editingId}`, payload);
        notifications.show({
          title: 'Sucesso',
          message: 'Colaborador atualizado com sucesso!',
          color: 'green',
        });
      } else {
        await api.post('/employees', payload);
        notifications.show({
          title: 'Sucesso',
          message: 'Colaborador criado com sucesso!',
          color: 'green',
        });
      }
      setOpened(false);
      form.reset();
      setEditingId(null);
      loadEmployees();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao salvar colaborador',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Deseja realmente excluir este colaborador?')) return;
    
    try {
      await api.delete(`/employees/${id}`);
      notifications.show({
        title: 'Sucesso',
        message: 'Colaborador excluído com sucesso!',
        color: 'green',
      });
      loadEmployees();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao excluir colaborador',
        color: 'red',
      });
    }
  };

  const activeCount = employees.filter(e => e.active).length;
  const inactiveCount = employees.filter(e => !e.active).length;

  return (
    <Shell>
      <Stack gap="lg">
        {/* Header */}
        <Paper p="md" radius="md" withBorder>
          <Group justify="space-between" align="center">
            <div>
              <Title order={2}>Colaboradores</Title>
              <Text c="dimmed" size="sm">Gerencie os colaboradores da empresa</Text>
            </div>
            <Button 
              leftSection={<IconPlus size={16} />}
              variant="gradient"
              gradient={{ from: 'violet', to: 'purple' }}
              onClick={handleOpenCreate}
            >
              Novo Colaborador
            </Button>
          </Group>
        </Paper>

        {/* KPIs */}
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Text size="sm" c="dimmed">Total Colaboradores</Text>
                <Text size="xl" fw={700}>{employees.length}</Text>
              </div>
              <ThemeIcon size={50} radius="md" variant="light" color="blue">
                <IconUsers size={28} />
              </ThemeIcon>
            </Group>
          </Card>
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Text size="sm" c="dimmed">Ativos</Text>
                <Text size="xl" fw={700} c="green">{activeCount}</Text>
              </div>
              <ThemeIcon size={50} radius="md" variant="light" color="green">
                <IconUserCheck size={28} />
              </ThemeIcon>
            </Group>
          </Card>
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Text size="sm" c="dimmed">Inativos</Text>
                <Text size="xl" fw={700} c="red">{inactiveCount}</Text>
              </div>
              <ThemeIcon size={50} radius="md" variant="light" color="red">
                <IconUserX size={28} />
              </ThemeIcon>
            </Group>
          </Card>
        </SimpleGrid>

        {/* Tabela */}
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Nome</Table.Th>
                <Table.Th>Cargo</Table.Th>
                <Table.Th>Empresa</Table.Th>
                <Table.Th>Regime</Table.Th>
                <Table.Th ta="right">Salário Base</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Ações</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {employees.map((emp) => (
                <Table.Tr key={emp.id}>
                  <Table.Td>
                    <Group gap="sm">
                      <ThemeIcon size="sm" radius="xl" variant="light">
                        <IconUsers size={14} />
                      </ThemeIcon>
                      <div>
                        <Text fw={500}>{emp.name}</Text>
                        {emp.cpf && <Text size="xs" c="dimmed">{emp.cpf}</Text>}
                      </div>
                    </Group>
                  </Table.Td>
                  <Table.Td>{emp.role_name || '-'}</Table.Td>
                  <Table.Td>
                    {companies.find(c => c.value === String(emp.company_id))?.label || '-'}
                  </Table.Td>
                  <Table.Td>
                    <Badge 
                      variant="gradient"
                      gradient={emp.regime === 'CLT' ? { from: 'blue', to: 'cyan' } : { from: 'green', to: 'teal' }}
                    >
                      {emp.regime}
                    </Badge>
                  </Table.Td>
                  <Table.Td ta="right">
                    {emp.base_salary ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(emp.base_salary) : '-'}
                  </Table.Td>
                  <Table.Td>
                    <Badge 
                      variant="gradient"
                      gradient={emp.active ? { from: 'green', to: 'teal' } : { from: 'red', to: 'pink' }}
                    >
                      {emp.active ? 'Ativo' : 'Inativo'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Tooltip label="Editar">
                        <ActionIcon 
                          color="blue" 
                          variant="light"
                          onClick={() => handleOpenEdit(emp)}
                        >
                          <IconEdit size={16} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Excluir">
                        <ActionIcon 
                          color="red" 
                          variant="light"
                          onClick={() => handleDelete(emp.id)}
                        >
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>

        {/* Modal Criar/Editar */}
        <Modal
          opened={opened}
          onClose={() => { setOpened(false); setEditingId(null); form.reset(); }}
          title={editingId ? 'Editar Colaborador' : 'Novo Colaborador'}
          size="md"
        >
          <form onSubmit={form.onSubmit(handleSubmit)}>
            <Stack>
              <TextInput
                label="Nome"
                placeholder="Nome completo"
                required
                {...form.getInputProps('name')}
              />
              <TextInput
                label="E-mail"
                placeholder="email@exemplo.com"
                description="Necessário para envio de recibos para assinatura"
                {...form.getInputProps('email')}
              />
              <Group grow>
                <TextInput
                  label="CPF"
                  placeholder="000.000.000-00"
                  {...form.getInputProps('cpf')}
                />
                <TextInput
                  label="Cargo"
                  placeholder="Ex: Desenvolvedor"
                  required
                  {...form.getInputProps('role_name')}
                />
              </Group>
              <Group grow>
                <Select
                  label="Empresa"
                  placeholder="Selecione a empresa"
                  data={companies}
                  searchable
                  clearable
                  {...form.getInputProps('company_id')}
                />
                <Select
                  label="Regime"
                  required
                  data={REGIME_TYPES}
                  {...form.getInputProps('regime')}
                />
              </Group>
              <Group grow>
                <NumberInput
                  label="Salário Base"
                  placeholder="0,00"
                  decimalScale={2}
                  fixedDecimalScale
                  prefix="R$ "
                  {...form.getInputProps('base_salary')}
                />
                <TextInput
                  label="Centro de Custo"
                  placeholder="Ex: TI-001"
                  {...form.getInputProps('cost_center')}
                />
              </Group>
              {editingId && (
                <Switch
                  label="Colaborador Ativo"
                  checked={form.values.active}
                  onChange={(e) => form.setFieldValue('active', e.currentTarget.checked)}
                />
              )}
              <Group justify="flex-end" mt="md">
                <Button variant="light" onClick={() => { setOpened(false); setEditingId(null); form.reset(); }}>
                  Cancelar
                </Button>
                <Button 
                  type="submit" 
                  loading={loading}
                  variant="gradient"
                  gradient={{ from: 'violet', to: 'purple' }}
                >
                  {editingId ? 'Salvar Alterações' : 'Criar Colaborador'}
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>
      </Stack>
    </Shell>
  );
}

export default function ColaboradoresPage() {
  return (
    <ProtectedRoute>
      <ColaboradoresContent />
    </ProtectedRoute>
  );
}
