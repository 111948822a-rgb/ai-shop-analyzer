"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { getShops, type Shop } from "@/lib/api";

type ShopContextValue = {
  shops: Shop[];
  currentShopId: string; // "" 代表全部店铺
  setCurrentShopId: (id: string) => void;
  shopIds: string[] | undefined; // 传给 API 的 shopIds（undefined=全部，[xxx]=指定店铺）
  loading: boolean;
  refreshShops: () => Promise<void>;
};

const ShopContext = createContext<ShopContextValue | null>(null);

const STORAGE_KEY = "app-current-shop";

export function ShopProvider({ children }: { children: ReactNode }) {
  const [shops, setShops] = useState<Shop[]>([]);
  const [currentShopId, setCurrentShopIdState] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const refreshShops = useCallback(async () => {
    try {
      const res = await getShops();
      setShops(res);
    } catch {
      setShops([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshShops();
    // 从 localStorage 恢复上次选中的店铺
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) {
      setCurrentShopIdState(saved);
    }
  }, [refreshShops]);

  const setCurrentShopId = useCallback((id: string) => {
    setCurrentShopIdState(id);
    localStorage.setItem(STORAGE_KEY, id);
  }, []);

  // shopIds 传给 API：空串=全部店铺(undefined)，否则=[currentShopId]
  const shopIds = currentShopId === "" ? undefined : [currentShopId];

  return (
    <ShopContext.Provider
      value={{ shops, currentShopId, setCurrentShopId, shopIds, loading, refreshShops }}
    >
      {children}
    </ShopContext.Provider>
  );
}

export function useShop() {
  const ctx = useContext(ShopContext);
  if (!ctx) {
    throw new Error("useShop must be used within ShopProvider");
  }
  return ctx;
}
