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
  Textarea,
  NumberInput,
  Select,
  ActionIcon,
  Card,
  Text,
  Paper,
  ThemeIcon,
  SimpleGrid,
  Box,
  ScrollArea
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { useForm } from '@mantine/form';
import { DateInput } from '@mantine/dates';
import { notifications } from '@mantine/notifications';
import { IconEdit, IconTrash, IconPlus, IconTrendingDown, IconReceipt, IconCheck } from '@tabler/icons-react';
import dayjs from 'dayjs';
import api from '@/lib/api';

interface Company {
  id: number;
  name: string;
}

interface Employee {
  id: number;
  name: string;
}

interface Expense {
  id: number;
  description: string;
  amount: number;
  date: string;
  due_date: string | null;
  category: string;
  recurrence: string;
  status: string;
  notes: string | null;
  company?: Company;
  employee?: Employee;
}

function DespesasContent() {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [companies, setCompanies] = useState<{value: string, label: string}[]>([]);
  const [employees, setEmployees] = useState<{value: string, label: string}[]>([]);
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const form = useForm({
    initialValues: {
      description: '',
      amount: 0,
      date: new Date(),
      due_date: null as Date | null,
      category: 'administrativo',
      recurrence: 'pontual',
      status: 'pendente',
      notes: '',
      company_id: null as string | null,
      employee_id: null as string | null,
    },
    validate: {
      description: (value) => (value.length < 3 ? 'Descrição muito curta' : null),
      amount: (value) => (value <= 0 ? 'Valor deve ser maior que zero' : null),
    },
  });

  useEffect(() => {
    loadExpenses();
    loadCompanies();
    loadEmployees();
  }, []);

  const loadExpenses = async () => {
    try {
      const response = await api.get('/expenses');
      setExpenses(response.data);
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao carregar despesas',
        color: 'red',
      });
    }
  };

  const loadCompanies = async () => {
    try {
      const response = await api.get('/companies');
      setCompanies(response.data.map((c: Company) => ({ value: String(c.id), label: c.name })));
    } catch (error) {
      console.error('Erro ao carregar empresas:', error);
    }
  };

  const loadEmployees = async () => {
    try {
      const response = await api.get('/employees');
      setEmployees(response.data.map((e: Employee) => ({ value: String(e.id), label: e.name })));
    } catch (error) {
      console.error('Erro ao carregar funcionários:', error);
    }
  };

  const handleSubmit = async (values: typeof form.values) => {
    setLoading(true);
    try {
      const payload = {
        ...values,
        date: values.date.toISOString(),
        due_date: values.due_date?.toISOString() || null,
        company_id: values.company_id ? parseInt(values.company_id) : null,
        employee_id: values.employee_id ? parseInt(values.employee_id) : null,
      };

      if (editingId) {
        await api.put(`/expenses/${editingId}`, payload);
        notifications.show({ title: 'Sucesso', message: 'Despesa atualizada', color: 'green' });
      } else {
        await api.post('/expenses', payload);
        notifications.show({ title: 'Sucesso', message: 'Despesa criada', color: 'green' });
      }
      setOpened(false);
      loadExpenses();
      form.reset();
      setEditingId(null);
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao salvar despesa',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (expense: Expense) => {
    setEditingId(expense.id);
    form.setValues({
      description: expense.description,
      amount: expense.amount,
      date: new Date(expense.date),
      due_date: expense.due_date ? new Date(expense.due_date) : null,
      category: expense.category,
      recurrence: expense.recurrence,
      status: expense.status,
      notes: expense.notes || '',
      company_id: expense.company?.id ? String(expense.company.id) : null,
      employee_id: expense.employee?.id ? String(expense.employee.id) : null,
    });
    setOpened(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Deseja realmente excluir esta despesa?')) return;
    
    try {
      await api.delete(`/expenses/${id}`);
      notifications.show({ title: 'Sucesso', message: 'Despesa excluída', color: 'green' });
      loadExpenses();
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao excluir despesa',
        color: 'red',
      });
    }
  };

  const handleMarkPaid = async (expense: Expense) => {
    try {
      await api.patch(`/expenses/${expense.id}/pay`);
      notifications.show({ title: 'Sucesso', message: 'Despesa marcada como paga', color: 'green' });
      loadExpenses();
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao marcar despesa como paga',
        color: 'red',
      });
    }
  };

  // Calcular totais
  const totalExpenses = expenses.reduce((sum, e) => sum + e.amount, 0);
  const pendingExpenses = expenses.filter(e => e.status === 'pendente').reduce((sum, e) => sum + e.amount, 0);
  const paidExpenses = expenses.filter(e => e.status === 'pago').reduce((sum, e) => sum + e.amount, 0);

  const categoryLabels: Record<string, string> = {
    administrativo: 'Administrativo',
    operacional: 'Operacional',
    impostos: 'Impostos',
    vale: 'Vale',
    adiantamento: 'Adiantamento',
    salario: 'Salário',
    beneficio: 'Benefício',
    outros: 'Outros',
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={2}>Despesas</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={() => {
          setEditingId(null);
          form.reset();
          setOpened(true);
        }}>
          Nova Despesa
        </Button>
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <Paper p="md" radius="md" withBorder>
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Total Despesas</Text>
            <ThemeIcon color="blue" variant="light" radius="md">
              <IconTrendingDown size="1.2rem" />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="md">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalExpenses)}
          </Text>
        </Paper>

        <Paper p="md" radius="md" withBorder>
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Pendente</Text>
            <ThemeIcon color="yellow" variant="light" radius="md">
              <IconReceipt size="1.2rem" />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="md" c="yellow.7">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(pendingExpenses)}
          </Text>
        </Paper>

        <Paper p="md" radius="md" withBorder>
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Pago</Text>
            <ThemeIcon color="green" variant="light" radius="md">
              <IconCheck size="1.2rem" />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="md" c="green">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(paidExpenses)}
          </Text>
        </Paper>
      </SimpleGrid>

      <Card withBorder radius="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Data</Table.Th>
              <Table.Th>Descrição</Table.Th>
              <Table.Th>Categoria</Table.Th>
              <Table.Th>Empresa</Table.Th>
              <Table.Th>Funcionário</Table.Th>
              <Table.Th ta="right">Valor</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Ações</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {expenses.map((expense) => (
              <Table.Tr key={expense.id}>
                <Table.Td>{dayjs(expense.date).format('DD/MM/YYYY')}</Table.Td>
                <Table.Td>
                  <Text size="sm" fw={500}>{expense.description}</Text>
                  <Text size="xs" c="dimmed">{expense.recurrence === 'mensal' ? 'Recorrente Mensal' : 'Pontual'}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="light">{categoryLabels[expense.category] || expense.category}</Badge>
                </Table.Td>
                <Table.Td>{expense.company?.name || '-'}</Table.Td>
                <Table.Td>{expense.employee?.name || '-'}</Table.Td>
                <Table.Td ta="right" fw={500}>
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(expense.amount)}
                </Table.Td>
                <Table.Td>
                  <Badge color={expense.status === 'pago' ? 'green' : 'yellow'}>
                    {expense.status === 'pago' ? 'Pago' : 'Pendente'}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap={0}>
                    {expense.status === 'pendente' && (
                      <ActionIcon variant="subtle" color="green" onClick={() => handleMarkPaid(expense)} title="Marcar como pago">
                        <IconCheck size={16} />
                      </ActionIcon>
                    )}
                    <ActionIcon variant="subtle" color="blue" onClick={() => handleEdit(expense)}>
                      <IconEdit size={16} />
                    </ActionIcon>
                    <ActionIcon variant="subtle" color="red" onClick={() => handleDelete(expense.id)}>
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {expenses.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={8}>
                  <Text ta="center" c="dimmed" py="md">
                    Nenhuma despesa cadastrada
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title={editingId ? "Editar Despesa" : "Nova Despesa"} size="lg">
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            <TextInput
              label="Descrição"
              placeholder="Ex: Aluguel, Material de Escritório"
              required
              {...form.getInputProps('description')}
            />
            
            <Group grow>
              <NumberInput
                label="Valor"
                placeholder="0,00"
                required
                decimalScale={2}
                fixedDecimalScale
                prefix="R$ "
                {...form.getInputProps('amount')}
              />

              <Select
                label="Categoria"
                data={[
                  { value: 'administrativo', label: 'Administrativo' },
                  { value: 'operacional', label: 'Operacional' },
                  { value: 'impostos', label: 'Impostos' },
                  { value: 'vale', label: 'Vale (Funcionário)' },
                  { value: 'adiantamento', label: 'Adiantamento (Funcionário)' },
                  { value: 'salario', label: 'Salário' },
                  { value: 'beneficio', label: 'Benefício' },
                  { value: 'outros', label: 'Outros' },
                ]}
                required
                {...form.getInputProps('category')}
              />
            </Group>

            <Group grow>
              <DateInput
                label="Data"
                placeholder="DD/MM/AAAA"
                required
                valueFormat="DD/MM/YYYY"
                {...form.getInputProps('date')}
              />

              <DateInput
                label="Vencimento"
                placeholder="DD/MM/AAAA"
                valueFormat="DD/MM/YYYY"
                clearable
                {...form.getInputProps('due_date')}
              />
            </Group>

            <Group grow>
              <Select
                label="Empresa"
                data={companies}
                placeholder="Associar a uma empresa"
                clearable
                searchable
                {...form.getInputProps('company_id')}
              />

              <Select
                label="Funcionário"
                data={employees}
                placeholder="Associar a um funcionário"
                clearable
                searchable
                {...form.getInputProps('employee_id')}
              />
            </Group>

            <Group grow>
              <Select
                label="Recorrência"
                data={[
                  { value: 'pontual', label: 'Pontual' },
                  { value: 'mensal', label: 'Mensal' },
                ]}
                required
                {...form.getInputProps('recurrence')}
              />

              <Select
                label="Status"
                data={[
                  { value: 'pendente', label: 'Pendente' },
                  { value: 'pago', label: 'Pago' },
                ]}
                required
                {...form.getInputProps('status')}
              />
            </Group>

            <Textarea
              label="Observações"
              placeholder="Observações adicionais"
              rows={2}
              {...form.getInputProps('notes')}
            />

            <Button type="submit" loading={loading}>
              Salvar
            </Button>
          </Stack>
        </form>
      </Modal>
    </Stack>
  );
}

export default function DespesasPage() {
  return (
    <ProtectedRoute>
      <Shell>
        <DespesasContent />
      </Shell>
    </ProtectedRoute>
  );
}
