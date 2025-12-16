'use client';

import { useState } from 'react';
import { Shell } from '@/components/Shell';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { 
  Title, 
  Button, 
  Select,
  Stack,
  Group,
  Card,
  Text,
  Table,
  Badge
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { notifications } from '@mantine/notifications';
import api from '@/lib/api';

function RelatoriosContent() {
  const [competency, setCompetency] = useState<string>('');
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleGenerateReport = async () => {
    if (!competency) {
      notifications.show({
        title: 'Atenção',
        message: 'Selecione uma competência',
        color: 'yellow',
      });
      return;
    }

    setLoading(true);
    try {
      const { data } = await api.get(`/reports/competency/${competency}`);
      setReportData(data);
      notifications.show({
        title: 'Sucesso',
        message: 'Relatório gerado com sucesso!',
        color: 'green',
      });
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao gerar relatório',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePeriodReport = async () => {
    if (!startDate || !endDate) {
      notifications.show({
        title: 'Atenção',
        message: 'Selecione o período',
        color: 'yellow',
      });
      return;
    }

    setLoading(true);
    try {
      const { data } = await api.get('/reports/period', {
        params: {
          start_date: startDate.toISOString().split('T')[0],
          end_date: endDate.toISOString().split('T')[0]
        }
      });
      setReportData(data);
      notifications.show({
        title: 'Sucesso',
        message: 'Relatório de período gerado!',
        color: 'green',
      });
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao gerar relatório',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Shell>
      <Stack>
        <Title order={2}>Relatórios de Pagamentos</Title>

        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Stack>
            <Text fw={500}>Relatório por Competência</Text>
            <Group align="flex-end">
              <Select
                label="Competência"
                placeholder="Selecione o mês/ano"
                data={[
                  { value: '12/2025', label: 'Dezembro/2025' },
                  { value: '11/2025', label: 'Novembro/2025' },
                  { value: '10/2025', label: 'Outubro/2025' },
                ]}
                value={competency}
                onChange={(val) => setCompetency(val || '')}
                style={{ flex: 1 }}
              />
              <Button onClick={handleGenerateReport} loading={loading}>
                Gerar Relatório
              </Button>
            </Group>
          </Stack>
        </Card>

        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Stack>
            <Text fw={500}>Relatório por Período</Text>
            <Group align="flex-end">
              <DatePickerInput
                label="Data Início"
                placeholder="Selecione a data"
                value={startDate}
                onChange={setStartDate}
                style={{ flex: 1 }}
              />
              <DatePickerInput
                label="Data Fim"
                placeholder="Selecione a data"
                value={endDate}
                onChange={setEndDate}
                style={{ flex: 1 }}
              />
              <Button onClick={handleGeneratePeriodReport} loading={loading}>
                Gerar Relatório
              </Button>
            </Group>
          </Stack>
        </Card>

        {reportData && (
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Stack>
              <Group justify="space-between">
                <Text size="xl" fw={700}>Resumo Financeiro</Text>
              </Group>
              
              <Group grow>
                <Card bg="green.1" padding="md">
                  <Text size="sm" c="dimmed">Total Proventos</Text>
                  <Text size="xl" fw={700} c="green">
                    R$ {(Number(reportData.total_earnings) || 0).toFixed(2)}
                  </Text>
                </Card>
                <Card bg="red.1" padding="md">
                  <Text size="sm" c="dimmed">Total Descontos</Text>
                  <Text size="xl" fw={700} c="red">
                    R$ {(Number(reportData.total_deductions) || 0).toFixed(2)}
                  </Text>
                </Card>
                <Card bg="blue.1" padding="md">
                  <Text size="sm" c="dimmed">Líquido Total</Text>
                  <Text size="xl" fw={700} c="blue">
                    R$ {(Number(reportData.net_total) || 0).toFixed(2)}
                  </Text>
                </Card>
              </Group>

              {reportData.payments && reportData.payments.length > 0 && (
                <>
                  <Text size="lg" fw={600} mt="md">Detalhamento por Colaborador</Text>
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Colaborador</Table.Th>
                        <Table.Th>Proventos</Table.Th>
                        <Table.Th>Descontos</Table.Th>
                        <Table.Th>Líquido</Table.Th>
                        <Table.Th>Status</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {reportData.payments.map((payment: any) => (
                        <Table.Tr key={payment.id}>
                          <Table.Td>{payment.employee_name}</Table.Td>
                          <Table.Td c="green">R$ {(Number(payment.total_earnings) || 0).toFixed(2)}</Table.Td>
                          <Table.Td c="red">R$ {(Number(payment.total_deductions) || 0).toFixed(2)}</Table.Td>
                          <Table.Td fw={700}>R$ {(Number(payment.net_amount) || 0).toFixed(2)}</Table.Td>
                          <Table.Td>
                            <Badge color={payment.status === 'paid' ? 'green' : payment.status === 'pending' ? 'yellow' : 'gray'}>
                              {payment.status === 'paid' ? 'Pago' : payment.status === 'pending' ? 'Pendente' : payment.status}
                            </Badge>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </>
              )}
            </Stack>
          </Card>
        )}
      </Stack>
    </Shell>
  );
}

export default function RelatoriosPage() {
  return (
    <ProtectedRoute>
      <RelatoriosContent />
    </ProtectedRoute>
  );
}
