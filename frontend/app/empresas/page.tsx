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
  ActionIcon,
  Card,
  Text,
  Switch,
  Paper,
  ThemeIcon,
  SimpleGrid,
  Select,
  Divider,
  Tabs,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconEdit, IconTrash, IconPlus, IconBuildingStore, IconBuilding, IconUsers, IconMapPin, IconReceipt } from '@tabler/icons-react';
import api from '@/lib/api';

// Lista de UFs com códigos IBGE
const UF_OPTIONS = [
  { value: 'AC', label: 'AC - Acre', ibge: '12' },
  { value: 'AL', label: 'AL - Alagoas', ibge: '27' },
  { value: 'AP', label: 'AP - Amapá', ibge: '16' },
  { value: 'AM', label: 'AM - Amazonas', ibge: '13' },
  { value: 'BA', label: 'BA - Bahia', ibge: '29' },
  { value: 'CE', label: 'CE - Ceará', ibge: '23' },
  { value: 'DF', label: 'DF - Distrito Federal', ibge: '53' },
  { value: 'ES', label: 'ES - Espírito Santo', ibge: '32' },
  { value: 'GO', label: 'GO - Goiás', ibge: '52' },
  { value: 'MA', label: 'MA - Maranhão', ibge: '21' },
  { value: 'MT', label: 'MT - Mato Grosso', ibge: '51' },
  { value: 'MS', label: 'MS - Mato Grosso do Sul', ibge: '50' },
  { value: 'MG', label: 'MG - Minas Gerais', ibge: '31' },
  { value: 'PA', label: 'PA - Pará', ibge: '15' },
  { value: 'PB', label: 'PB - Paraíba', ibge: '25' },
  { value: 'PR', label: 'PR - Paraná', ibge: '41' },
  { value: 'PE', label: 'PE - Pernambuco', ibge: '26' },
  { value: 'PI', label: 'PI - Piauí', ibge: '22' },
  { value: 'RJ', label: 'RJ - Rio de Janeiro', ibge: '33' },
  { value: 'RN', label: 'RN - Rio Grande do Norte', ibge: '24' },
  { value: 'RS', label: 'RS - Rio Grande do Sul', ibge: '43' },
  { value: 'RO', label: 'RO - Rondônia', ibge: '11' },
  { value: 'RR', label: 'RR - Roraima', ibge: '14' },
  { value: 'SC', label: 'SC - Santa Catarina', ibge: '42' },
  { value: 'SP', label: 'SP - São Paulo', ibge: '35' },
  { value: 'SE', label: 'SE - Sergipe', ibge: '28' },
  { value: 'TO', label: 'TO - Tocantins', ibge: '17' },
];

const REGIME_OPTIONS = [
  { value: 'simples', label: 'Simples Nacional' },
  { value: 'lucro_presumido', label: 'Lucro Presumido' },
  { value: 'lucro_real', label: 'Lucro Real' },
  { value: 'mei', label: 'MEI' },
];

interface Company {
  id: number;
  name: string;
  cnpj: string | null;
  ie: string | null;
  im: string | null;
  email: string | null;
  phone: string | null;
  cep: string | null;
  logradouro: string | null;
  numero: string | null;
  complemento: string | null;
  bairro: string | null;
  cidade: string | null;
  uf: string | null;
  codigo_ibge_cidade: string | null;
  codigo_ibge_uf: string | null;
  address: string | null;
  regime_tributario: string | null;
  is_main: boolean;
  active: boolean;
}

interface CompanySummary {
  company_id: number;
  company_name: string;
  total_employees: number;
  total_expenses: number;
  total_pending: number;
  total_paid: number;
}

function EmpresasContent() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [summaries, setSummaries] = useState<CompanySummary[]>([]);
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const form = useForm({
    initialValues: {
      name: '',
      cnpj: '',
      ie: '',
      im: '',
      email: '',
      phone: '',
      cep: '',
      logradouro: '',
      numero: '',
      complemento: '',
      bairro: '',
      cidade: '',
      uf: '',
      codigo_ibge_cidade: '',
      address: '',
      regime_tributario: '',
      is_main: false,
      active: true,
    },
    validate: {
      name: (value) => (!value || value.length < 2 ? 'Nome é obrigatório (mínimo 2 caracteres)' : null),
      email: (value) => {
        if (!value) return null;
        return /^\S+@\S+$/.test(value) ? null : 'Email inválido';
      },
    },
  });

  useEffect(() => {
    loadCompanies();
    loadSummaries();
  }, []);

  const loadCompanies = async () => {
    try {
      const response = await api.get('/companies?active_only=false');
      setCompanies(response.data);
    } catch (error) {
      notifications.show({
        title: 'Erro',
        message: 'Erro ao carregar empresas',
        color: 'red',
      });
    }
  };

  const loadSummaries = async () => {
    try {
      const response = await api.get('/companies/summary');
      setSummaries(response.data);
    } catch (error) {
      console.error('Erro ao carregar resumos:', error);
    }
  };

  // Busca CEP via ViaCEP
  const handleCepBlur = async () => {
    const cep = form.values.cep.replace(/\D/g, '');
    if (cep.length !== 8) return;

    try {
      const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const data = await response.json();
      
      if (!data.erro) {
        form.setValues({
          ...form.values,
          logradouro: data.logradouro || '',
          bairro: data.bairro || '',
          cidade: data.localidade || '',
          uf: data.uf || '',
          codigo_ibge_cidade: data.ibge || '',
        });
      }
    } catch (error) {
      console.error('Erro ao buscar CEP:', error);
    }
  };

  // Atualiza código IBGE da UF quando UF muda
  const handleUfChange = (value: string | null) => {
    form.setFieldValue('uf', value || '');
  };

  const handleSubmit = async (values: typeof form.values) => {
    setLoading(true);
    try {
      const ufOption = UF_OPTIONS.find(u => u.value === values.uf);
      
      const payload = {
        name: values.name,
        cnpj: values.cnpj || null,
        ie: values.ie || null,
        im: values.im || null,
        email: values.email || null,
        phone: values.phone || null,
        cep: values.cep || null,
        logradouro: values.logradouro || null,
        numero: values.numero || null,
        complemento: values.complemento || null,
        bairro: values.bairro || null,
        cidade: values.cidade || null,
        uf: values.uf || null,
        codigo_ibge_cidade: values.codigo_ibge_cidade || null,
        codigo_ibge_uf: ufOption?.ibge || null,
        address: values.address || null,
        regime_tributario: values.regime_tributario || null,
        is_main: values.is_main,
        active: values.active,
      };

      if (editingId) {
        await api.put(`/companies/${editingId}`, payload);
        notifications.show({ title: 'Sucesso', message: 'Empresa atualizada', color: 'green' });
      } else {
        await api.post('/companies', payload);
        notifications.show({ title: 'Sucesso', message: 'Empresa criada', color: 'green' });
      }
      setOpened(false);
      loadCompanies();
      loadSummaries();
      form.reset();
      setEditingId(null);
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao salvar empresa',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (company: Company) => {
    setEditingId(company.id);
    form.setValues({
      name: company.name,
      cnpj: company.cnpj || '',
      ie: company.ie || '',
      im: company.im || '',
      email: company.email || '',
      phone: company.phone || '',
      cep: company.cep || '',
      logradouro: company.logradouro || '',
      numero: company.numero || '',
      complemento: company.complemento || '',
      bairro: company.bairro || '',
      cidade: company.cidade || '',
      uf: company.uf || '',
      codigo_ibge_cidade: company.codigo_ibge_cidade || '',
      address: company.address || '',
      regime_tributario: company.regime_tributario || '',
      is_main: company.is_main,
      active: company.active,
    });
    setOpened(true);
  };

  const handleDelete = async (company: Company) => {
    if (company.is_main) {
      notifications.show({
        title: 'Erro',
        message: 'Não é possível excluir a empresa principal',
        color: 'red',
      });
      return;
    }
    
    if (!confirm(`Deseja realmente desativar "${company.name}"?`)) return;
    
    try {
      await api.delete(`/companies/${company.id}`);
      notifications.show({ title: 'Sucesso', message: 'Empresa desativada', color: 'green' });
      loadCompanies();
      loadSummaries();
    } catch (error: any) {
      notifications.show({
        title: 'Erro',
        message: error.response?.data?.detail || 'Erro ao desativar empresa',
        color: 'red',
      });
    }
  };

  const mainCompany = companies.find(c => c.is_main);
  const otherCompanies = companies.filter(c => !c.is_main);

  const getSummary = (companyId: number) => summaries.find(s => s.company_id === companyId);

  const getRegimeLabel = (regime: string | null) => {
    if (!regime) return '-';
    const option = REGIME_OPTIONS.find(r => r.value === regime);
    return option?.label || regime;
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={2}>Empresas</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={() => {
          setEditingId(null);
          form.reset();
          setOpened(true);
        }}>
          Nova Empresa
        </Button>
      </Group>

      {/* Empresa Principal */}
      {mainCompany && (
        <Paper withBorder p="lg" radius="md" bg="blue.0">
          <Group justify="space-between" mb="md">
            <Group>
              <ThemeIcon size="xl" radius="md" variant="filled" color="blue">
                <IconBuilding size={24} />
              </ThemeIcon>
              <div>
                <Text fw={700} size="lg">{mainCompany.name}</Text>
                <Text size="sm" c="dimmed">Empresa Principal</Text>
              </div>
            </Group>
            <ActionIcon variant="subtle" color="blue" onClick={() => handleEdit(mainCompany)}>
              <IconEdit size={18} />
            </ActionIcon>
          </Group>
          
          <SimpleGrid cols={{ base: 2, md: 4 }} mb="md">
            <div>
              <Text size="xs" c="dimmed">CNPJ</Text>
              <Text size="sm" fw={500}>{mainCompany.cnpj || '-'}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">Inscrição Estadual</Text>
              <Text size="sm" fw={500}>{mainCompany.ie || '-'}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">Regime Tributário</Text>
              <Text size="sm" fw={500}>{getRegimeLabel(mainCompany.regime_tributario)}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">UF</Text>
              <Text size="sm" fw={500}>{mainCompany.uf || '-'}</Text>
            </div>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 2, md: 4 }}>
            <div>
              <Text size="xs" c="dimmed">Email</Text>
              <Text size="sm" fw={500}>{mainCompany.email || '-'}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">Telefone</Text>
              <Text size="sm" fw={500}>{mainCompany.phone || '-'}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">Cidade</Text>
              <Text size="sm" fw={500}>{mainCompany.cidade ? `${mainCompany.cidade}/${mainCompany.uf}` : '-'}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">Funcionários</Text>
              <Text size="sm" fw={500}>{getSummary(mainCompany.id)?.total_employees || 0}</Text>
            </div>
          </SimpleGrid>
        </Paper>
      )}

      {/* Outras Empresas */}
      <Card withBorder radius="md">
        <Group mb="md">
          <ThemeIcon variant="light" size="lg">
            <IconBuildingStore size={20} />
          </ThemeIcon>
          <Text fw={600}>Fornecedores e Parceiros</Text>
        </Group>
        
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Nome</Table.Th>
              <Table.Th>CNPJ</Table.Th>
              <Table.Th>UF</Table.Th>
              <Table.Th>Contato</Table.Th>
              <Table.Th>Funcionários</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Ações</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {otherCompanies.map((company) => {
              const summary = getSummary(company.id);
              return (
                <Table.Tr key={company.id}>
                  <Table.Td fw={500}>{company.name}</Table.Td>
                  <Table.Td>{company.cnpj || '-'}</Table.Td>
                  <Table.Td>{company.uf || '-'}</Table.Td>
                  <Table.Td>
                    <Text size="sm">{company.email || '-'}</Text>
                    <Text size="xs" c="dimmed">{company.phone || ''}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4}>
                      <IconUsers size={14} />
                      <Text size="sm">{summary?.total_employees || 0}</Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={company.active ? 'green' : 'gray'}>
                      {company.active ? 'Ativo' : 'Inativo'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={0}>
                      <ActionIcon variant="subtle" color="blue" onClick={() => handleEdit(company)}>
                        <IconEdit size={16} />
                      </ActionIcon>
                      <ActionIcon variant="subtle" color="red" onClick={() => handleDelete(company)}>
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              );
            })}
            {otherCompanies.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text ta="center" c="dimmed" py="md">
                    Nenhuma empresa cadastrada. Adicione fornecedores e parceiros.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title={editingId ? "Editar Empresa" : "Nova Empresa"} size="xl">
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Tabs defaultValue="geral">
            <Tabs.List mb="md">
              <Tabs.Tab value="geral" leftSection={<IconBuilding size={14} />}>
                Dados Gerais
              </Tabs.Tab>
              <Tabs.Tab value="endereco" leftSection={<IconMapPin size={14} />}>
                Endereço
              </Tabs.Tab>
              <Tabs.Tab value="fiscal" leftSection={<IconReceipt size={14} />}>
                Dados Fiscais
              </Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="geral">
              <Stack>
                <TextInput
                  label="Nome *"
                  placeholder="Nome da Empresa"
                  required
                  withAsterisk
                  {...form.getInputProps('name')}
                />
                
                <Group grow>
                  <TextInput
                    label="CNPJ"
                    placeholder="00.000.000/0000-00"
                    {...form.getInputProps('cnpj')}
                  />

                  <TextInput
                    label="Telefone"
                    placeholder="(00) 00000-0000"
                    {...form.getInputProps('phone')}
                  />
                </Group>

                <TextInput
                  label="Email"
                  placeholder="contato@empresa.com"
                  type="email"
                  {...form.getInputProps('email')}
                />

                <Group>
                  <Switch
                    label="Empresa Principal (própria)"
                    description="Marque se esta é a sua empresa"
                    {...form.getInputProps('is_main', { type: 'checkbox' })}
                  />
                  
                  <Switch
                    label="Ativo"
                    {...form.getInputProps('active', { type: 'checkbox' })}
                  />
                </Group>
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="endereco">
              <Stack>
                <Group grow>
                  <TextInput
                    label="CEP"
                    placeholder="00000-000"
                    {...form.getInputProps('cep')}
                    onBlur={handleCepBlur}
                    description="Digite o CEP para preencher automaticamente"
                  />
                  <Select
                    label="UF"
                    placeholder="Selecione"
                    data={UF_OPTIONS}
                    searchable
                    clearable
                    value={form.values.uf}
                    onChange={handleUfChange}
                  />
                </Group>

                <Group grow>
                  <TextInput
                    label="Logradouro"
                    placeholder="Rua, Avenida..."
                    {...form.getInputProps('logradouro')}
                  />
                  <TextInput
                    label="Número"
                    placeholder="123"
                    style={{ maxWidth: 100 }}
                    {...form.getInputProps('numero')}
                  />
                </Group>

                <Group grow>
                  <TextInput
                    label="Complemento"
                    placeholder="Sala, Bloco..."
                    {...form.getInputProps('complemento')}
                  />
                  <TextInput
                    label="Bairro"
                    placeholder="Bairro"
                    {...form.getInputProps('bairro')}
                  />
                </Group>

                <Group grow>
                  <TextInput
                    label="Cidade"
                    placeholder="Cidade"
                    {...form.getInputProps('cidade')}
                  />
                  <TextInput
                    label="Código IBGE Cidade"
                    placeholder="0000000"
                    {...form.getInputProps('codigo_ibge_cidade')}
                    description="Preenchido automaticamente pelo CEP"
                  />
                </Group>

                <Divider my="sm" label="Endereço Legado (opcional)" labelPosition="center" />
                
                <Textarea
                  label="Endereço Completo"
                  placeholder="Endereço em texto livre (campo antigo)"
                  rows={2}
                  {...form.getInputProps('address')}
                  description="Use apenas se não preencher os campos acima"
                />
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="fiscal">
              <Stack>
                <Text size="sm" c="dimmed" mb="sm">
                  Dados necessários para emissão de NF-e e comunicação com a SEFAZ.
                </Text>

                <Group grow>
                  <TextInput
                    label="Inscrição Estadual"
                    placeholder="000.000.000.000"
                    {...form.getInputProps('ie')}
                    description="Deixe em branco se isento"
                  />
                  <TextInput
                    label="Inscrição Municipal"
                    placeholder="000000000"
                    {...form.getInputProps('im')}
                  />
                </Group>

                <Select
                  label="Regime Tributário"
                  placeholder="Selecione o regime"
                  data={REGIME_OPTIONS}
                  clearable
                  {...form.getInputProps('regime_tributario')}
                />

                <Paper withBorder p="md" radius="sm" bg="gray.0">
                  <Text size="sm" fw={500} mb="xs">Códigos IBGE (automático)</Text>
                  <Group>
                    <div>
                      <Text size="xs" c="dimmed">Código UF</Text>
                      <Text size="sm">{UF_OPTIONS.find(u => u.value === form.values.uf)?.ibge || '-'}</Text>
                    </div>
                    <div>
                      <Text size="xs" c="dimmed">Código Cidade</Text>
                      <Text size="sm">{form.values.codigo_ibge_cidade || '-'}</Text>
                    </div>
                  </Group>
                </Paper>
              </Stack>
            </Tabs.Panel>
          </Tabs>

          <Button type="submit" loading={loading} mt="xl" fullWidth>
            Salvar
          </Button>
        </form>
      </Modal>
    </Stack>
  );
}

export default function EmpresasPage() {
  return (
    <ProtectedRoute>
      <Shell>
        <EmpresasContent />
      </Shell>
    </ProtectedRoute>
  );
}
