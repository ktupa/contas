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
  Select,
  TextInput,
  Modal,
  ActionIcon,
  Tooltip,
  Pagination,
  Grid,
  ThemeIcon,
  Tabs,
  Code,
  Loader,
  Center,
  Box,
  Divider,
  SimpleGrid,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import {
  IconFileText,
  IconRefresh,
  IconFilter,
  IconSearch,
  IconCalendar,
  IconBuilding,
  IconArrowRight,
  IconArrowLeft,
  IconFileDownload,
  IconKey,
  IconInfoCircle,
  IconFileTypePdf,
  IconFileCode,
  IconEye,
  IconX,
} from '@tabler/icons-react';
import api from '@/lib/api';
import { formatCurrency } from '@/lib/constants';

interface NfeDocument {
  id: string;
  chave: string;
  tipo: string;
  situacao: string;
  xml_kind?: string;
  numero?: string;
  serie?: string;
  data_emissao?: string;
  cnpj_emitente?: string;
  emitente_nome?: string;
  cnpj_destinatario?: string;
  destinatario_nome?: string;
  valor_total?: number;
}

function NotasFiscaisContent() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);
  const [documents, setDocuments] = useState<NfeDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [tipo, setTipo] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [dateRange, setDateRange] = useState<[Date | null, Date | null]>([null, null]);
  const [importModalOpened, setImportModalOpened] = useState(false);
  const [detailsModalOpened, setDetailsModalOpened] = useState(false);
  const [selectedNfe, setSelectedNfe] = useState<NfeDocument | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string>('');
  const [xmlContent, setXmlContent] = useState<string>('');
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [lastSync, setLastSync] = useState<any | null>(null);
  const [resolving, setResolving] = useState(false);
  
  const limit = 50;

  const importForm = useForm({
    initialValues: {
      chave: '',
    },
    validate: {
      chave: (value) =>
        value.length === 44 ? null : 'A chave deve ter 44 dígitos',
    },
  });

  useEffect(() => {
    loadCompanies();
  }, []);

  useEffect(() => {
    if (selectedCompany) {
      loadDocuments();
    }
  }, [selectedCompany, page, tipo, dateRange]);

  const loadCompanies = async () => {
    try {
      const { data } = await api.get('/companies');
      setCompanies(data);
      if (data.length > 0 && !selectedCompany) {
        setSelectedCompany(String(data[0].id));
      }
    } catch (error) {
      console.error('Erro ao carregar empresas:', error);
    }
  };

  const loadDocuments = async () => {
    if (!selectedCompany) return;

    try {
      setLoading(true);
      const params: any = {
        company_id: selectedCompany,
        skip: (page - 1) * limit,
        limit,
      };

      if (tipo) params.tipo = tipo;
      if (searchTerm) params.emitente = searchTerm;
      if (dateRange[0]) params.data_ini = dateRange[0].toISOString();
      if (dateRange[1]) params.data_fim = dateRange[1].toISOString();

      const { data } = await api.get('/fiscal/nfe', { params });
      setDocuments(data);
      setTotal(data.length);
    } catch (error) {
      console.error('Erro ao carregar documentos:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    if (!selectedCompany) return;

    try {
      setSyncing(true);
      const { data } = await api.post(`/fiscal/nfe/sync/${selectedCompany}`);
      setLastSync(data);
      
      notifications.show({
        title: 'Sincronização Concluída',
        message: `${data.docs_imported} documentos importados de ${data.docs_found} encontrados`,
        color: data.status === 'success' ? 'green' : data.status === 'partial' ? 'yellow' : 'orange',
      });

      loadDocuments();
    } catch (error: any) {
      notifications.show({
        title: 'Erro na Sincronização',
        message: error.response?.data?.error_message || 'Erro ao sincronizar',
        color: 'red',
      });
    } finally {
      setSyncing(false);
    }
  };

  const handleImportByKey = async (values: any) => {
    if (!selectedCompany) return;

    try {
      setLoading(true);
      const { data } = await api.post('/fiscal/nfe/import-by-key', {
        company_id: parseInt(selectedCompany),
        chave: values.chave,
      });

      notifications.show({
        title: 'Sucesso',
        message: `${data.docs_imported} documento(s) importado(s)`,
        color: 'green',
      });

      setImportModalOpened(false);
      importForm.reset();
      loadDocuments();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao importar',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = async (nfe: NfeDocument) => {
    setSelectedNfe(nfe);
    setDetailsModalOpened(true);
    setLoadingDetails(true);
    setPdfUrl('');
    setXmlContent('');

    try {
        if (nfe.xml_kind !== 'summary') {
          // Busca PDF autenticado e gera URL local (evita erro de auth no iframe)
          const pdfResponse = await api.get(`/fiscal/nfe/${nfe.id}/pdf`, {
            responseType: 'blob',
          });
          const pdfBlobUrl = URL.createObjectURL(pdfResponse.data);
          setPdfUrl(pdfBlobUrl);
        }

      const { data } = await api.get(`/fiscal/nfe/${nfe.id}/xml-content`);
      setXmlContent(data.xml_content);
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao carregar detalhes da NF-e',
        color: 'red',
      });
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleDownloadXML = async (nfeId: string) => {
    try {
      const { data } = await api.get(`/fiscal/nfe/${nfeId}/xml`);
      window.open(data.download_url, '_blank');
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao gerar link de download',
        color: 'red',
      });
    }
  };

  const handleDownloadPDF = async (nfeId: string, numero?: string, serie?: string) => {
    try {
      const response = await api.get(`/fiscal/nfe/${nfeId}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `nfe_${numero || 'sem-numero'}_${serie || 'sem-serie'}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao baixar PDF',
        color: 'red',
      });
    }
  };

  const handleResolveAll = async () => {
    if (!selectedCompany) return;
    try {
      setResolving(true);
      const { data } = await api.post(`/fiscal/nfe/resolve/${selectedCompany}`);
      notifications.show({
        title: 'Manifestação enviada',
        message: `${data.resolved} XML(s) completos obtidos, ${data.still_summary} ainda em resumo`,
        color: data.resolved > 0 ? 'green' : 'yellow',
      });
      loadDocuments();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao resolver XML',
        color: 'red',
      });
    } finally {
      setResolving(false);
    }
  };

  const handleResolveSingle = async (chave: string) => {
    if (!selectedCompany) return;
    try {
      setResolving(true);
      const { data } = await api.post(`/fiscal/nfe/resolve/${selectedCompany}/${chave}`);
      notifications.show({
        title: data.resolved ? 'XML completo obtido' : 'Manifestação registrada',
        message: data.resolved
          ? 'DANFE já disponível para esta chave'
          : 'A SEFAZ ainda não liberou o XML completo (tente novamente em alguns minutos)',
        color: data.resolved ? 'green' : 'yellow',
      });
      await loadDocuments();
      if (selectedNfe) {
        const updated = documents.find((d) => d.chave === chave);
        if (updated) setSelectedNfe(updated);
      }
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao manifestar',
        color: 'red',
      });
    } finally {
      setResolving(false);
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  const formatCNPJ = (cnpj: string) => {
    if (!cnpj) return '-';
    const cleaned = cnpj.replace(/\D/g, '');
    if (cleaned.length === 14) {
      return cleaned.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
    }
    return cnpj;
  };

  const getTipoBadge = (tipo: string) => {
    const config: any = {
      recebida: { color: 'blue', icon: IconArrowLeft, label: 'Entrada' },
      emitida: { color: 'green', icon: IconArrowRight, label: 'Saída' },
      desconhecida: { color: 'gray', icon: IconFileText, label: 'Desconhecida' },
    };

    const { color, icon: Icon, label } = config[tipo] || config.desconhecida;

    return (
      <Badge
        variant="light"
        color={color}
        leftSection={<Icon size={12} />}
        size="md"
      >
        {label}
      </Badge>
    );
  };

  const getSituacaoBadge = (situacao: string) => {
    const config: any = {
      autorizada: { color: 'green', label: 'Autorizada' },
      cancelada: { color: 'red', label: 'Cancelada' },
      denegada: { color: 'orange', label: 'Denegada' },
      desconhecida: { color: 'gray', label: 'Desconhecida' },
    };

    const { color, label } = config[situacao] || config.desconhecida;

    return (
      <Badge variant="dot" color={color} size="md">
        {label}
      </Badge>
    );
  };

  return (
    <Shell>
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={2}>📄 Notas Fiscais Eletrônicas</Title>
          <Group gap="xs">
            <Button
              variant="light"
              leftSection={<IconKey size={16} />}
              onClick={() => setImportModalOpened(true)}
            >
              Importar por Chave
            </Button>
            <Button
              variant="light"
              leftSection={<IconFileCode size={16} />}
              onClick={handleResolveAll}
              loading={resolving}
              disabled={!selectedCompany}
            >
              Resolver XML Completo
            </Button>
            <Button
              leftSection={<IconRefresh size={16} />}
              onClick={handleSync}
              loading={syncing}
              disabled={!selectedCompany}
            >
              Sincronizar Agora
            </Button>
          </Group>
        </Group>

        {lastSync && (
          <Card withBorder shadow="xs" padding="md" bg="blue.0">
            <Group justify="space-between" align="flex-start">
              <Group gap="xs">
                <ThemeIcon 
                  color={lastSync.status === 'success' ? 'green' : lastSync.status === 'partial' ? 'yellow' : 'orange'} 
                  variant="light"
                  size="lg"
                >
                  <IconInfoCircle size={20} />
                </ThemeIcon>
                <Stack gap={2}>
                  <Text fw={600} size="sm">Última Sincronização</Text>
                  <Text size="sm" c="dimmed">
                    <strong>{lastSync.docs_imported}</strong> de <strong>{lastSync.docs_found}</strong> documentos importados
                    {lastSync.last_nsu && ` • NSU: ${lastSync.last_nsu}`}
                  </Text>
                  {lastSync.error_message && (
                    <Text size="sm" c="red">⚠️ {lastSync.error_message}</Text>
                  )}
                </Stack>
              </Group>
            </Group>
          </Card>
        )}

        <Card shadow="sm" padding="md" radius="md" withBorder>
          <Grid>
            <Grid.Col span={{ base: 12, md: 3 }}>
              <Select
                label="Empresa"
                placeholder="Selecione uma empresa"
                data={companies.map((c) => ({ value: String(c.id), label: c.name }))}
                value={selectedCompany}
                onChange={setSelectedCompany}
                leftSection={<IconBuilding size={16} />}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 2 }}>
              <Select
                label="Tipo"
                placeholder="Todos"
                data={[
                  { value: 'recebida', label: 'Entrada' },
                  { value: 'emitida', label: 'Saída' },
                ]}
                value={tipo}
                onChange={setTipo}
                clearable
                leftSection={<IconFilter size={16} />}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 3 }}>
              <TextInput
                label="Buscar Emitente"
                placeholder="Nome ou CNPJ"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && loadDocuments()}
                leftSection={<IconSearch size={16} />}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 3 }}>
              <DatePickerInput
                type="range"
                label="Período"
                placeholder="Selecione período"
                value={dateRange}
                onChange={setDateRange}
                clearable
                leftSection={<IconCalendar size={16} />}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 1 }}>
              <Button
                fullWidth
                mt="xl"
                onClick={loadDocuments}
                leftSection={<IconSearch size={16} />}
              >
                Buscar
              </Button>
            </Grid.Col>
          </Grid>
        </Card>

        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Chave / Número</Table.Th>
                <Table.Th>Tipo</Table.Th>
                <Table.Th>Data</Table.Th>
                <Table.Th>Emitente</Table.Th>
                <Table.Th>Destinatário</Table.Th>
                <Table.Th>Valor Total</Table.Th>
                <Table.Th>Situação</Table.Th>
                <Table.Th>XML</Table.Th>
                <Table.Th>Ações</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {loading ? (
                <Table.Tr>
                  <Table.Td colSpan={9}>
                    <Center p="xl">
                      <Loader size="md" />
                    </Center>
                  </Table.Td>
                </Table.Tr>
              ) : documents.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={9}>
                    <Center p="xl">
                      <Stack align="center" gap="xs">
                        <IconFileText size={48} stroke={1.5} color="gray" />
                        <Text c="dimmed" size="sm">
                          Nenhuma nota fiscal encontrada
                        </Text>
                      </Stack>
                    </Center>
                  </Table.Td>
                </Table.Tr>
              ) : (
                documents.map((doc) => (
                  <Table.Tr key={doc.id}>
                    <Table.Td>
                      <Stack gap={2}>
                        <Text size="xs" ff="monospace" c="dimmed">
                          {doc.chave?.substring(0, 20)}...
                        </Text>
                        <Text size="sm" fw={500}>
                          Nº {doc.numero || '-'} / Série {doc.serie || '-'}
                        </Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>{getTipoBadge(doc.tipo)}</Table.Td>
                    <Table.Td>
                      <Text size="sm">{formatDate(doc.data_emissao || '')}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Stack gap={2}>
                        <Text size="sm" fw={500} lineClamp={1}>
                          {doc.emitente_nome || '-'}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {formatCNPJ(doc.cnpj_emitente || '')}
                        </Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>
                      <Stack gap={2}>
                        <Text size="sm" fw={500} lineClamp={1}>
                          {doc.destinatario_nome || '-'}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {formatCNPJ(doc.cnpj_destinatario || '')}
                        </Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" fw={700} c="green">
                        {doc.valor_total ? formatCurrency(doc.valor_total) : '-'}
                      </Text>
                    </Table.Td>
                    <Table.Td>{getSituacaoBadge(doc.situacao)}</Table.Td>
                    <Table.Td>
                      <Badge color={doc.xml_kind === 'full' ? 'green' : 'yellow'} variant="light">
                        {doc.xml_kind === 'full' ? 'Completa' : 'Resumo'}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Tooltip label="Visualizar DANFE">
                          <ActionIcon
                            variant="light"
                            color="blue"
                            onClick={() => handleViewDetails(doc)}
                          >
                            <IconEye size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Download PDF">
                          <ActionIcon
                            variant="light"
                            color="red"
                            onClick={() => handleDownloadPDF(doc.id, doc.numero, doc.serie)}
                          >
                            <IconFileTypePdf size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Download XML">
                          <ActionIcon
                            variant="light"
                            color="orange"
                            onClick={() => handleDownloadXML(doc.id)}
                          >
                            <IconFileCode size={16} />
                          </ActionIcon>
                        </Tooltip>
                        {doc.xml_kind === 'summary' && (
                          <Tooltip label="Manifestar e tentar baixar completo">
                            <ActionIcon
                              variant="light"
                              color="yellow"
                              onClick={() => handleResolveSingle(doc.chave)}
                              loading={resolving}
                            >
                              <IconRefresh size={16} />
                            </ActionIcon>
                          </Tooltip>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>

          {total > limit && (
            <Group justify="center" mt="md">
              <Pagination
                total={Math.ceil(total / limit)}
                value={page}
                onChange={setPage}
              />
            </Group>
          )}
        </Card>

        <Modal
          opened={importModalOpened}
          onClose={() => setImportModalOpened(false)}
          title="📥 Importar NF-e por Chave"
          size="md"
        >
          <form onSubmit={importForm.onSubmit(handleImportByKey)}>
            <Stack gap="md">
              <TextInput
                label="Chave de Acesso"
                placeholder="Digite a chave de 44 dígitos"
                {...importForm.getInputProps('chave')}
                maxLength={44}
                description="Chave de acesso da NF-e (44 dígitos)"
              />

              <Group justify="flex-end">
                <Button variant="light" onClick={() => setImportModalOpened(false)}>
                  Cancelar
                </Button>
                <Button type="submit" loading={loading} leftSection={<IconKey size={16} />}>
                  Importar
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>

        <Modal
          opened={detailsModalOpened}
          onClose={() => setDetailsModalOpened(false)}
          title={selectedNfe ? `📄 NF-e ${selectedNfe.numero}/${selectedNfe.serie}` : 'Detalhes da NF-e'}
          size="xl"
          fullScreen
        >
          {selectedNfe && (
            <Stack gap="md">
              <Card withBorder padding="md">
                <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }}>
                  <Box>
                    <Text size="xs" c="dimmed">Emitente</Text>
                    <Text size="sm" fw={600}>{selectedNfe.emitente_nome}</Text>
                    <Text size="xs" c="dimmed">{formatCNPJ(selectedNfe.cnpj_emitente || '')}</Text>
                  </Box>
                  <Box>
                    <Text size="xs" c="dimmed">Destinatário</Text>
                    <Text size="sm" fw={600}>{selectedNfe.destinatario_nome}</Text>
                    <Text size="xs" c="dimmed">{formatCNPJ(selectedNfe.cnpj_destinatario || '')}</Text>
                  </Box>
                  <Box>
                    <Text size="xs" c="dimmed">Valor Total</Text>
                    <Text size="lg" fw={700} c="green">
                      {selectedNfe.valor_total ? formatCurrency(selectedNfe.valor_total) : '-'}
                    </Text>
                  </Box>
                  <Box>
                    <Text size="xs" c="dimmed">Data Emissão</Text>
                    <Text size="sm" fw={600}>{formatDate(selectedNfe.data_emissao || '')}</Text>
                    <Group gap="xs" mt="xs">
                      {getTipoBadge(selectedNfe.tipo)} {getSituacaoBadge(selectedNfe.situacao)}
                      <Badge color={selectedNfe.xml_kind === 'full' ? 'green' : 'yellow'} variant="light">
                        {selectedNfe.xml_kind === 'full' ? 'XML Completo' : 'XML Resumo'}
                      </Badge>
                    </Group>
                  </Box>
                </SimpleGrid>
              </Card>

              {selectedNfe.xml_kind === 'summary' && (
                <Card withBorder radius="md" bg="yellow.0">
                  <Group justify="space-between" align="center">
                    <Stack gap={4}>
                      <Text fw={600}>XML em modo resumo</Text>
                      <Text size="sm" c="dimmed">Para gerar DANFE completo, manifeste a operação e rebaixe o XML completo.</Text>
                    </Stack>
                    <Button
                      variant="light"
                      color="yellow"
                      leftSection={<IconRefresh size={16} />}
                      onClick={() => handleResolveSingle(selectedNfe.chave)}
                      loading={resolving}
                    >
                      Manifestar e resolver
                    </Button>
                  </Group>
                </Card>
              )}

              <Divider />

              <Tabs defaultValue="pdf">
                <Tabs.List>
                  <Tabs.Tab value="pdf" leftSection={<IconFileTypePdf size={16} />}>
                    DANFE (PDF)
                  </Tabs.Tab>
                  <Tabs.Tab value="xml" leftSection={<IconFileCode size={16} />}>
                    XML
                  </Tabs.Tab>
                </Tabs.List>

                <Tabs.Panel value="pdf" pt="md">
                  {loadingDetails ? (
                    <Center p="xl">
                      <Loader size="lg" />
                    </Center>
                  ) : selectedNfe.xml_kind === 'summary' ? (
                    <Center p="xl">
                      <Stack gap="xs" align="center">
                        <Text fw={600}>XML em resumo</Text>
                        <Text c="dimmed" size="sm">Manifeste para habilitar o DANFE.</Text>
                      </Stack>
                    </Center>
                  ) : pdfUrl ? (
                    <Box
                      style={{
                        width: '100%',
                        height: '70vh',
                        border: '1px solid #dee2e6',
                        borderRadius: '8px',
                        overflow: 'hidden',
                      }}
                    >
                      <iframe
                        src={pdfUrl}
                        style={{ width: '100%', height: '100%', border: 'none' }}
                        title="DANFE"
                      />
                    </Box>
                  ) : (
                    <Center p="xl">
                      <Text c="dimmed">Erro ao carregar PDF</Text>
                    </Center>
                  )}
                </Tabs.Panel>

                <Tabs.Panel value="xml" pt="md">
                  {loadingDetails ? (
                    <Center p="xl">
                      <Loader size="lg" />
                    </Center>
                  ) : xmlContent ? (
                    <Code block style={{ maxHeight: '70vh', overflow: 'auto' }}>
                      {xmlContent}
                    </Code>
                  ) : (
                    <Center p="xl">
                      <Text c="dimmed">Erro ao carregar XML</Text>
                    </Center>
                  )}
                </Tabs.Panel>
              </Tabs>

              <Divider />

              <Group justify="flex-end">
                <Button
                  variant="light"
                  leftSection={<IconFileDownload size={16} />}
                  onClick={() => handleDownloadXML(selectedNfe.id)}
                >
                  Download XML
                </Button>
                <Button
                  variant="light"
                  leftSection={<IconFileTypePdf size={16} />}
                  onClick={() => handleDownloadPDF(selectedNfe.id, selectedNfe.numero, selectedNfe.serie)}
                >
                  Download PDF
                </Button>
                <Button
                  variant="default"
                  leftSection={<IconX size={16} />}
                  onClick={() => setDetailsModalOpened(false)}
                >
                  Fechar
                </Button>
              </Group>
            </Stack>
          )}
        </Modal>
      </Stack>
    </Shell>
  );
}

export default function NotasFiscaisPage() {
  return (
    <ProtectedRoute>
      <NotasFiscaisContent />
    </ProtectedRoute>
  );
}
