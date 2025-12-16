'use client';

import { useState, useEffect } from 'react';
import { Container, Title, Button, Group, Table, Badge, Paper, Text, ActionIcon, Tooltip, CopyButton, Alert } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconPlus, IconSignature, IconReceipt, IconDownload, IconExternalLink, IconCopy, IconCheck, IconLink, IconTrash, IconAlertCircle } from '@tabler/icons-react';
import { getSignatures, getSignatureDownloadUrl, bulkDeleteSignatures, SignatureDocument } from '@/lib/signatures';
import CreateSignatureModal from '@/components/signatures/CreateSignatureModal';
import CreateReceiptModal from '@/components/signatures/CreateReceiptModal';
import { Shell } from '@/components/Shell';

export default function SignaturesPage() {
  const [signatures, setSignatures] = useState<SignatureDocument[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [receiptModalOpen, setReceiptModalOpen] = useState(false);
  const [loadingDownload, setLoadingDownload] = useState<string | null>(null);

  const fetchSignatures = async () => {
    try {
      const data = await getSignatures();
      setSignatures(data);
    } catch (error) {
      console.error('Error fetching signatures:', error);
    }
  };

  useEffect(() => {
    fetchSignatures();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'green';
      case 'sent': return 'blue';
      case 'draft': return 'gray';
      case 'pending_local': return 'yellow';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed': return 'Assinado';
      case 'sent': return 'Enviado';
      case 'draft': return 'Rascunho';
      case 'pending_local': return 'Pendente';
      case 'error': return 'Erro';
      default: return status;
    }
  };

  const handleDownload = async (id: string) => {
    setLoadingDownload(id);
    try {
      const url = await getSignatureDownloadUrl(id);
      window.open(url, '_blank');
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Não foi possível obter o link do documento',
        color: 'red',
      });
    } finally {
      setLoadingDownload(null);
    }
  };

  const handleBulkDelete = async () => {
    if (!confirm('Deseja realmente remover TODOS os documentos de assinatura? Esta ação não pode ser desfeita.')) {
      return;
    }

    try {
      const result = await bulkDeleteSignatures();
      notifications.show({
        title: 'Sucesso',
        message: `${result.deleted_count} documento(s) removido(s)`,
        color: 'green',
      });
      fetchSignatures();
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao remover documentos',
        color: 'red',
      });
    }
  };

  return (
    <Shell>
      <Container size="xl" py="xl">
        <Group justify="space-between" mb="xl">
          <Title order={2}>Assinaturas Eletrônicas</Title>
          <Group>
            <Button leftSection={<IconReceipt size={20} />} variant="light" onClick={() => setReceiptModalOpen(true)}>
              Gerar Recibo
            </Button>
            <Button leftSection={<IconPlus size={20} />} onClick={() => setModalOpen(true)}>
              Nova Assinatura
            </Button>
            {signatures.length > 0 && (
              <Button 
                leftSection={<IconTrash size={20} />} 
                color="red" 
                variant="light"
                onClick={handleBulkDelete}
              >
                Limpar Tudo
              </Button>
            )}
          </Group>
        </Group>

        {signatures.some(s => s.status === 'pending_local') && (
          <Alert 
            icon={<IconAlertCircle size={16} />} 
            title="⚠️ Limite do Documenso Atingido" 
            color="orange"
            mb="md"
          >
            <Text size="sm">
              O serviço de assinatura eletrônica (Documenso) atingiu o limite de documentos deste mês.
              Os recibos foram salvos localmente e podem ser baixados, mas não estão disponíveis para assinatura eletrônica.
            </Text>
            <Text size="xs" mt="xs" c="dimmed">
              Entre em contato com o administrador para atualizar o plano ou aguarde o próximo ciclo de cobrança.
            </Text>
          </Alert>
        )}

        <Paper withBorder p="md" radius="md">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Título</Table.Th>
                <Table.Th>Colaborador</Table.Th>
                <Table.Th>Tipo</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Link de Assinatura</Table.Th>
                <Table.Th>Data Criação</Table.Th>
                <Table.Th>Data Assinatura</Table.Th>
                <Table.Th ta="center">Ações</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {signatures.map((sig) => (
                <Table.Tr key={sig.id}>
                  <Table.Td>
                    <Group gap="sm">
                      <IconSignature size={16} color="#228be6" />
                      <Text size="sm" fw={500}>{sig.title}</Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{sig.signer_name || '-'}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="light" color="gray">
                      {sig.entity_type === 'payment_receipt' ? 'Recibo' : 
                       sig.entity_type === 'receipt' ? 'Recibo' : 
                       sig.entity_type || 'Documento'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={getStatusColor(sig.status)}>{getStatusLabel(sig.status)}</Badge>
                  </Table.Td>
                  <Table.Td>
                    {sig.sign_url ? (
                      <Group gap="xs">
                        <CopyButton value={sig.sign_url}>
                          {({ copied, copy }) => (
                            <Tooltip label={copied ? 'Copiado!' : 'Copiar link'}>
                              <ActionIcon color={copied ? 'green' : 'blue'} variant="light" onClick={copy}>
                                {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                              </ActionIcon>
                            </Tooltip>
                          )}
                        </CopyButton>
                        <Tooltip label="Abrir link de assinatura">
                          <ActionIcon 
                            color="teal" 
                            variant="light" 
                            component="a"
                            href={sig.sign_url}
                            target="_blank"
                          >
                            <IconLink size={16} />
                          </ActionIcon>
                        </Tooltip>
                      </Group>
                    ) : (
                      <Text size="sm" c="dimmed">-</Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">
                      {new Date(sig.created_at).toLocaleDateString('pt-BR', { 
                        day: '2-digit', 
                        month: '2-digit', 
                        year: 'numeric' 
                      })}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" c={sig.signed_at ? 'green' : 'dimmed'}>
                      {sig.signed_at 
                        ? new Date(sig.signed_at).toLocaleDateString('pt-BR', { 
                            day: '2-digit', 
                            month: '2-digit', 
                            year: 'numeric' 
                          })
                        : '-'}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs" justify="center">
                      <Tooltip label="Visualizar/Baixar PDF">
                        <ActionIcon 
                          variant="light" 
                          color="blue"
                          onClick={() => handleDownload(sig.id)}
                          loading={loadingDownload === sig.id}
                        >
                          <IconDownload size={18} />
                        </ActionIcon>
                      </Tooltip>
                      {sig.provider_doc_id && (
                        <Tooltip label="Abrir no Documenso">
                          <ActionIcon 
                            variant="light" 
                            color="grape"
                            component="a"
                            href={`https://app.documenso.com/documents/${sig.provider_doc_id}`}
                            target="_blank"
                          >
                            <IconExternalLink size={18} />
                          </ActionIcon>
                        </Tooltip>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {signatures.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={7}>
                    <Text ta="center" c="dimmed" py="xl">
                      Nenhuma assinatura encontrada. Clique em "Gerar Recibo" para criar um documento.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Paper>

        <CreateSignatureModal 
          opened={modalOpen} 
          onClose={() => setModalOpen(false)} 
          onSuccess={() => {
            setModalOpen(false);
            fetchSignatures();
          }}
        />

        <CreateReceiptModal
          opened={receiptModalOpen}
          onClose={() => setReceiptModalOpen(false)}
          onSuccess={() => {
            setReceiptModalOpen(false);
            fetchSignatures();
          }}
        />
      </Container>
    </Shell>
  );
}
