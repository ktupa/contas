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
  FileInput,
  Modal,
  ActionIcon,
  Tooltip,
  Alert,
  Paper,
  ThemeIcon,
  Box
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useMediaQuery } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import {
  IconCertificate,
  IconUpload,
  IconCheck,
  IconX,
  IconAlertTriangle,
  IconBuilding,
  IconCalendar,
  IconRefresh,
} from '@tabler/icons-react';
import api from '@/lib/api';
import { useRouter } from 'next/navigation';

function CertificadosContent() {
  const router = useRouter();
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);
  const [certificate, setCertificate] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [modalOpened, setModalOpened] = useState(false);

  const form = useForm({
    initialValues: {
      file: null as File | null,
      password: '',
    },
    validate: {
      file: (value) => (value ? null : 'Selecione o arquivo .pfx'),
      password: (value) => (value.length >= 1 ? null : 'Digite a senha do certificado'),
    },
  });

  useEffect(() => {
    loadCompanies();
  }, []);

  useEffect(() => {
    if (selectedCompany) {
      loadCertificate();
    }
  }, [selectedCompany]);

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

  const loadCertificate = async () => {
    if (!selectedCompany) return;

    try {
      setLoading(true);
      const { data } = await api.get(`/fiscal/companies/${selectedCompany}/certificate`);
      setCertificate(data);
    } catch (error: any) {
      if (error.response?.status === 404) {
        setCertificate(null);
      } else {
        console.error('Erro ao carregar certificado:', error);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUploadCertificate = async (values: any) => {
    if (!selectedCompany) return;

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', values.file);
      formData.append('password', values.password);

      await api.post(`/fiscal/companies/${selectedCompany}/certificate`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      notifications.show({
        title: 'Sucesso',
        message: 'Certificado enviado e validado com sucesso!',
        color: 'green',
      });

      setModalOpened(false);
      form.reset();
      loadCertificate();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao enviar certificado',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (newStatus: string) => {
    if (!selectedCompany) return;

    try {
      await api.patch(`/fiscal/companies/${selectedCompany}/certificate`, {
        status: newStatus,
      });

      notifications.show({
        title: 'Sucesso',
        message: 'Status atualizado com sucesso!',
        color: 'green',
      });

      loadCertificate();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao atualizar status',
        color: 'red',
      });
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-BR');
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: any = {
      active: { color: 'green', label: 'Ativo', icon: IconCheck },
      inactive: { color: 'gray', label: 'Inativo', icon: IconX },
      expired: { color: 'red', label: 'Expirado', icon: IconAlertTriangle },
      error: { color: 'orange', label: 'Erro', icon: IconAlertTriangle },
    };

    const config = statusConfig[status] || statusConfig.inactive;
    const Icon = config.icon;

    return (
      <Badge
        size="lg"
        variant="light"
        color={config.color}
        leftSection={<Icon size={14} />}
      >
        {config.label}
      </Badge>
    );
  };

  return (
    <Shell>
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={2}>Certificados Digitais</Title>
          <Button
            leftSection={<IconUpload size={16} />}
            onClick={() => setModalOpened(true)}
            disabled={!selectedCompany}
          >
            {certificate ? 'Atualizar Certificado' : 'Enviar Certificado'}
          </Button>
        </Group>

        <Select
          label="Empresa"
          placeholder="Selecione uma empresa"
          data={companies.map((c) => ({ value: String(c.id), label: c.name }))}
          value={selectedCompany}
          onChange={setSelectedCompany}
          leftSection={<IconBuilding size={16} />}
        />

        {certificate ? (
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Stack gap="md">
              <Group justify="space-between">
                <Group gap="sm">
                  <ThemeIcon size="xl" radius="xl" variant="light" color="blue">
                    <IconCertificate size={24} />
                  </ThemeIcon>
                  <div>
                    <Text size="lg" fw={600}>
                      Certificado A1
                    </Text>
                    <Text size="sm" c="dimmed">
                      CNPJ: {certificate.cnpj}
                    </Text>
                  </div>
                </Group>
                {getStatusBadge(certificate.status)}
              </Group>

              <Paper p="md" withBorder>
                <Stack gap="xs">
                  <Group justify="space-between">
                    <Text size="sm" c="dimmed">
                      Thumbprint
                    </Text>
                    <Text size="sm" fw={500} ff="monospace">
                      {certificate.cert_thumbprint?.substring(0, 16)}...
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm" c="dimmed">
                      Válido de
                    </Text>
                    <Text size="sm" fw={500}>
                      {formatDate(certificate.valid_from)}
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm" c="dimmed">
                      Válido até
                    </Text>
                    <Text
                      size="sm"
                      fw={500}
                      c={
                        new Date(certificate.valid_to) < new Date()
                          ? 'red'
                          : new Date(certificate.valid_to) <
                            new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
                          ? 'orange'
                          : 'green'
                      }
                    >
                      {formatDate(certificate.valid_to)}
                    </Text>
                  </Group>
                </Stack>
              </Paper>

              {certificate.last_error && (
                <Alert icon={<IconAlertTriangle size={16} />} title="Erro" color="red">
                  {certificate.last_error}
                </Alert>
              )}

              <Group gap="xs">
                {certificate.status === 'active' && (
                  <Button
                    variant="light"
                    color="gray"
                    onClick={() => handleToggleStatus('inactive')}
                  >
                    Desativar
                  </Button>
                )}
                {certificate.status === 'inactive' && (
                  <Button
                    variant="light"
                    color="green"
                    onClick={() => handleToggleStatus('active')}
                  >
                    Ativar
                  </Button>
                )}
              </Group>
            </Stack>
          </Card>
        ) : (
          <Alert icon={<IconAlertTriangle size={16} />} title="Nenhum certificado" color="blue">
            Esta empresa ainda não possui certificado digital cadastrado. Clique em &quot;Enviar
            Certificado&quot; para fazer o upload.
          </Alert>
        )}

        <Modal
          opened={modalOpened}
          onClose={() => setModalOpened(false)}
          title="Upload de Certificado Digital"
          size="md"
        >
          <form onSubmit={form.onSubmit(handleUploadCertificate)}>
            <Stack gap="md">
              <Alert icon={<IconAlertTriangle size={16} />} color="yellow">
                O certificado será criptografado e armazenado com segurança. A senha é necessária
                apenas para validação.
              </Alert>

              <FileInput
                label="Arquivo .pfx"
                placeholder="Selecione o arquivo .pfx"
                accept=".pfx,.p12"
                {...form.getInputProps('file')}
                required
              />

              <TextInput
                label="Senha do Certificado"
                placeholder="Digite a senha"
                type="password"
                {...form.getInputProps('password')}
                required
              />

              <Group justify="flex-end">
                <Button variant="light" onClick={() => setModalOpened(false)}>
                  Cancelar
                </Button>
                <Button type="submit" loading={loading} leftSection={<IconUpload size={16} />}>
                  Enviar Certificado
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>
      </Stack>
    </Shell>
  );
}

export default function CertificadosPage() {
  return (
    <ProtectedRoute>
      <CertificadosContent />
    </ProtectedRoute>
  );
}
