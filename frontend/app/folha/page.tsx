'use client';

import { useEffect, useState } from 'react';
import {
  Stack,
  Title,
  Card,
  Table,
  Badge,
  Group,
  Text,
  Button,
  Select,
  Paper,
  ThemeIcon,
  SimpleGrid,
  Modal,
  NumberInput,
  TextInput,
  ActionIcon,
  Tooltip,
  Progress,
  Divider,
  Box,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { DateInput } from '@mantine/dates';
import { notifications } from '@mantine/notifications';
import {
  IconCash,
  IconPlus,
  IconCheck,
  IconCoin,
  IconReceipt,
  IconUser,
  IconCalendar,
  IconSignature,
} from '@tabler/icons-react';
import dayjs from 'dayjs';
import { Shell } from '@/components/Shell';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import api from '@/lib/api';

interface Employee {
  id: number;
  name: string;
  role_name: string;
  regime: string;
  base_salary: number | null;
  company_id: number | null;
}

interface Rubric {
  id: number;
  name: string;
  type: string;
  category: string;
  default_value: number | null;
  entra_clt: boolean;
  entra_calculo_percentual: boolean;
  recurring: boolean;
}

interface CompetencyItem {
  id: number;
  rubric_id: number;
  value: number;
  rubric?: Rubric;
}

interface Payment {
  id: number;
  date: string;
  amount: number;
  kind: string;
  method: string;
  status: string;
  notes: string | null;
  signature_id?: string;
  signature_status?: string;
  signature_url?: string;
  signed_at?: string;
}

interface Competency {
  id: number;
  employee_id: number;
  year: number;
  month: number;
  status: string;
  items: CompetencyItem[];
  payments: Payment[];
  totals_json: {
    total_proventos: number;
    total_descontos: number;
    total_geral: number;
    total_pago: number;
    saldo: number;
  } | null;
}

function FolhaContent() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [selectedEmployee, setSelectedEmployee] = useState<string | null>(null);
  const [competency, setCompetency] = useState<Competency | null>(null);
  const [loading, setLoading] = useState(false);
  const [paymentModalOpened, setPaymentModalOpened] = useState(false);
  const [itemModalOpened, setItemModalOpened] = useState(false);
  const [generatingReceipt, setGeneratingReceipt] = useState<number | null>(null);
  const [paymentAmount, setPaymentAmount] = useState<number | string>(0);
  const [paymentDate, setPaymentDate] = useState<Date | null>(new Date());

  // Mês e ano atual
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);

  const paymentForm = useForm({
    initialValues: {
      kind: 'salario',
      method: 'pix',
      notes: '',
    },
  });

  const itemForm = useForm({
    initialValues: {
      rubric_id: '',
      value: 0,
    },
  });

  // Abrir modal de pagamento com valor do saldo
  const openPaymentModal = () => {
    const currentTotals = calculateTotals();
    setPaymentAmount(currentTotals.saldo > 0 ? currentTotals.saldo : 0);
    setPaymentDate(new Date());
    paymentForm.reset();
    setPaymentModalOpened(true);
  };

  // Função para gerar recibo de um pagamento
  const handleGenerateReceipt = async (paymentId: number) => {
    setGeneratingReceipt(paymentId);
    try {
      const response = await api.post(`/payments/${paymentId}/generate-receipt`);
      
      // Se tem link de assinatura, mostrar opção de copiar
      if (response.data.sign_url) {
        notifications.show({
          title: '✅ Recibo Gerado com Link de Assinatura!',
          message: (
            <Stack gap="xs">
              <Text size="sm">Enviado para: {response.data.employee_email}</Text>
              <Group gap="xs">
                <Button 
                  size="xs" 
                  variant="light"
                  onClick={() => {
                    navigator.clipboard.writeText(response.data.sign_url);
                    notifications.show({
                      title: 'Link Copiado!',
                      message: 'Link de assinatura copiado para a área de transferência',
                      color: 'green',
                    });
                  }}
                >
                  📋 Copiar Link
                </Button>
                <Button 
                  size="xs" 
                  variant="light"
                  color="blue"
                  onClick={() => window.open(response.data.sign_url, '_blank')}
                >
                  🔗 Abrir Link
                </Button>
              </Group>
            </Stack>
          ),
          color: 'green',
          autoClose: false,
        });
      } else {
        notifications.show({
          title: 'Recibo Gerado!',
          message: `Recibo enviado para assinatura do colaborador (${response.data.employee_email})`,
          color: 'green',
          autoClose: 5000,
        });
      }
      
      // Abrir PDF em nova aba
      if (response.data.download_url) {
        window.open(response.data.download_url, '_blank');
      } else if (response.data.signature_id) {
        const downloadResponse = await api.get(`/signatures/${response.data.signature_id}/download`);
        if (downloadResponse.data.download_url) {
          window.open(downloadResponse.data.download_url, '_blank');
        }
      }
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao gerar recibo',
        color: 'red',
      });
    } finally {
      setGeneratingReceipt(null);
    }
  };

  useEffect(() => {
    loadEmployees();
    loadRubrics();
  }, []);

  useEffect(() => {
    if (selectedEmployee) {
      loadCompetency();
    }
  }, [selectedEmployee, year, month]);

  const loadEmployees = async () => {
    try {
      const response = await api.get('/employees');
      setEmployees(response.data);
    } catch (error) {
      console.error('Erro ao carregar funcionários:', error);
    }
  };

  const loadRubrics = async () => {
    try {
      const response = await api.get('/rubrics');
      setRubrics(response.data);
    } catch (error) {
      console.error('Erro ao carregar rubricas:', error);
    }
  };

  const loadCompetency = async () => {
    if (!selectedEmployee) return;
    setLoading(true);
    try {
      // Tentar buscar competência existente
      const response = await api.get(`/competencies/employee/${selectedEmployee}`, {
        params: { year, month }
      });
      setCompetency(response.data);
    } catch (error: any) {
      if (error.response?.status === 404) {
        // Criar nova competência
        try {
          const createResponse = await api.post('/competencies', {
            employee_id: parseInt(selectedEmployee),
            year,
            month,
          });
          setCompetency(createResponse.data);
        } catch (createError) {
          console.error('Erro ao criar competência:', createError);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAddPayment = async () => {
    if (!competency) return;
    
    const amount = typeof paymentAmount === 'string' ? parseFloat(paymentAmount) || 0 : paymentAmount;
    const values = paymentForm.values;
    
    if (amount <= 0) {
      notifications.show({
        title: 'Atenção',
        message: 'Informe um valor maior que zero',
        color: 'yellow',
      });
      return;
    }
    
    // Validar se vale está dentro do limite de 40%
    if (values.kind === 'vale') {
      const currentTotals = calculateTotals();
      const newValePago = currentTotals.valePago + amount;
      
      if (newValePago > currentTotals.maxVale) {
        const excedente = newValePago - currentTotals.maxVale;
        notifications.show({
          title: 'Atenção: Limite de Vale Excedido!',
          message: `Este vale excede o limite em ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(excedente)}. Máximo disponível: ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(currentTotals.valeDisponivel)}`,
          color: 'orange',
          autoClose: 5000,
        });
      }
    }
    
    try {
      await api.post(`/competencies/${competency.id}/payments`, {
        ...values,
        amount: amount,
        date: paymentDate?.toISOString() || new Date().toISOString(),
        status: 'pago',
      });
      notifications.show({
        title: 'Sucesso',
        message: 'Pagamento registrado!',
        color: 'green',
      });
      paymentForm.reset();
      setPaymentAmount(0);
      setPaymentModalOpened(false);
      loadCompetency();
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao registrar pagamento',
        color: 'red',
      });
    }
  };

  const handleAddItem = async (values: typeof itemForm.values) => {
    if (!competency) return;
    try {
      await api.post(`/competencies/${competency.id}/items`, {
        rubric_id: parseInt(values.rubric_id),
        value: values.value,
      });
      notifications.show({
        title: 'Sucesso',
        message: 'Item adicionado!',
        color: 'green',
      });
      itemForm.reset();
      setItemModalOpened(false);
      loadCompetency();
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao adicionar item',
        color: 'red',
      });
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!competency) return;
    try {
      await api.delete(`/competencies/${competency.id}/items/${itemId}`);
      loadCompetency();
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao remover item',
        color: 'red',
      });
    }
  };

  // Calcular totais
  const calculateTotals = () => {
    if (!competency) return { proventos: 0, descontos: 0, total: 0, pago: 0, saldo: 0, baseVale: 0, maxVale: 0, valePago: 0, valeDisponivel: 0 };

    let proventos = 0;
    let descontos = 0;
    let baseVale = 0; // Apenas itens que entram no cálculo de vale

    competency.items.forEach(item => {
      const rubric = rubrics.find(r => r.id === item.rubric_id);
      if (!rubric) return;

      if (rubric.type === 'provento') {
        proventos += item.value;
        // Soma na base de vale apenas se entra_calculo_percentual for true
        if (rubric.entra_calculo_percentual) {
          baseVale += item.value;
        }
      } else {
        descontos += item.value;
      }
    });

    const total = proventos - descontos;
    const maxVale = baseVale * 0.4; // 40% da base de vale
    
    // Total pago: exclui pagamentos kind="desconto" pois descontos já estão no total líquido
    const pago = competency.payments
      .filter(p => p.status === 'pago' && p.kind !== 'desconto')
      .reduce((sum, p) => sum + p.amount, 0);
    const saldo = total - pago;
    
    // Vale já sacado (pagamentos do tipo "vale")
    const valePago = competency.payments
      .filter(p => p.status === 'pago' && p.kind === 'vale')
      .reduce((sum, p) => sum + p.amount, 0);
    
    // Vale disponível (considerando todo o valor já pago contra o limite de 40%)
    // Se já recebeu mais que 40% do salário (seja como vale ou salário), não tem mais margem
    const valeDisponivel = maxVale - pago;

    return { proventos, descontos, total, pago, saldo, baseVale, maxVale, valePago, valeDisponivel };
  };

  const totals = calculateTotals();
  const percentPago = totals.total > 0 ? (totals.pago / totals.total) * 100 : 0;

  const months = [
    { value: '1', label: 'Janeiro' },
    { value: '2', label: 'Fevereiro' },
    { value: '3', label: 'Março' },
    { value: '4', label: 'Abril' },
    { value: '5', label: 'Maio' },
    { value: '6', label: 'Junho' },
    { value: '7', label: 'Julho' },
    { value: '8', label: 'Agosto' },
    { value: '9', label: 'Setembro' },
    { value: '10', label: 'Outubro' },
    { value: '11', label: 'Novembro' },
    { value: '12', label: 'Dezembro' },
  ];

  const years = Array.from({ length: 5 }, (_, i) => {
    const y = new Date().getFullYear() - 2 + i;
    return { value: String(y), label: String(y) };
  });

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>Folha de Pagamento</Title>
      </Group>

      {/* Seletores */}
      <Card withBorder p="md">
        <Group>
          <Select
            label="Funcionário"
            placeholder="Selecione um funcionário"
            data={employees.map(e => ({ value: String(e.id), label: `${e.name} - ${e.role_name}` }))}
            value={selectedEmployee}
            onChange={setSelectedEmployee}
            searchable
            w={300}
          />
          <Select
            label="Mês"
            data={months}
            value={String(month)}
            onChange={(v) => setMonth(parseInt(v || '1'))}
            w={150}
          />
          <Select
            label="Ano"
            data={years}
            value={String(year)}
            onChange={(v) => setYear(parseInt(v || String(new Date().getFullYear())))}
            w={100}
          />
        </Group>
      </Card>

      {selectedEmployee && competency && (
        <>
          {/* Cards de Resumo */}
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 6 }}>
            <Paper p="md" radius="md" withBorder>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">Total Proventos</Text>
                <ThemeIcon color="green" variant="light" radius="md">
                  <IconCoin size="1.2rem" />
                </ThemeIcon>
              </Group>
              <Text fw={700} size="xl" mt="md">
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.proventos)}
              </Text>
            </Paper>

            <Paper p="md" radius="md" withBorder>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">Base p/ Vale</Text>
                <ThemeIcon color="violet" variant="light" radius="md">
                  <IconReceipt size="1.2rem" />
                </ThemeIcon>
              </Group>
              <Text fw={700} size="xl" mt="md">
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.baseVale)}
              </Text>
              <Text size="xs" c="dimmed">
                Máx. 40%: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.maxVale)}
              </Text>
            </Paper>

            <Paper p="md" radius="md" withBorder style={{ borderColor: totals.valeDisponivel < 0 ? 'var(--mantine-color-red-4)' : totals.valeDisponivel > 0 ? 'var(--mantine-color-cyan-4)' : undefined }}>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">Vale Disponível</Text>
                <ThemeIcon color={totals.valeDisponivel < 0 ? 'red' : 'cyan'} variant="light" radius="md">
                  <IconCash size="1.2rem" />
                </ThemeIcon>
              </Group>
              <Text fw={700} size="xl" mt="md" c={totals.valeDisponivel < 0 ? 'red' : totals.valeDisponivel > 0 ? 'cyan' : 'gray'}>
                {totals.valeDisponivel < 0 
                  ? `Ultrapassado em ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Math.abs(totals.valeDisponivel))}`
                  : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.valeDisponivel)
                }
              </Text>
              <Text size="xs" c="dimmed">
                {totals.valeDisponivel < 0 
                  ? `Total Pago: ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.pago)}`
                  : `Sacado: ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.valePago)}`
                }
              </Text>
            </Paper>

            <Paper p="md" radius="md" withBorder>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">Já Pago</Text>
                <ThemeIcon color="blue" variant="light" radius="md">
                  <IconCheck size="1.2rem" />
                </ThemeIcon>
              </Group>
              <Text fw={700} size="xl" mt="md">
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.pago)}
              </Text>
            </Paper>

            <Paper p="md" radius="md" withBorder>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">Saldo a Pagar</Text>
                <ThemeIcon color={totals.saldo > 0 ? 'orange' : 'green'} variant="light" radius="md">
                  <IconCash size="1.2rem" />
                </ThemeIcon>
              </Group>
              <Text fw={700} size="xl" mt="md" c={totals.saldo > 0 ? 'orange' : 'green'}>
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.saldo)}
              </Text>
            </Paper>

            <Paper p="md" radius="md" withBorder>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">Total Líquido</Text>
                <ThemeIcon color="teal" variant="light" radius="md">
                  <IconCash size="1.2rem" />
                </ThemeIcon>
              </Group>
              <Text fw={700} size="xl" mt="md" c="teal">
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.total)}
              </Text>
            </Paper>
          </SimpleGrid>

          {/* Barras de Progresso */}
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            <Card withBorder p="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" fw={500}>Progresso do Pagamento Total</Text>
                <Text size="sm" c="dimmed">{percentPago.toFixed(0)}% pago</Text>
              </Group>
              <Progress value={percentPago} size="lg" radius="md" color={percentPago >= 100 ? 'green' : 'blue'} />
            </Card>
            
            <Card withBorder p="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" fw={500}>Vale Sacado (máx. 40%)</Text>
                <Text size="sm" c="dimmed">
                  {totals.maxVale > 0 ? ((totals.valePago / totals.maxVale) * 100).toFixed(0) : 0}% do limite
                </Text>
              </Group>
              <Progress 
                value={totals.maxVale > 0 ? (totals.valePago / totals.maxVale) * 100 : 0} 
                size="lg" 
                radius="md" 
                color={totals.valePago >= totals.maxVale ? 'red' : 'cyan'} 
              />
              <Text size="xs" c="dimmed" mt="xs">
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.valePago)} de {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.maxVale)}
              </Text>
            </Card>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, md: 2 }}>
            {/* Composição do Salário */}
            <Card withBorder>
              <Group justify="space-between" mb="md">
                <Text fw={600}>Composição do Salário</Text>
                <Button size="xs" leftSection={<IconPlus size={14} />} onClick={() => setItemModalOpened(true)}>
                  Adicionar
                </Button>
              </Group>
              <Table striped>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Descrição</Table.Th>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Base Vale</Table.Th>
                    <Table.Th ta="right">Valor</Table.Th>
                    <Table.Th></Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {competency.items.map((item) => {
                    const rubric = rubrics.find(r => r.id === item.rubric_id);
                    return (
                      <Table.Tr key={item.id}>
                        <Table.Td>
                          <Text size="sm" fw={500}>{rubric?.name || 'Rubrica'}</Text>
                          <Text size="xs" c="dimmed">{rubric?.category === 'folha' ? 'Folha' : rubric?.category === 'beneficio' ? 'Benefício' : 'Reembolso'}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge color={rubric?.type === 'provento' ? 'green' : 'red'} size="sm">
                            {rubric?.type === 'provento' ? 'Provento' : 'Desconto'}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Badge color={rubric?.entra_calculo_percentual ? 'violet' : 'gray'} size="xs" variant="light">
                            {rubric?.entra_calculo_percentual ? 'Sim' : 'Não'}
                          </Badge>
                        </Table.Td>
                        <Table.Td ta="right" fw={500} c={rubric?.type === 'provento' ? 'green' : 'red'}>
                          {rubric?.type === 'desconto' ? '- ' : ''}
                          {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.value)}
                        </Table.Td>
                        <Table.Td>
                          <ActionIcon 
                            variant="subtle" 
                            color="red" 
                            size="sm"
                            onClick={() => handleDeleteItem(item.id)}
                          >
                            ×
                          </ActionIcon>
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                  {competency.items.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={5}>
                        <Text ta="center" c="dimmed" size="sm">
                          Nenhum item cadastrado. Adicione salário base, benefícios, etc.
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
                <Table.Tfoot>
                  <Table.Tr>
                    <Table.Td colSpan={3}><Text fw={700}>TOTAL LÍQUIDO</Text></Table.Td>
                    <Table.Td ta="right">
                      <Text fw={700} size="lg">
                        {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.total)}
                      </Text>
                    </Table.Td>
                    <Table.Td></Table.Td>
                  </Table.Tr>
                </Table.Tfoot>
              </Table>
            </Card>

            {/* Pagamentos do Mês */}
            <Card withBorder>
              <Group justify="space-between" mb="md">
                <Text fw={600}>Pagamentos do Mês</Text>
                <Button 
                  size="xs" 
                  leftSection={<IconCash size={14} />} 
                  onClick={openPaymentModal}
                  color="green"
                >
                  Registrar Pagamento
                </Button>
              </Group>
              <Table striped>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Data</Table.Th>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Método</Table.Th>
                    <Table.Th ta="right">Valor</Table.Th>
                    <Table.Th>Assinatura</Table.Th>
                    <Table.Th ta="center">Ações</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {competency.payments.map((payment) => (
                    <Table.Tr key={payment.id}>
                      <Table.Td>{dayjs(payment.date).format('DD/MM')}</Table.Td>
                      <Table.Td>
                        <Badge variant="light">
                          {payment.kind === 'vale' ? 'Vale' :
                           payment.kind === 'adiantamento' ? 'Adiantamento' :
                           payment.kind === 'salario' ? 'Salário' :
                           payment.kind === 'beneficio' ? 'Benefício' : 'Outros'}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm" tt="uppercase">{payment.method}</Text>
                      </Table.Td>
                      <Table.Td ta="right" fw={500}>
                        {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(payment.amount)}
                      </Table.Td>
                      <Table.Td>
                        {payment.signature_status ? (
                          <Group gap="xs">
                            <Badge 
                              size="xs"
                              color={
                                payment.signature_status === 'completed' ? 'green' :
                                payment.signature_status === 'sent' ? 'blue' :
                                'gray'
                              }
                            >
                              {payment.signature_status === 'completed' ? '✓ Assinado' :
                               payment.signature_status === 'sent' ? 'Enviado' :
                               'Pendente'}
                            </Badge>
                          </Group>
                        ) : (
                          <Text size="xs" c="dimmed">-</Text>
                        )}
                      </Table.Td>
                      <Table.Td ta="center">
                        <Group gap="xs" justify="center">
                          {payment.signature_url && (
                            <Tooltip label="Abrir Link de Assinatura">
                              <ActionIcon
                                variant="light"
                                color="purple"
                                size="sm"
                                component="a"
                                href={payment.signature_url}
                                target="_blank"
                              >
                                <IconReceipt size={16} />
                              </ActionIcon>
                            </Tooltip>
                          )}
                          {!payment.signature_id && (
                            <Tooltip label="Gerar Recibo para Assinatura">
                              <ActionIcon
                                variant="light"
                                color="blue"
                                size="sm"
                                loading={generatingReceipt === payment.id}
                                onClick={() => handleGenerateReceipt(payment.id)}
                              >
                                <IconSignature size={16} />
                              </ActionIcon>
                            </Tooltip>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                  {competency.payments.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={5}>
                        <Text ta="center" c="dimmed" size="sm">
                          Nenhum pagamento registrado este mês
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
                <Table.Tfoot>
                  <Table.Tr>
                    <Table.Td colSpan={4}><Text fw={700}>TOTAL PAGO</Text></Table.Td>
                    <Table.Td ta="right">
                      <Text fw={700} size="lg" c="green">
                        {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.pago)}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                </Table.Tfoot>
              </Table>
            </Card>
          </SimpleGrid>
        </>
      )}

      {!selectedEmployee && (
        <Card withBorder p="xl">
          <Stack align="center" gap="md">
            <ThemeIcon size={60} radius="xl" variant="light">
              <IconUser size={30} />
            </ThemeIcon>
            <Text size="lg" fw={500}>Selecione um Funcionário</Text>
            <Text c="dimmed" ta="center">
              Escolha um funcionário para visualizar e gerenciar a folha de pagamento mensal
            </Text>
          </Stack>
        </Card>
      )}

      {/* Modal Adicionar Item */}
      <Modal opened={itemModalOpened} onClose={() => setItemModalOpened(false)} title="Adicionar Item ao Salário">
        <form onSubmit={itemForm.onSubmit(handleAddItem)}>
          <Stack>
            <Select
              label="Rubrica"
              placeholder="Selecione"
              data={rubrics.map(r => ({ 
                value: String(r.id), 
                label: `${r.name} (${r.type === 'provento' ? '+' : '-'})` 
              }))}
              required
              {...itemForm.getInputProps('rubric_id')}
            />
            <NumberInput
              label="Valor"
              placeholder="0,00"
              required
              decimalScale={2}
              fixedDecimalScale
              prefix="R$ "
              {...itemForm.getInputProps('value')}
            />
            <Button type="submit">Adicionar</Button>
          </Stack>
        </form>
      </Modal>

      {/* Modal Registrar Pagamento */}
      <Modal opened={paymentModalOpened} onClose={() => setPaymentModalOpened(false)} title="Registrar Pagamento" size="md">
        <Stack>
          <Paper p="sm" bg="blue.0" radius="md">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Saldo a pagar:</Text>
              <Text size="lg" fw={700} c={totals.saldo > 0 ? 'blue' : 'green'}>
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totals.saldo)}
              </Text>
            </Group>
          </Paper>
          
          <NumberInput
            label="Valor do Pagamento"
            placeholder="0,00"
            required
            decimalScale={2}
            fixedDecimalScale
            prefix="R$ "
            value={paymentAmount}
            onChange={(val) => setPaymentAmount(val)}
            min={0}
          />
          
          <DateInput
            label="Data do Pagamento"
            placeholder="Selecione a data"
            value={paymentDate}
            onChange={setPaymentDate}
            valueFormat="DD/MM/YYYY"
          />
          
          <Select
            label="Tipo"
            data={[
              { value: 'salario', label: 'Salário' },
              { value: 'vale', label: 'Vale' },
              { value: 'adiantamento', label: 'Adiantamento' },
              { value: 'beneficio', label: 'Benefício' },
              { value: 'outros', label: 'Outros' },
            ]}
            required
            {...paymentForm.getInputProps('kind')}
          />
          
          <Select
            label="Método"
            data={[
              { value: 'pix', label: 'PIX' },
              { value: 'ted', label: 'TED' },
              { value: 'dinheiro', label: 'Dinheiro' },
              { value: 'cartao', label: 'Cartão' },
            ]}
            required
            {...paymentForm.getInputProps('method')}
          />
          
          <TextInput
            label="Descrição (opcional)"
            placeholder="Ex: Pagamento via PIX"
            {...paymentForm.getInputProps('notes')}
          />
          
          <Group justify="flex-end" mt="md">
            <Button variant="light" onClick={() => setPaymentModalOpened(false)}>Cancelar</Button>
            <Button color="green" leftSection={<IconCheck size={16} />} onClick={handleAddPayment}>
              Confirmar Pagamento
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

export default function FolhaPage() {
  return (
    <ProtectedRoute>
      <Shell>
        <FolhaContent />
      </Shell>
    </ProtectedRoute>
  );
}
