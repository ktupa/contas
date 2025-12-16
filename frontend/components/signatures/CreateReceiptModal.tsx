import { useState } from 'react';
import { Modal, TextInput, Button, Group, Stack, NumberInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { createReceiptSignature } from '@/lib/signatures';
import { notifications } from '@mantine/notifications';
import { IconReceipt } from '@tabler/icons-react';

interface Props {
  opened: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CreateReceiptModal({ opened, onClose, onSuccess }: Props) {
  const [loading, setLoading] = useState(false);
  
  const form = useForm({
    initialValues: {
      title: 'Recibo de Pagamento',
      company_name: 'Minha Empresa Ltda',
      company_cnpj: '00.000.000/0001-00',
      employee_name: '',
      employee_email: '',
      employee_cpf: '',
      amount: 0,
      reference_month: new Date().toISOString().slice(0, 7), // YYYY-MM
      description: 'Serviços prestados',
    },
    validate: {
      employee_name: (value) => (value.length < 2 ? 'Nome inválido' : null),
      employee_email: (value) => (/^\S+@\S+$/.test(value) ? null : 'Email inválido'),
      amount: (value) => (value <= 0 ? 'Valor deve ser maior que zero' : null),
    },
  });

  const handleSubmit = async (values: typeof form.values) => {
    setLoading(true);
    try {
      await createReceiptSignature({
        ...values,
        reference_month: values.reference_month.split('-').reverse().join('/'), // Convert YYYY-MM to MM/YYYY
      });
      notifications.show({ title: 'Sucesso', message: 'Recibo gerado e enviado para assinatura', color: 'green' });
      form.reset();
      onSuccess();
    } catch (error) {
      console.error(error);
      notifications.show({ title: 'Erro', message: 'Falha ao gerar recibo', color: 'red' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Gerar Recibo e Enviar para Assinatura" size="lg">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          <TextInput
            label="Título do Documento"
            required
            {...form.getInputProps('title')}
          />
          
          <Group grow>
            <TextInput
              label="Nome da Empresa"
              required
              {...form.getInputProps('company_name')}
            />
            <TextInput
              label="CNPJ"
              required
              {...form.getInputProps('company_cnpj')}
            />
          </Group>

          <Group grow>
            <TextInput
              label="Nome do Funcionário"
              placeholder="João da Silva"
              required
              {...form.getInputProps('employee_name')}
            />
            <TextInput
              label="CPF"
              placeholder="000.000.000-00"
              required
              {...form.getInputProps('employee_cpf')}
            />
          </Group>

          <TextInput
            label="Email do Funcionário (para assinatura)"
            placeholder="joao@email.com"
            required
            {...form.getInputProps('employee_email')}
          />

          <Group grow>
            <NumberInput
              label="Valor (R$)"
              required
              min={0}
              decimalScale={2}
              fixedDecimalScale
              prefix="R$ "
              {...form.getInputProps('amount')}
            />
            <TextInput
              label="Mês de Referência"
              type="month"
              required
              {...form.getInputProps('reference_month')}
            />
          </Group>

          <TextInput
            label="Descrição"
            required
            {...form.getInputProps('description')}
          />

          <Group justify="flex-end" mt="xl">
            <Button variant="default" onClick={onClose}>Cancelar</Button>
            <Button type="submit" loading={loading} leftSection={<IconReceipt size={16} />}>
              Gerar e Enviar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
