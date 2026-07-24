import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "success" | "danger" | "warning" | "secondary";

const variants: Record<Variant, string> = {
  default: "bg-gray-100 text-gray-700 border-gray-200",
  success: "bg-green-50 text-green-700 border-green-200",
  danger: "bg-red-50 text-red-700 border-red-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  secondary: "bg-blue-50 text-blue-700 border-blue-200",
};

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
