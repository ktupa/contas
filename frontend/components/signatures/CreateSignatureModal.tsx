import { useState } from 'react';
import { Modal, TextInput, Button, Group, FileInput, Stack, ActionIcon, Text } from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconTrash, IconPlus } from '@tabler/icons-react';
import { createSignatureRequest, Signer } from '@/lib/signatures';
import { notifications } from '@mantine/notifications';

interface Props {
  opened: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CreateSignatureModal({ opened, onClose, onSuccess }: Props) {
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  
  const form = useForm({
    initialValues: {
      title: '',
      entityType: 'misc', // Default to misc
      entityId: 0, // Default to 0
      signers: [{ name: '', email: '', role: 'SIGNER' }] as Signer[],
    },
    validate: {
      title: (value) => (value.length < 3 ? 'Título muito curto' : null),
      signers: {
        name: (value) => (value.length < 2 ? 'Nome inválido' : null),
        email: (value) => (/^\S+@\S+$/.test(value) ? null : 'Email inválido'),
      },
    },
  });

  const handleSubmit = async (values: typeof form.values) => {
    if (!file) {
      notifications.show({ title: 'Erro', message: 'Selecione um arquivo PDF', color: 'red' });
      return;
    }

    setLoading(true);
    try {
      await createSignatureRequest(
        values.title,
        values.entityType,
        values.entityId,
        values.signers,
        file
      );
      notifications.show({ title: 'Sucesso', message: 'Solicitação criada com sucesso', color: 'green' });
      form.reset();
      setFile(null);
      onSuccess();
    } catch (error) {
      console.error(error);
      notifications.show({ title: 'Erro', message: 'Falha ao criar solicitação', color: 'red' });
    } finally {
      setLoading(false);
    }
  };

  const addSigner = () => {
    form.insertListItem('signers', { name: '', email: '', role: 'SIGNER' });
  };

  const removeSigner = (index: number) => {
    form.removeListItem('signers', index);
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Nova Solicitação de Assinatura" size="lg">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <TextInput
            label="Título do Documento"
            placeholder="Ex: Contrato de Prestação de Serviços"
            required
            {...form.getInputProps('title')}
          />
          
          <FileInput
            label="Arquivo PDF"
            placeholder="Selecione o arquivo"
            accept="application/pdf"
            required
            value={file}
            onChange={setFile}
          />

          <Text fw={500} size="sm" mt="md">Assinantes</Text>
          
          {form.values.signers.map((item, index) => (
            <Group key={index} align="flex-start">
              <TextInput
                placeholder="Nome"
                style={{ flex: 1 }}
                {...form.getInputProps(`signers.${index}.name`)}
              />
              <TextInput
                placeholder="Email"
                style={{ flex: 1 }}
                {...form.getInputProps(`signers.${index}.email`)}
              />
              <ActionIcon color="red" onClick={() => removeSigner(index)} disabled={form.values.signers.length === 1}>
                <IconTrash size={16} />
              </ActionIcon>
            </Group>
          ))}

          <Button variant="subtle" leftSection={<IconPlus size={16} />} onClick={addSigner} size="compact-sm">
            Adicionar Assinante
          </Button>

          <Group justify="flex-end" mt="xl">
            <Button variant="default" onClick={onClose}>Cancelar</Button>
            <Button type="submit" loading={loading}>Criar Solicitação</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
