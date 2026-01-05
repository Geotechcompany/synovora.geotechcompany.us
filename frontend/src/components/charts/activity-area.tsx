import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from 'recharts';

type Point = { day: string; count: number };

function TooltipContent({
  active,
  payload,
  label,
}: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const value = payload[0]?.value as number | undefined;
  return (
    <div className="rounded-xl border border-slate-200 bg-white/95 px-3 py-2 text-xs shadow-sm backdrop-blur">
      <div className="font-semibold text-slate-900">{label}</div>
      <div className="text-slate-600">{value ?? 0} posts</div>
    </div>
  );
}

export function ActivityAreaChart({ data }: { data: Point[] }) {
  return (
    <div className="h-44 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
          <defs>
            <linearGradient id="synvoraArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#6366f1" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(15,23,42,0.06)" />
          <XAxis
            dataKey="day"
            tick={{ fontSize: 11, fill: '#64748b' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 11, fill: '#64748b' }}
            axisLine={false}
            tickLine={false}
            width={28}
          />
          <Tooltip content={<TooltipContent />} />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#4f46e5"
            strokeWidth={2}
            fill="url(#synvoraArea)"
            dot={false}
            activeDot={{ r: 4 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}


