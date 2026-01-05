import clsx from 'clsx';

export function Skeleton({
  className,
  rounded = 'md',
}: {
  className?: string;
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | 'full';
}) {
  const roundedClass =
    rounded === 'none'
      ? 'rounded-none'
      : rounded === 'sm'
        ? 'rounded-sm'
        : rounded === 'md'
          ? 'rounded-md'
          : rounded === 'lg'
            ? 'rounded-lg'
            : rounded === 'xl'
              ? 'rounded-xl'
              : 'rounded-full';

  return (
    <div
      className={clsx(
        'animate-pulse bg-slate-200/80',
        'dark:bg-slate-800/60',
        roundedClass,
        className,
      )}
    />
  );
}


