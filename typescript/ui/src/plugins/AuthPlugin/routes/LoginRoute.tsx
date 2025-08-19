import { lazy, Suspense } from "react";

const LazyLogin = lazy(() => import("../components/Login"));

export default function LoginRoute() {
  return (
    <Suspense>
      <LazyLogin />
    </Suspense>
  );
}
