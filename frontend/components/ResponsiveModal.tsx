'use client';

import { Modal, ModalProps } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';

interface ResponsiveModalProps extends ModalProps {
  children: React.ReactNode;
}

export function ResponsiveModal({ children, ...props }: ResponsiveModalProps) {
  const isMobile = useMediaQuery('(max-width: 768px)');

  return (
    <Modal
      {...props}
      fullScreen={isMobile}
      size={isMobile ? 'full' : props.size || 'md'}
      padding={isMobile ? 'md' : props.padding}
      overlayProps={{
        ...props.overlayProps,
        opacity: isMobile ? 0.7 : (props.overlayProps?.opacity || 0.55),
      }}
    >
      {children}
    </Modal>
  );
}
