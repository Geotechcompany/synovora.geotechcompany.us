import { Skeleton } from './skeleton';

export function AppShellSkeleton() {
  return (
    <div className="min-h-screen bg-slate-100 md:flex">
      <aside className="hidden md:flex md:w-64 md:flex-col md:border-r md:border-slate-200 md:bg-white/90">
        <div className="p-6 space-y-8">
          <div className="flex justify-center">
            <Skeleton className="h-12 w-40" rounded="xl" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" rounded="xl" />
            <Skeleton className="h-10 w-full" rounded="xl" />
            <Skeleton className="h-10 w-full" rounded="xl" />
            <Skeleton className="h-10 w-full" rounded="xl" />
          </div>
        </div>
        <div className="mt-auto p-6 border-t border-slate-100">
          <div className="flex items-center gap-3">
            <Skeleton className="h-12 w-12" rounded="full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
          <Skeleton className="mt-4 h-10 w-full" rounded="xl" />
        </div>
      </aside>

      <main className="flex-1">
        <div className="max-w-6xl mx-auto p-6 space-y-8">
          <div className="flex items-center justify-end gap-4">
            <div className="text-right space-y-2">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-4 w-40" />
            </div>
            <Skeleton className="h-10 w-10" rounded="full" />
            <Skeleton className="h-9 w-24" rounded="full" />
          </div>

          <Skeleton className="h-56 w-full" rounded="xl" />

          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-7 w-40" />
              <Skeleton className="h-4 w-72" />
            </div>
            <Skeleton className="h-10 w-32" rounded="xl" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Skeleton className="h-36 w-full" rounded="xl" />
            <Skeleton className="h-36 w-full" rounded="xl" />
            <Skeleton className="h-36 w-full" rounded="xl" />
          </div>

          <Skeleton className="h-44 w-full" rounded="xl" />
        </div>
      </main>
    </div>
  );
}


