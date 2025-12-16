'use client';

import { useEffect, useState } from 'react';
import { Modal, Text, Button, Group, Stack, Progress } from '@mantine/core';
import { useAuthStore } from '@/lib/store';
import { notifications } from '@mantine/notifications';
import api from '@/lib/api';
import { useRouter } from 'next/navigation';

export function SessionMonitor() {
  const { accessToken, refreshToken, setAuth, logout } = useAuthStore();
  const [opened, setOpened] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const router = useRouter();

  // Função auxiliar para decodificar JWT
  const parseJwt = (token: string) => {
    try {
      return JSON.parse(atob(token.split('.')[1]));
    } catch (e) {
      return null;
    }
  };

  useEffect(() => {
    if (!accessToken) return;

    const checkToken = () => {
      const decoded = parseJwt(accessToken);
      if (!decoded || !decoded.exp) return;

      const now = Math.floor(Date.now() / 1000);
      const diff = decoded.exp - now;

      // Se faltar menos de 60 segundos e o modal não estiver aberto
      if (diff <= 60 && diff > 0 && !opened) {
        setOpened(true);
      }

      // Se o token expirou
      if (diff <= 0) {
        setOpened(false);
        handleLogout();
      }

      if (opened) {
        setTimeLeft(diff);
      }
    };

    const interval = setInterval(checkToken, 1000);
    return () => clearInterval(interval);
  }, [accessToken, opened]);

  const handleLogout = () => {
    logout();
    setOpened(false);
    router.push('/login');
    notifications.show({
      title: 'Sessão Expirada',
      message: 'Sua sessão expirou. Por favor, faça login novamente.',
      color: 'orange',
    });
  };

  const handleRenew = async () => {
    try {
      if (!refreshToken) {
        handleLogout();
        return;
      }

      const { data } = await api.post('/auth/refresh', { refresh_token: refreshToken });
      
      // Atualizar store com novo token
      // Precisamos decodificar o token para pegar os dados do usuário se necessário, 
      // mas aqui vamos manter o usuário atual e só atualizar os tokens
      const currentUser = useAuthStore.getState().user;
      if (currentUser) {
        setAuth(currentUser, data.access_token, data.refresh_token);
        notifications.show({
          title: 'Sessão Renovada',
          message: 'Sua sessão foi estendida com sucesso.',
          color: 'green',
        });
        setOpened(false);
      }
    } catch (error) {
      console.error('Erro ao renovar token:', error);
      handleLogout();
    }
  };

  return (
    <Modal 
      opened={opened} 
      onClose={() => {}} 
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      title="Sessão Expirando"
      centered
    >
      <Stack>
        <Text>Sua sessão irá expirar em <b>{timeLeft} segundos</b>.</Text>
        <Text size="sm" c="dimmed">Deseja manter-se conectado?</Text>
        
        <Progress value={(timeLeft / 60) * 100} color={timeLeft < 10 ? 'red' : 'orange'} animated />
        
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={handleLogout}>
            Sair Agora
          </Button>
          <Button color="blue" onClick={handleRenew}>
            Manter Conectado
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
