'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Shell } from '@/components/Shell';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { 
  Title, 
  Button, 
  Table,
  Badge,
  Stack,
  Group,
  Grid,
  Card,
  Text,
  Modal,
  NumberInput,
  ActionIcon,
  Tooltip,
  Select,
  Paper,
  ThemeIcon,
  Divider,
  SimpleGrid,
  TextInput,
  Tabs
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { 
  IconCheck, 
  IconTrash, 
  IconCash, 
  IconPlus,
  IconArrowLeft,
  IconReceipt,
  IconTrendingUp,
  IconTrendingDown,
  IconEdit,
  IconCoin,
  IconSignature,
  IconDownload
} from '@tabler/icons-react';
import api from '@/lib/api';
import { formatCurrency, MONTHS } from '@/lib/constants';

function CompetenciaDetailContent() {
  const params = useParams();
  const router = useRouter();
  const competencyId = params.id;
  
  const [competency, setCompetency] = useState<any>(null);
  const [employee, setEmployee] = useState<any>(null);
  const [items, setItems] = useState<any[]>([]);
  const [rubrics, setRubrics] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modais
  const [itemModalOpened, setItemModalOpened] = useState(false);
  const [paymentModalOpened, setPaymentModalOpened] = useState(false);
  const [editingItemId, setEditingItemId] = useState<number | null>(null);

  // Forms
  const itemForm = useForm({
    initialValues: {
      rubric_id: '',
      value: 0,
      description: '',
    },
    validate: {
      rubric_id: (value) => (!value ? 'Selecione uma rubrica' : null),
      value: (value) => (value <= 0 ? 'Valor deve ser maior que zero' : null),
    },
  });

  // Ao selecionar rubrica, preencher valor padrão
  const handleRubricChange = (rubricId: string) => {
    itemForm.setFieldValue('rubric_id', rubricId);
    const selectedRubric = rubrics.find(r => r.id === parseInt(rubricId));
    if (selectedRubric && selectedRubric.default_value) {
      itemForm.setFieldValue('value', Number(selectedRubric.default_value));
    }
  };

  const paymentForm = useForm({
    initialValues: {
      amount: 0,
      payment_date: new Date(),
      description: '',
    },
  });

  useEffect(() => {
    loadAll();
  }, [competencyId]);

  const loadAll = async () => {
    setLoading(true);
    await Promise.all([
      loadCompetency(),
      loadItems(),
      loadRubrics(),
      loadPayments()
    ]);
    setLoading(false);
  };

  const loadCompetency = async () => {
    try {
      const { data } = await api.get(`/competencies/${competencyId}`);
      setCompetency(data);
      
      // Carregar dados do colaborador
      try {
        const { data: emp } = await api.get(`/employees/${data.employee_id}`);
        setEmployee(emp);
      } catch {}
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao carregar competência',
        color: 'red',
      });
    }
  };

  const loadItems = async () => {
    try {
      const { data } = await api.get(`/competencies/${competencyId}/items`);
      setItems(data || []);
    } catch (error) {
      console.error('Erro ao carregar itens:', error);
      setItems([]);
    }
  };

  const loadRubrics = async () => {
    try {
      const { data } = await api.get('/rubrics');
      setRubrics(data.filter((r: any) => r.active));
    } catch (error) {
      console.error('Erro ao carregar rubricas:', error);
    }
  };

  const loadPayments = async () => {
    try {
      const { data } = await api.get(`/competencies/${competencyId}/payments`);
      setPayments(data || []);
    } catch (error) {
      console.error('Erro ao carregar pagamentos:', error);
      setPayments([]);
    }
  };

  // Handlers para Itens (Proventos/Descontos)
  const handleOpenAddItem = () => {
    setEditingItemId(null);
    itemForm.reset();
    setItemModalOpened(true);
  };

  const handleOpenEditItem = (item: any) => {
    setEditingItemId(item.id);
    itemForm.setValues({
      rubric_id: String(item.rubric_id),
      value: Number(item.value) || 0,
      description: item.notes || '',
    });
    setItemModalOpened(true);
  };

  const handleSubmitItem = async (values: any) => {
    try {
      const payload = {
        rubric_id: parseInt(values.rubric_id),
        value: values.value,
        notes: values.description,
      };

      if (editingItemId) {
        await api.put(`/competencies/${competencyId}/items/${editingItemId}`, payload);
        notifications.show({
          title: 'Sucesso',
          message: 'Item atualizado!',
          color: 'green',
        });
      } else {
        // Criar novo item (sem auto_generate_payment)
        await api.post(`/competencies/${competencyId}/items`, payload);
        
        notifications.show({
          title: 'Sucesso',
          message: 'Item adicionado!',
          color: 'green',
        });
      }

      setItemModalOpened(false);
      itemForm.reset();
      setEditingItemId(null);
      loadItems();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao salvar item',
        color: 'red',
      });
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!confirm('Deseja remover este item?')) return;
    
    try {
      await api.delete(`/competencies/${competencyId}/items/${itemId}`);
      notifications.show({
        title: 'Sucesso',
        message: 'Item removido!',
        color: 'green',
      });
      loadItems();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao remover item',
        color: 'red',
      });
    }
  };

  // Handlers para Pagamentos
  const handleOpenAddPayment = () => {
    paymentForm.setValues({
      amount: totals.saldo,
      payment_date: new Date(),
      description: '',
    });
    setPaymentModalOpened(true);
  };

  const handleSubmitPayment = async (values: any) => {
    try {
      await api.post(`/competencies/${competencyId}/payments`, {
        amount: values.amount,
        date: values.payment_date.toISOString(),
        kind: 'salario',
        method: 'pix',
        description: values.description
      });

      notifications.show({
        title: 'Sucesso',
        message: 'Pagamento registrado!',
        color: 'green',
      });

      setPaymentModalOpened(false);
      paymentForm.reset();
      loadPayments();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao registrar pagamento',
        color: 'red',
      });
    }
  };

  const handleDeletePayment = async (paymentId: number) => {
    if (!confirm('Deseja remover este pagamento?')) return;
    
    try {
      await api.delete(`/competencies/${competencyId}/payments/${paymentId}`);
      notifications.show({
        title: 'Sucesso',
        message: 'Pagamento removido!',
        color: 'green',
      });
      loadPayments();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao remover pagamento',
        color: 'red',
      });
    }
  };

  const handleGenerateReceipt = async (paymentId: number) => {
    try {
      notifications.show({
        id: 'generating-receipt',
        title: 'Gerando Recibo',
        message: 'Aguarde enquanto o recibo é gerado...',
        loading: true,
        autoClose: false,
      });
      
      const response = await api.post(`/payments/${paymentId}/generate-receipt`);
      
      console.log('📄 Resposta do generate-receipt:', response.data);
      
      // Recarregar pagamentos para atualizar o estado
      await loadPayments();
      
      // Se tem link de assinatura, mostrar opção de copiar
      if (response.data.sign_url) {
        notifications.update({
          id: 'generating-receipt',
          title: '✅ Recibo Gerado com Link de Assinatura!',
          message: (
            <Stack gap="xs">
              <Text size="sm">Enviado para: {response.data.employee_email}</Text>
              <Text size="xs" c="dimmed">Status: {response.data.status}</Text>
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
          loading: false,
          autoClose: false,
        });
      } else if (response.data.error_message) {
        // Mostrar erro específico do Documenso
        notifications.update({
          id: 'generating-receipt',
          title: '⚠️ Recibo Salvo Localmente',
          message: (
            <Stack gap="xs">
              <Text size="sm" c="orange">{response.data.error_message}</Text>
              <Text size="xs" c="dimmed">
                O recibo foi gerado e salvo, mas não foi possível enviar para assinatura eletrônica.
              </Text>
              <Text size="xs" c="dimmed">
                Você pode baixar o PDF usando o botão verde na lista de pagamentos.
              </Text>
            </Stack>
          ),
          color: 'orange',
          loading: false,
          autoClose: 10000,
        });
      } else {
        notifications.update({
          id: 'generating-receipt',
          title: 'Recibo Gerado!',
          message: `Recibo salvo (${response.data.status}). Enviado para: ${response.data.employee_email}`,
          color: response.data.status === 'pending_local' ? 'yellow' : 'green',
          loading: false,
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
      console.error('❌ Erro ao gerar recibo:', error);
      notifications.update({
        id: 'generating-receipt',
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao gerar recibo',
        color: 'red',
        loading: false,
        autoClose: 5000,
      });
    }
  };

  const handleDownloadReceipt = async (signatureId: string) => {
    try {
      const response = await api.get(`/signatures/${signatureId}/download`);
      if (response.data.download_url) {
        window.open(response.data.download_url, '_blank');
      }
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao baixar recibo',
        color: 'red',
      });
    }
  };

  // Calcular totais
  const totals = items.reduce((acc, item) => {
    const rubric = rubrics.find(r => r.id === item.rubric_id);
    const value = Number(item.value) || 0;
    
    if (rubric?.type === 'provento') {
      acc.proventos += value;
    } else {
      acc.descontos += value;
    }
    return acc;
  }, { proventos: 0, descontos: 0 });

  totals.liquido = totals.proventos - totals.descontos;
  
  // Total pago: exclui pagamentos kind="desconto" pois descontos já estão no líquido
  const totalPago = payments
    .filter(p => p.kind !== 'desconto')
    .reduce((sum, p) => sum + (Number(p.amount) || 0), 0);
  totals.saldo = totals.liquido - totalPago;

  if (loading) {
    return (
      <Shell>
        <Text>Carregando...</Text>
      </Shell>
    );
  }

  const monthName = MONTHS.find(m => m.value === competency?.month)?.label || competency?.month;

  return (
    <Shell>
      <Stack gap="lg">
        {/* Header */}
        <Paper p="md" radius="md" withBorder>
          <Group justify="space-between" align="center">
            <Group>
              <ActionIcon 
                variant="light" 
                size="lg" 
                onClick={() => router.push('/competencias')}
              >
                <IconArrowLeft size={20} />
              </ActionIcon>
              <div>
                <Title order={2}>
                  Competência {monthName}/{competency?.year}
                </Title>
                <Text c="dimmed" size="sm">
                  {employee?.name || `Colaborador #${competency?.employee_id}`}
                </Text>
              </div>
            </Group>
            <Badge 
              size="xl"
              variant="gradient"
              gradient={competency?.status === 'aberta' ? 
                { from: 'blue', to: 'cyan' } : 
                competency?.status === 'fechada' ?
                { from: 'green', to: 'teal' } :
                { from: 'gray', to: 'dark' }
              }
            >
              {competency?.status}
            </Badge>
          </Group>
        </Paper>

        {/* Cards de Resumo Financeiro - Visual Melhorado */}
        <Grid>
          <Grid.Col span={{ base: 12, md: 8 }}>
            <Card shadow="md" padding="xl" radius="md" withBorder>
              <Stack gap="lg">
                <Group justify="space-between">
                  <Title order={3}>Resumo Financeiro</Title>
                  <Badge size="lg" variant="dot" color={totals.saldo === 0 ? 'green' : 'orange'}>
                    {totals.saldo === 0 ? 'Pago' : 'Pendente'}
                  </Badge>
                </Group>

                {/* Líquido Total */}
                <div>
                  <Group justify="space-between" mb="xs">
                    <Text size="sm" fw={500}>Salário Líquido (Total a Receber)</Text>
                    <Text size="xl" fw={700} c="violet.6">{formatCurrency(totals.liquido)}</Text>
                  </Group>
                  <Paper p="sm" bg="violet.0" radius="md">
                    <Group justify="space-between" mb={4}>
                      <Text size="xs" c="dimmed">Proventos</Text>
                      <Text size="sm" fw={600} c="green.7">{formatCurrency(totals.proventos)}</Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="xs" c="dimmed">Descontos</Text>
                      <Text size="sm" fw={600} c="red.7">- {formatCurrency(totals.descontos)}</Text>
                    </Group>
                  </Paper>
                </div>

                <Divider />

                {/* Pagamentos Realizados */}
                <div>
                  <Group justify="space-between" mb="xs">
                    <Text size="sm" fw={500}>Já Pago</Text>
                    <Group gap="xs">
                      <Text size="lg" fw={700} c="green.6">{formatCurrency(totalPago)}</Text>
                      {totalPago > (totals.liquido * 0.4) && (
                        <Badge color="red" variant="light" size="sm">Acima de 40%</Badge>
                      )}
                    </Group>
                  </Group>
                  
                  {/* Barra de Progresso Principal */}
                  <Paper p="md" bg="gray.0" radius="md">
                    <Stack gap="xs">
                      <Group justify="space-between">
                        <Text size="xs" c="dimmed">Progresso do Pagamento</Text>
                        <Text size="sm" fw={600} c="dark.3">
                          {totals.liquido > 0 ? ((totalPago / totals.liquido) * 100).toFixed(1) : 0}%
                        </Text>
                      </Group>
                      
                      <div style={{ position: 'relative', height: 24, background: '#e9ecef', borderRadius: 12, overflow: 'hidden' }}>
                        {/* Barra de Progresso */}
                        <div style={{ 
                          width: `${totals.liquido > 0 ? Math.min((totalPago / totals.liquido) * 100, 100) : 0}%`, 
                          height: '100%', 
                          background: totalPago > (totals.liquido * 0.4) 
                            ? 'linear-gradient(90deg, #fab005, #fd7e14)' 
                            : 'linear-gradient(90deg, #37b24d, #2f9e44)',
                          transition: 'width 0.3s ease',
                          borderRadius: 12
                        }} />
                        
                        {/* Marcador de 40% */}
                        <div style={{
                          position: 'absolute',
                          left: '40%',
                          top: 0,
                          bottom: 0,
                          width: 2,
                          background: 'rgba(0,0,0,0.3)',
                          zIndex: 2
                        }} />
                        <Text 
                          size="10px" 
                          c="dimmed" 
                          style={{ 
                            position: 'absolute', 
                            left: '40%', 
                            top: '50%', 
                            transform: 'translate(-50%, -50%)',
                            zIndex: 3,
                            background: 'rgba(255,255,255,0.8)',
                            padding: '0 4px',
                            borderRadius: 4,
                            fontWeight: 700
                          }}
                        >
                          40% (Vale)
                        </Text>
                      </div>

                      {/* Informações do Limite de Vale */}
                      <Group justify="space-between" mt={4}>
                        <Text size="xs" c="dimmed">
                          Limite de Vale (40%): <b>{formatCurrency(totals.liquido * 0.4)}</b>
                        </Text>
                        <Text size="xs" c={totalPago > (totals.liquido * 0.4) ? "red" : "dimmed"}>
                          {totalPago > (totals.liquido * 0.4) 
                            ? `Excedeu ${formatCurrency(totalPago - (totals.liquido * 0.4))}`
                            : `Disponível: ${formatCurrency((totals.liquido * 0.4) - totalPago)}`
                          }
                        </Text>
                      </Group>
                    </Stack>
                  </Paper>
                </div>

                <Divider />

                {/* Saldo Restante */}
                <Paper 
                  p="xl" 
                  radius="md"
                  style={{ 
                    background: totals.saldo > 0 
                      ? 'linear-gradient(135deg, #f59f00 0%, #fab005 100%)'
                      : 'linear-gradient(135deg, #37b24d 0%, #2f9e44 100%)',
                    color: 'white'
                  }}
                >
                  <Stack gap="xs" align="center">
                    <Text size="sm" opacity={0.95} fw={500}>
                      {totals.saldo > 0 ? 'Falta Pagar' : 'Totalmente Pago!'}
                    </Text>
                    <Text size="40px" fw={900} style={{ textShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                      {formatCurrency(Math.abs(totals.saldo))}
                    </Text>
                    {totals.saldo > 0 && (
                      <Text size="xs" opacity={0.9}>
                        Restam {((totals.saldo / totals.liquido) * 100).toFixed(1)}% do total
                      </Text>
                    )}
                  </Stack>
                </Paper>
              </Stack>
            </Card>
          </Grid.Col>

          {/* Cards Laterais */}
          <Grid.Col span={{ base: 12, md: 4 }}>
            <Stack gap="md">
              <Card shadow="sm" padding="lg" radius="md" withBorder style={{ 
                background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
                color: 'white'
              }}>
                <Group justify="space-between" mb="xs">
                  <Text size="xs" opacity={0.9}>Proventos</Text>
                  <ThemeIcon size={40} radius="md" variant="white" color="green">
                    <IconTrendingUp size={22} />
                  </ThemeIcon>
                </Group>
                <Text size="xl" fw={900}>{formatCurrency(totals.proventos)}</Text>
                <Text size="xs" opacity={0.85}>{items.filter(i => rubrics.find(r => r.id === i.rubric_id)?.type === 'provento').length} itens</Text>
              </Card>

              <Card shadow="sm" padding="lg" radius="md" withBorder style={{ 
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                color: 'white'
              }}>
                <Group justify="space-between" mb="xs">
                  <Text size="xs" opacity={0.9}>Descontos</Text>
                  <ThemeIcon size={40} radius="md" variant="white" color="red">
                    <IconTrendingDown size={22} />
                  </ThemeIcon>
                </Group>
                <Text size="xl" fw={900}>{formatCurrency(totals.descontos)}</Text>
                <Text size="xs" opacity={0.85}>{items.filter(i => rubrics.find(r => r.id === i.rubric_id)?.type === 'desconto').length} itens</Text>
              </Card>

              <Card shadow="sm" padding="lg" radius="md" withBorder style={{ 
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white'
              }}>
                <Group justify="space-between" mb="xs">
                  <Text size="xs" opacity={0.9}>Pagamentos</Text>
                  <ThemeIcon size={40} radius="md" variant="white" color="violet">
                    <IconCash size={22} />
                  </ThemeIcon>
                </Group>
                <Text size="xl" fw={900}>{formatCurrency(totalPago)}</Text>
                <Text size="xs" opacity={0.85}>{payments.length} lançamentos</Text>
              </Card>
            </Stack>
          </Grid.Col>
        </Grid>

        {/* Tabs para Itens e Pagamentos */}
        <Tabs defaultValue="itens" variant="outline">
          <Tabs.List>
            <Tabs.Tab value="itens" leftSection={<IconReceipt size={16} />}>
              Proventos e Descontos ({items.length})
            </Tabs.Tab>
            <Tabs.Tab value="pagamentos" leftSection={<IconCash size={16} />}>
              Pagamentos ({payments.length})
            </Tabs.Tab>
          </Tabs.List>

          {/* Tab: Itens (Proventos/Descontos) */}
          <Tabs.Panel value="itens" pt="md">
            <Card shadow="sm" padding="lg" radius="md" withBorder>
              <Group justify="space-between" mb="md">
                <Title order={4}>Itens da Competência</Title>
                <Button 
                  leftSection={<IconPlus size={16} />}
                  variant="gradient"
                  gradient={{ from: 'violet', to: 'purple' }}
                  onClick={handleOpenAddItem}
                >
                  Adicionar Item
                </Button>
              </Group>

              {items.length === 0 ? (
                <Paper p="xl" bg="gray.0" ta="center">
                  <IconReceipt size={48} color="gray" style={{ marginBottom: 10 }} />
                  <Text c="dimmed" mb="md">Nenhum item cadastrado</Text>
                  <Button 
                    variant="light" 
                    leftSection={<IconPlus size={16} />}
                    onClick={handleOpenAddItem}
                  >
                    Adicionar Primeiro Item
                  </Button>
                </Paper>
              ) : (
                <Table striped highlightOnHover withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Rubrica</Table.Th>
                      <Table.Th>Tipo</Table.Th>
                      <Table.Th>Descrição</Table.Th>
                      <Table.Th>Valor</Table.Th>
                      <Table.Th>Ações</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {items.map((item) => {
                      const rubric = rubrics.find(r => r.id === item.rubric_id);
                      const isProvento = rubric?.type === 'provento';
                      
                      return (
                        <Table.Tr key={item.id}>
                          <Table.Td>
                            <Group gap="sm">
                              <ThemeIcon 
                                size="sm" 
                                radius="xl" 
                                variant="light"
                                color={isProvento ? 'green' : 'red'}
                              >
                                {isProvento ? <IconTrendingUp size={14} /> : <IconTrendingDown size={14} />}
                              </ThemeIcon>
                              <Text fw={500}>{rubric?.name || `Rubrica #${item.rubric_id}`}</Text>
                            </Group>
                          </Table.Td>
                          <Table.Td>
                            <Badge 
                              variant="gradient"
                              gradient={isProvento ? { from: 'green', to: 'teal' } : { from: 'red', to: 'pink' }}
                            >
                              {isProvento ? 'Provento' : 'Desconto'}
                            </Badge>
                          </Table.Td>
                          <Table.Td>{item.notes || '-'}</Table.Td>
                          <Table.Td>
                            <Text fw={700} c={isProvento ? 'green' : 'red'}>
                              {isProvento ? '+' : '-'} {formatCurrency(Number(item.value) || 0)}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Group gap="xs">
                              <Tooltip label="Editar">
                                <ActionIcon 
                                  color="blue" 
                                  variant="light"
                                  onClick={() => handleOpenEditItem(item)}
                                >
                                  <IconEdit size={16} />
                                </ActionIcon>
                              </Tooltip>
                              <Tooltip label="Remover">
                                <ActionIcon 
                                  color="red" 
                                  variant="light"
                                  onClick={() => handleDeleteItem(item.id)}
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
                  <Table.Tfoot>
                    <Table.Tr style={{ backgroundColor: '#f8f9fa' }}>
                      <Table.Td colSpan={3}>
                        <Text fw={700}>TOTAIS</Text>
                      </Table.Td>
                      <Table.Td colSpan={2}>
                        <Stack gap={4}>
                          <Text size="sm" c="green">Proventos: {formatCurrency(totals.proventos)}</Text>
                          <Text size="sm" c="red">Descontos: {formatCurrency(totals.descontos)}</Text>
                          <Divider />
                          <Text fw={700}>Líquido: {formatCurrency(totals.liquido)}</Text>
                        </Stack>
                      </Table.Td>
                    </Table.Tr>
                  </Table.Tfoot>
                </Table>
              )}
            </Card>
          </Tabs.Panel>

          {/* Tab: Pagamentos */}
          <Tabs.Panel value="pagamentos" pt="md">
            <Card shadow="sm" padding="lg" radius="md" withBorder>
              <Group justify="space-between" mb="md">
                <Title order={4}>Pagamentos Realizados</Title>
                {totals.saldo > 0 && (
                  <Button 
                    leftSection={<IconCash size={16} />}
                    variant="gradient"
                    gradient={{ from: 'green', to: 'teal' }}
                    onClick={handleOpenAddPayment}
                  >
                    Registrar Pagamento
                  </Button>
                )}
              </Group>

              {payments.length === 0 ? (
                <Paper p="xl" bg="gray.0" ta="center">
                  <IconCash size={48} color="gray" style={{ marginBottom: 10 }} />
                  <Text c="dimmed" mb="md">Nenhum pagamento registrado</Text>
                  {totals.liquido > 0 && (
                    <Button 
                      variant="light" 
                      color="green"
                      leftSection={<IconCash size={16} />}
                      onClick={handleOpenAddPayment}
                    >
                      Registrar Primeiro Pagamento
                    </Button>
                  )}
                </Paper>
              ) : (
                <Table striped highlightOnHover withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Data</Table.Th>
                      <Table.Th>Descrição</Table.Th>
                      <Table.Th>Valor</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Assinatura</Table.Th>
                      <Table.Th ta="center">Ações</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {payments.map((payment) => (
                      <Table.Tr key={payment.id}>
                        <Table.Td>
                          {payment.payment_date 
                            ? new Date(payment.payment_date).toLocaleDateString('pt-BR')
                            : '-'
                          }
                        </Table.Td>
                        <Table.Td>{payment.description || '-'}</Table.Td>
                        <Table.Td>
                          <Text fw={700} c="green">
                            {formatCurrency(Number(payment.amount) || 0)}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge 
                            variant="gradient"
                            gradient={{ from: 'green', to: 'teal' }}
                          >
                            <IconCheck size={12} style={{ marginRight: 4 }} />
                            Pago
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          {payment.signature_status ? (
                            <Group gap="xs">
                              <Badge 
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
                              {payment.signed_at && (
                                <Text size="xs" c="dimmed">
                                  {new Date(payment.signed_at).toLocaleDateString('pt-BR')}
                                </Text>
                              )}
                            </Group>
                          ) : (
                            <Text size="sm" c="dimmed">Sem assinatura</Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs" justify="center">
                            {payment.signature_url && (
                              <Tooltip label="Abrir Link de Assinatura">
                                <ActionIcon 
                                  color="purple" 
                                  variant="light"
                                  component="a"
                                  href={payment.signature_url}
                                  target="_blank"
                                >
                                  <IconSignature size={16} />
                                </ActionIcon>
                              </Tooltip>
                            )}
                            {payment.signature_id && (
                              <Tooltip label="Baixar Recibo PDF">
                                <ActionIcon 
                                  color="green" 
                                  variant="light"
                                  onClick={() => handleDownloadReceipt(payment.signature_id)}
                                >
                                  <IconDownload size={16} />
                                </ActionIcon>
                              </Tooltip>
                            )}
                            {!payment.signature_id && (
                              <Tooltip label="Gerar Recibo para Assinatura">
                                <ActionIcon 
                                  color="blue" 
                                  variant="light"
                                  onClick={() => handleGenerateReceipt(payment.id)}
                                >
                                  <IconReceipt size={16} />
                                </ActionIcon>
                              </Tooltip>
                            )}
                            <Tooltip label="Remover">
                              <ActionIcon 
                                color="red" 
                                variant="light"
                                onClick={() => handleDeletePayment(payment.id)}
                              >
                                <IconTrash size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                  <Table.Tfoot>
                    <Table.Tr style={{ backgroundColor: '#f8f9fa' }}>
                      <Table.Td colSpan={2}>
                        <Text fw={700}>TOTAL PAGO</Text>
                      </Table.Td>
                      <Table.Td colSpan={3}>
                        <Text fw={700} c="green" size="lg">
                          {formatCurrency(totalPago)}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                    {totals.saldo > 0 && (
                      <Table.Tr style={{ backgroundColor: '#fff3cd' }}>
                        <Table.Td colSpan={2}>
                          <Text fw={700} c="orange">SALDO RESTANTE</Text>
                        </Table.Td>
                        <Table.Td colSpan={3}>
                          <Text fw={700} c="orange" size="lg">
                            {formatCurrency(totals.saldo)}
                          </Text>
                        </Table.Td>
                      </Table.Tr>
                    )}
                  </Table.Tfoot>
                </Table>
              )}
            </Card>
          </Tabs.Panel>
        </Tabs>

        {/* Modal Adicionar/Editar Item */}
        <Modal
          opened={itemModalOpened}
          onClose={() => { setItemModalOpened(false); setEditingItemId(null); itemForm.reset(); }}
          title={editingItemId ? 'Editar Item' : 'Adicionar Provento/Desconto'}
          size="md"
        >
          <form onSubmit={itemForm.onSubmit(handleSubmitItem)}>
            <Stack>
              <Select
                label="Rubrica"
                placeholder="Selecione a rubrica"
                data={rubrics.map(r => ({ 
                  value: String(r.id), 
                  label: `${r.code} - ${r.name} (${r.type === 'provento' ? 'Provento' : 'Desconto'}${r.default_value ? ` - R$ ${Number(r.default_value).toFixed(2)}` : ''})`
                }))}
                searchable
                required
                value={itemForm.values.rubric_id}
                onChange={(value) => handleRubricChange(value || '')}
              />

              <NumberInput
                label="Valor"
                placeholder="0,00"
                required
                min={0}
                decimalScale={2}
                fixedDecimalScale
                prefix="R$ "
                thousandSeparator="."
                decimalSeparator=","
                {...itemForm.getInputProps('value')}
              />

              <TextInput
                label="Descrição (opcional)"
                placeholder="Ex: Horas extras ref. semana 1"
                {...itemForm.getInputProps('description')}
              />

              <Group justify="flex-end" mt="md">
                <Button variant="light" onClick={() => { setItemModalOpened(false); setEditingItemId(null); itemForm.reset(); }}>
                  Cancelar
                </Button>
                <Button 
                  type="submit"
                  variant="gradient"
                  gradient={{ from: 'violet', to: 'purple' }}
                >
                  {editingItemId ? 'Salvar Alterações' : 'Adicionar Item'}
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>

        {/* Modal Registrar Pagamento */}
        <Modal
          opened={paymentModalOpened}
          onClose={() => { setPaymentModalOpened(false); paymentForm.reset(); }}
          title="Registrar Pagamento"
          size="md"
        >
          <form onSubmit={paymentForm.onSubmit(handleSubmitPayment)}>
            <Stack>
              <Paper p="md" bg="blue.0" radius="md">
                <Group justify="space-between">
                  <Text size="sm">Saldo a pagar:</Text>
                  <Text fw={700} size="lg" c="blue">{formatCurrency(totals.saldo)}</Text>
                </Group>
              </Paper>

              <NumberInput
                label="Valor do Pagamento"
                placeholder="0,00"
                required
                min={0}
                max={totals.saldo}
                decimalScale={2}
                fixedDecimalScale
                prefix="R$ "
                thousandSeparator="."
                decimalSeparator=","
                {...paymentForm.getInputProps('amount')}
              />

              <DatePickerInput
                label="Data do Pagamento"
                placeholder="Selecione a data"
                required
                {...paymentForm.getInputProps('payment_date')}
              />

              <TextInput
                label="Descrição (opcional)"
                placeholder="Ex: Pagamento via PIX"
                {...paymentForm.getInputProps('description')}
              />

              <Group justify="flex-end" mt="md">
                <Button variant="light" onClick={() => { setPaymentModalOpened(false); paymentForm.reset(); }}>
                  Cancelar
                </Button>
                <Button 
                  type="submit"
                  variant="gradient"
                  gradient={{ from: 'green', to: 'teal' }}
                  leftSection={<IconCheck size={16} />}
                >
                  Confirmar Pagamento
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>
      </Stack>
    </Shell>
  );
}

export default function CompetenciaDetailPage() {
  return (
    <ProtectedRoute>
      <CompetenciaDetailContent />
    </ProtectedRoute>
  );
}
