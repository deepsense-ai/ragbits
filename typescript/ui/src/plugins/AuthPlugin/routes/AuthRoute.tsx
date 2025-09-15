import { lazy, PropsWithChildren, Suspense } from "react";

const LazyAuthGuard = lazy(() => import("../components/AuthGuard"));
export default function AuthRoute({ children }: PropsWithChildren) {
  return (
    <Suspense>
      <LazyAuthGuard>{children}</LazyAuthGuard>
    </Suspense>
  );
}
