import React from 'react';
import { cn } from '../../lib/utils';

export interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'destructive' | 'success';
}

const Toast = React.forwardRef<HTMLDivElement, ToastProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    const variants = {
      default: 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700',
      destructive: 'bg-red-50 dark:bg-red-900 border-red-200 dark:border-red-800',
      success: 'bg-green-50 dark:bg-green-900 border-green-200 dark:border-green-800'
    };

    return (
      <div
        ref={ref}
        className={cn(
          'pointer-events-auto w-full max-w-sm overflow-hidden rounded-lg border shadow-lg',
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);
Toast.displayName = 'Toast';

export { Toast };