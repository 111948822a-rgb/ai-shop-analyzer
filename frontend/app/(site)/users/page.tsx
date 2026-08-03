"use client";

// 用户分析页面（数据缺失骨架）
// 后端暂无对应 API，所有数据区域显示空状态占位

// ===== 指标卡 =====
function MetricCard({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="ds-card-hover p-5">
      <p className="ds-caption">{label}</p>
      <p className="mt-2 text-2xl font-bold tabular-nums text-gray-900">-</p>
      <div className="mt-2">
        {hint && <span className="ds-caption">{hint}</span>}
      </div>
    </div>
  );
}

// 区块标题
function SectionHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div>
      <h2 className="ds-title">{title}</h2>
      {subtitle && <p className="ds-subtitle mt-1">{subtitle}</p>}
    </div>
  );
}

// 空状态
function EmptyState({ emoji, source }: { emoji: string; source: string }) {
  return (
    <div className="ds-empty">
      <div className="mb-3 text-4xl opacity-30">{emoji}</div>
      <p className="ds-subtitle text-gray-400">暂无数据</p>
      <p className="ds-caption mt-1">需对接{source}接口</p>
    </div>
  );
}

export default function UsersPage() {
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="ds-title">用户分析</h1>
        <p className="ds-subtitle mt-1">
          用户增长、画像分布、消费分层与复购行为
        </p>
      </div>

      {/* 1. 顶部4列指标卡 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="累计粉丝数" hint="全店关注用户总数" />
        <MetricCard label="新增买家数" hint="周期内首次下单用户" />
        <MetricCard label="复购率" hint="二次下单用户占比" />
        <MetricCard label="客户留存率" hint="周期内活跃留存占比" />
      </div>

      {/* 2. 用户增长趋势（全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title="用户增长趋势"
          subtitle="新增粉丝与新增买家按日变化"
        />
        <div className="mt-4">
          <EmptyState emoji="📈" source="用户增长趋势" />
        </div>
      </section>

      {/* 3. 用户性别与年龄分布（左1/2） + 4. 买家地域 TOP10（右1/2） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="ds-card p-5">
          <SectionHeader
            title="用户性别与年龄分布"
            subtitle="买家性别占比与年龄段构成"
          />
          <div className="mt-4">
            <EmptyState emoji="👥" source="用户画像" />
          </div>
        </section>

        <section className="ds-card p-5">
          <SectionHeader
            title="买家地域 TOP10"
            subtitle="下单用户所在省市排行"
          />
          <div className="mt-4">
            <EmptyState emoji="🗺️" source="地域分布" />
          </div>
        </section>
      </div>

      {/* 5. 用户消费能力分层（左1/2） + 6. 复购行为分析（右1/2） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="ds-card p-5">
          <SectionHeader
            title="用户消费能力分层"
            subtitle="RFM 分群与客单价分层占比"
          />
          <div className="mt-4">
            <EmptyState emoji="💎" source="消费分层" />
          </div>
        </section>

        <section className="ds-card p-5">
          <SectionHeader
            title="复购行为分析"
            subtitle="复购周期、复购次数与复购 GMV 占比"
          />
          <div className="mt-4">
            <EmptyState emoji="🔁" source="复购分析" />
          </div>
        </section>
      </div>
    </div>
  );
}
