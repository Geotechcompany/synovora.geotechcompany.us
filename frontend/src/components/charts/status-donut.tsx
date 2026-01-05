import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipProps,
} from 'recharts';

type Slice = {
  name: string;
  value: number;
  color: string;
};

function TooltipContent({
  active,
  payload,
}: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const slice = payload[0]?.payload as Slice | undefined;
  if (!slice) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white/95 px-3 py-2 text-xs shadow-sm backdrop-blur">
      <div className="font-semibold text-slate-900">{slice.name}</div>
      <div className="text-slate-600">{slice.value}</div>
    </div>
  );
}

export function StatusDonutChart({
  data,
}: {
  data: Slice[];
}) {
  const nonZero = data.filter((d) => d.value > 0);
  const chartData = nonZero.length ? nonZero : [{ name: 'No data', value: 1, color: '#cbd5e1' }];

  return (
    <div className="h-44 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip content={<TooltipContent />} />
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            innerRadius="62%"
            outerRadius="88%"
            paddingAngle={3}
            stroke="rgba(15,23,42,0.06)"
          >
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}


