'use client';

import { Table, Card, Stack, Group, Text, Badge, ActionIcon, Box } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { ReactNode } from 'react';

interface Column {
  key: string;
  label: string;
  render?: (value: any, row: any) => ReactNode;
  mobileLabel?: string;
  hiddenOnMobile?: boolean;
}

interface ResponsiveTableProps {
  columns: Column[];
  data: any[];
  onRowClick?: (row: any) => void;
  actions?: (row: any) => ReactNode;
}

export function ResponsiveTable({ columns, data, onRowClick, actions }: ResponsiveTableProps) {
  const isMobile = useMediaQuery('(max-width: 768px)');

  if (isMobile) {
    return (
      <Stack gap="sm">
        {data.map((row, idx) => (
          <Card 
            key={idx} 
            padding="md" 
            radius="md" 
            withBorder
            style={{ cursor: onRowClick ? 'pointer' : 'default' }}
            onClick={() => onRowClick?.(row)}
          >
            <Stack gap="xs">
              {columns
                .filter(col => !col.hiddenOnMobile)
                .map((col) => (
                  <Group key={col.key} justify="space-between" wrap="nowrap">
                    <Text size="sm" c="dimmed" fw={500} style={{ minWidth: '100px' }}>
                      {col.mobileLabel || col.label}:
                    </Text>
                    <Box style={{ flex: 1, textAlign: 'right' }}>
                      {col.render ? col.render(row[col.key], row) : (
                        <Text size="sm">{row[col.key]}</Text>
                      )}
                    </Box>
                  </Group>
                ))}
              {actions && (
                <Group justify="flex-end" gap="xs" mt="sm" pt="sm" style={{ borderTop: '1px solid #dee2e6' }}>
                  {actions(row)}
                </Group>
              )}
            </Stack>
          </Card>
        ))}
      </Stack>
    );
  }

  return (
    <Table striped highlightOnHover withTableBorder>
      <Table.Thead>
        <Table.Tr>
          {columns.map((col) => (
            <Table.Th key={col.key}>{col.label}</Table.Th>
          ))}
          {actions && <Table.Th>Ações</Table.Th>}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {data.map((row, idx) => (
          <Table.Tr 
            key={idx}
            style={{ cursor: onRowClick ? 'pointer' : 'default' }}
            onClick={() => onRowClick?.(row)}
          >
            {columns.map((col) => (
              <Table.Td key={col.key}>
                {col.render ? col.render(row[col.key], row) : row[col.key]}
              </Table.Td>
            ))}
            {actions && (
              <Table.Td>
                <Group gap="xs">
                  {actions(row)}
                </Group>
              </Table.Td>
            )}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}
