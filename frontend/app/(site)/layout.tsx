export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-2 px-6 py-4">
          <span className="text-lg font-semibold">AI Shop Analyzer</span>
          <span className="text-sm text-gray-400">店铺 · 达人数据智能分析</span>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </>
  );
}
