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
  Select,
  NumberInput,
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
import { IconEdit, IconTrash, IconReceipt, IconPlus, IconTrendingUp, IconTrendingDown } from '@tabler/icons-react';
import api from '@/lib/api';

const RUBRIC_TYPES = [
  { value: 'provento', label: 'Provento' },
  { value: 'desconto', label: 'Desconto' }
];

const CATEGORY_TYPES = [
  { value: 'folha', label: 'Folha de Pagamento' },
  { value: 'beneficio', label: 'Benefício' },
  { value: 'reembolso', label: 'Reembolso' }
];

const CALCULATION_TYPES = [
  { value: 'fixed', label: 'Fixo' },
  { value: 'percentage', label: 'Percentual' }
];

function RubricasContent() {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [rubrics, setRubrics] = useState<any[]>([]);
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const form = useForm({
    initialValues: {
      code: '',
      name: '',
      type: 'provento',
      category: 'folha',
      calculation_type: 'fixed',
      default_value: 0,
      entra_clt: true,
      entra_calculo_percentual: true,
      recurring: false,
      active: true,
    },
  });

  useEffect(() => {
    loadRubrics();
  }, []);

  const loadRubrics = async () => {
    try {
      const { data } = await api.get('/rubrics');
      setRubrics(data);
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao carregar rubricas',
        color: 'red',
      });
    }
  };

  const handleOpenCreate = () => {
    setEditingId(null);
    form.reset();
    setOpened(true);
  };

  const handleOpenEdit = (rubric: any) => {
    setEditingId(rubric.id);
    form.setValues({
      code: rubric.code,
      name: rubric.name,
      type: rubric.type,
      category: rubric.category || 'folha',
      calculation_type: rubric.calculation_type,
      default_value: Number(rubric.default_value) || 0,
      entra_clt: rubric.entra_clt ?? true,
      entra_calculo_percentual: rubric.entra_calculo_percentual ?? true,
      recurring: rubric.recurring ?? false,
      active: rubric.active,
    });
    setOpened(true);
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      if (editingId) {
        await api.put(`/rubrics/${editingId}`, values);
        notifications.show({
          title: 'Sucesso',
          message: 'Rubrica atualizada com sucesso!',
          color: 'green',
        });
      } else {
        await api.post('/rubrics', values);
        notifications.show({
          title: 'Sucesso',
          message: 'Rubrica criada com sucesso!',
          color: 'green',
        });
      }
      setOpened(false);
      form.reset();
      setEditingId(null);
      loadRubrics();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao salvar rubrica',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Deseja realmente excluir esta rubrica?')) return;
    
    try {
      await api.delete(`/rubrics/${id}`);
      notifications.show({
        title: 'Sucesso',
        message: 'Rubrica excluída com sucesso!',
        color: 'green',
      });
      loadRubrics();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao excluir rubrica',
        color: 'red',
      });
    }
  };

  const proventosCount = rubrics.filter(r => r.type === 'provento').length;
  const descontosCount = rubrics.filter(r => r.type === 'desconto').length;

  return (
    <Shell>
      <Stack gap="lg">
        {/* Header */}
        <Paper p="md" radius="md" withBorder>
          <Group justify="space-between" align="center">
            <div>
              <Title order={2}>Rubricas</Title>
              <Text c="dimmed" size="sm">Configure proventos e descontos para folha de pagamento</Text>
            </div>
            <Button 
              leftSection={<IconPlus size={16} />}
              variant="gradient"
              gradient={{ from: 'violet', to: 'purple' }}
              onClick={handleOpenCreate}
            >
              Nova Rubrica
            </Button>
          </Group>
        </Paper>

        {/* KPIs */}
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Text size="sm" c="dimmed">Total Rubricas</Text>
                <Text size="xl" fw={700}>{rubrics.length}</Text>
              </div>
              <ThemeIcon size={50} radius="md" variant="light" color="blue">
                <IconReceipt size={28} />
              </ThemeIcon>
            </Group>
          </Card>
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Text size="sm" c="dimmed">Proventos</Text>
                <Text size="xl" fw={700} c="green">{proventosCount}</Text>
              </div>
              <ThemeIcon size={50} radius="md" variant="light" color="green">
                <IconTrendingUp size={28} />
              </ThemeIcon>
            </Group>
          </Card>
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <div>
                <Text size="sm" c="dimmed">Descontos</Text>
                <Text size="xl" fw={700} c="red">{descontosCount}</Text>
              </div>
              <ThemeIcon size={50} radius="md" variant="light" color="red">
                <IconTrendingDown size={28} />
              </ThemeIcon>
            </Group>
          </Card>
        </SimpleGrid>

        {/* Tabela */}
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Código</Table.Th>
                <Table.Th>Nome</Table.Th>
                <Table.Th>Tipo</Table.Th>
                <Table.Th>Valor Padrão</Table.Th>
                <Table.Th>Base Vale</Table.Th>
                <Table.Th>Recorrente</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Ações</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rubrics.map((rubric) => (
                <Table.Tr key={rubric.id}>
                  <Table.Td>
                    <Badge variant="light">{rubric.code}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text fw={500}>{rubric.name}</Text>
                    <Text size="xs" c="dimmed">{rubric.category === 'folha' ? 'Folha' : rubric.category === 'beneficio' ? 'Benefício' : 'Reembolso'}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge 
                      variant="gradient"
                      gradient={rubric.type === 'provento' ? { from: 'green', to: 'teal' } : { from: 'red', to: 'pink' }}
                    >
                      {rubric.type === 'provento' ? 'Provento' : 'Desconto'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text fw={600}>
                      {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(rubric.default_value) || 0)}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={rubric.entra_calculo_percentual ? 'green' : 'gray'} variant="light">
                      {rubric.entra_calculo_percentual ? 'Sim' : 'Não'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={rubric.recurring ? 'blue' : 'gray'} variant="light">
                      {rubric.recurring ? 'Sim' : 'Não'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge 
                      variant="gradient"
                      gradient={rubric.active ? { from: 'green', to: 'teal' } : { from: 'gray', to: 'dark' }}
                    >
                      {rubric.active ? 'Ativo' : 'Inativo'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Tooltip label="Editar">
                        <ActionIcon 
                          color="blue" 
                          variant="light"
                          onClick={() => handleOpenEdit(rubric)}
                        >
                          <IconEdit size={16} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Excluir">
                        <ActionIcon 
                          color="red" 
                          variant="light"
                          onClick={() => handleDelete(rubric.id)}
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
          title={editingId ? 'Editar Rubrica' : 'Nova Rubrica'}
          size="md"
        >
          <form onSubmit={form.onSubmit(handleSubmit)}>
            <Stack>
              <TextInput
                label="Código"
                required
                placeholder="Ex: 001"
                {...form.getInputProps('code')}
              />
              <TextInput
                label="Nome"
                required
                placeholder="Ex: Salário Base"
                {...form.getInputProps('name')}
              />
              <Select
                label="Tipo"
                required
                data={RUBRIC_TYPES}
                {...form.getInputProps('type')}
              />
              <Select
                label="Categoria"
                required
                data={CATEGORY_TYPES}
                {...form.getInputProps('category')}
              />
              <Select
                label="Tipo de Cálculo"
                required
                data={CALCULATION_TYPES}
                {...form.getInputProps('calculation_type')}
              />
              <NumberInput
                label="Valor Padrão"
                required
                min={0}
                decimalScale={2}
                fixedDecimalScale
                prefix="R$ "
                {...form.getInputProps('default_value')}
              />
              <Switch
                label="Entra no cálculo de Vale (40%)"
                description="Marque se este valor deve ser considerado na base de cálculo do vale"
                checked={form.values.entra_calculo_percentual}
                onChange={(e) => form.setFieldValue('entra_calculo_percentual', e.currentTarget.checked)}
              />
              <Switch
                label="Entra na base CLT"
                description="Marque se este valor faz parte da remuneração CLT"
                checked={form.values.entra_clt}
                onChange={(e) => form.setFieldValue('entra_clt', e.currentTarget.checked)}
              />
              <Switch
                label="Recorrente"
                description="Marque se este valor se repete todo mês automaticamente"
                checked={form.values.recurring}
                onChange={(e) => form.setFieldValue('recurring', e.currentTarget.checked)}
              />
              {editingId && (
                <Switch
                  label="Rubrica Ativa"
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
                  {editingId ? 'Salvar Alterações' : 'Criar Rubrica'}
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>
      </Stack>
    </Shell>
  );
}

export default function RubricasPage() {
  return (
    <ProtectedRoute>
      <RubricasContent />
    </ProtectedRoute>
  );
}
