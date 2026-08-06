"use client";

// 用户分析页面（数据缺失骨架）
// 后端暂无对应 API，所有数据区域显示空状态占位

import { useT } from "@/lib/i18n/context";

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
  const t = useT();
  return (
    <div className="ds-empty">
      <div className="mb-3 text-4xl opacity-30">{emoji}</div>
      <p className="ds-subtitle text-gray-400">{t("common.noData")}</p>
      <p className="ds-caption mt-1">{t("skeleton.needApi", { source })}</p>
    </div>
  );
}

export default function UsersPage() {
  const t = useT();
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="ds-title">{t("skeleton.usersTitle")}</h1>
        <p className="ds-subtitle mt-1">{t("skeleton.usersSub")}</p>
      </div>

      {/* 1. 顶部4列指标卡 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label={t("skeleton.usersK1")}
          hint={t("skeleton.usersK1Hint")}
        />
        <MetricCard
          label={t("skeleton.usersK2")}
          hint={t("skeleton.usersK2Hint")}
        />
        <MetricCard
          label={t("skeleton.usersK3")}
          hint={t("skeleton.usersK3Hint")}
        />
        <MetricCard
          label={t("skeleton.usersK4")}
          hint={t("skeleton.usersK4Hint")}
        />
      </div>

      {/* 2. 用户增长趋势（全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title={t("skeleton.usersS1")}
          subtitle={t("skeleton.usersS1Sub")}
        />
        <div className="mt-4">
          <EmptyState emoji="📈" source={t("skeleton.usersSrc1")} />
        </div>
      </section>

      {/* 3. 用户性别与年龄分布（左1/2） + 4. 买家地域 TOP10（右1/2） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="ds-card p-5">
          <SectionHeader
            title={t("skeleton.usersS2")}
            subtitle={t("skeleton.usersS2Sub")}
          />
          <div className="mt-4">
            <EmptyState emoji="👥" source={t("skeleton.usersSrc2")} />
          </div>
        </section>

        <section className="ds-card p-5">
          <SectionHeader
            title={t("skeleton.usersS3")}
            subtitle={t("skeleton.usersS3Sub")}
          />
          <div className="mt-4">
            <EmptyState emoji="🗺️" source={t("skeleton.usersSrc3")} />
          </div>
        </section>
      </div>

      {/* 5. 用户消费能力分层（左1/2） + 6. 复购行为分析（右1/2） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="ds-card p-5">
          <SectionHeader
            title={t("skeleton.usersS4")}
            subtitle={t("skeleton.usersS4Sub")}
          />
          <div className="mt-4">
            <EmptyState emoji="💎" source={t("skeleton.usersSrc4")} />
          </div>
        </section>

        <section className="ds-card p-5">
          <SectionHeader
            title={t("skeleton.usersS5")}
            subtitle={t("skeleton.usersS5Sub")}
          />
          <div className="mt-4">
            <EmptyState emoji="🔁" source={t("skeleton.usersSrc5")} />
          </div>
        </section>
      </div>
    </div>
  );
}
