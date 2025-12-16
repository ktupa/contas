'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Paper, 
  TextInput, 
  PasswordInput, 
  Button, 
  Title, 
  Container,
  Center,
  Stack,
  Text,
  Box,
  ThemeIcon,
  Group
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconLock, IconMail, IconCash, IconChartLine, IconUsers, IconReceipt } from '@tabler/icons-react';
import { useAuthStore } from '@/lib/store';
import api from '@/lib/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const isMobile = useMediaQuery('(max-width: 768px)');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { data } = await api.post('/auth/login', { email, password });
      
      // Get user info
      const { data: user } = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` }
      });

      setAuth(user, data.access_token, data.refresh_token);
      
      notifications.show({
        title: 'Sucesso!',
        message: `Bem-vindo de volta, ${user.name}!`,
        color: 'green',
      });

      // Forçar recarregamento para garantir estado limpo
      window.location.href = '/dashboard';
    } catch (error: any) {
      let errorMessage = 'Email ou senha incorretos';
      
      if (error.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
          // Erro de validação (422)
          errorMessage = error.response.data.detail
            .map((err: any) => err.msg)
            .join(', ');
        } else if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        }
      }

      notifications.show({
        title: 'Erro no Login',
        message: errorMessage,
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box 
      style={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
    >
      <Container size={isMobile ? '100%' : 900} px={isMobile ? 0 : 'md'}>
        <Stack gap="xl" hiddenFrom="sm">
          {/* Mobile - Logo e Título */}
          <Stack align="center" gap="sm">
            <ThemeIcon size={70} radius="md" variant="white" color="violet">
              <IconCash size={40} />
            </ThemeIcon>
            <Title order={1} size={32} c="white" ta="center">
              Financeiro Pro
            </Title>
            <Text size="md" c="white" ta="center" opacity={0.95}>
              Sistema de Gestão de Pagamentos
            </Text>
          </Stack>
          
          {/* Mobile - Card de Login */}
          <Paper 
            radius="lg" 
            p="xl" 
            shadow="xl"
            style={{
              background: 'rgba(255, 255, 255, 0.98)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <form onSubmit={handleLogin}>
              <Stack gap="md">
                <Title order={3} ta="center">Entrar</Title>
                <TextInput
                  required
                  label="Email"
                  placeholder="seu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  leftSection={<IconMail size={18} />}
                  size="md"
                />
                <PasswordInput
                  required
                  label="Senha"
                  placeholder="Sua senha"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  leftSection={<IconLock size={18} />}
                  size="md"
                />
                <Button 
                  type="submit" 
                  fullWidth 
                  loading={loading}
                  size="lg"
                  variant="gradient"
                  gradient={{ from: 'violet', to: 'purple' }}
                  mt="md"
                >
                  Entrar
                </Button>
              </Stack>
            </form>
          </Paper>
        </Stack>

        <Group align="stretch" gap="xl" visibleFrom="sm">
          {/* Desktop - Branding */}
          <Box style={{ flex: 1, color: 'white' }}>
            <Stack gap="xl">
              <div>
                <Group mb="md">
                  <ThemeIcon size={60} radius="md" variant="white" color="violet">
                    <IconCash size={35} />
                  </ThemeIcon>
                  <Title order={1} size={42}>
                    Financeiro Pro
                  </Title>
                </Group>
                <Text size="xl" mb="md" fw={500}>
                  Sistema Completo de Gestão de Pagamentos
                </Text>
                <Text size="md" opacity={0.9}>
                  Controle total sobre os pagamentos de colaboradores da sua empresa
                </Text>
              </div>

              <Stack gap="md" mt="xl">
                <Group>
                  <ThemeIcon size={40} radius="md" variant="white" color="violet">
                    <IconChartLine size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={600} size="lg">Relatórios Detalhados</Text>
                    <Text size="sm" opacity={0.9}>Análise completa de pagamentos e despesas</Text>
                  </div>
                </Group>
                
                <Group>
                  <ThemeIcon size={40} radius="md" variant="white" color="violet">
                    <IconUsers size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={600} size="lg">Gestão de Colaboradores</Text>
                    <Text size="sm" opacity={0.9}>Cadastro e controle de funcionários</Text>
                  </div>
                </Group>
                
                <Group>
                  <ThemeIcon size={40} radius="md" variant="white" color="violet">
                    <IconReceipt size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={600} size="lg">Rubricas Personalizadas</Text>
                    <Text size="sm" opacity={0.9}>Configure proventos e descontos</Text>
                  </div>
                </Group>
              </Stack>
            </Stack>
          </Box>

          {/* Right side - Login Form */}
          <Paper 
            withBorder 
            shadow="xl" 
            p={40} 
            radius="md" 
            style={{ flex: '0 0 400px', backgroundColor: 'white' }}
          >
            <Stack gap="md">
              <div>
                <Title order={2} ta="center" mb="xs">
                  Bem-vindo!
                </Title>
                <Text c="dimmed" size="sm" ta="center" mb="xl">
                  Faça login para acessar o sistema
                </Text>
              </div>

              <form onSubmit={handleLogin}>
                <Stack gap="md">
                  <TextInput
                    label="Email"
                    placeholder="seu@email.com"
                    required
                    size="md"
                    leftSection={<IconMail size={18} />}
                    value={email}
                    onChange={(e) => setEmail(e.currentTarget.value)}
                  />

                  <PasswordInput
                    label="Senha"
                    placeholder="Digite sua senha"
                    required
                    size="md"
                    leftSection={<IconLock size={18} />}
                    value={password}
                    onChange={(e) => setPassword(e.currentTarget.value)}
                  />

                  <Button 
                    type="submit" 
                    fullWidth 
                    size="md"
                    loading={loading}
                    mt="md"
                    variant="gradient"
                    gradient={{ from: 'violet', to: 'purple', deg: 135 }}
                  >
                    Entrar no Sistema
                  </Button>
                </Stack>
              </form>
            </Stack>
          </Paper>
        </Group>
      </Container>
    </Box>
  );
}
