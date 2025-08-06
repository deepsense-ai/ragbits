import Layout from "./core/components/Layout";
import { useMemo } from "react";
import { useConfigContext } from "./core/contexts/ConfigContext/useConfigContext";
import { DEFAULT_LOGO, DEFAULT_SUBTITLE, DEFAULT_TITLE } from "./config";
import { Outlet } from "react-router";

export default function App() {
  const {
    config: { customization },
  } = useConfigContext();

  const logo = useMemo(
    () => customization?.header?.logo ?? DEFAULT_LOGO,
    [customization?.header?.logo],
  );
  const title = useMemo(
    () => customization?.header?.title ?? DEFAULT_TITLE,
    [customization?.header?.title],
  );
  const subTitle = useMemo(
    () => customization?.header?.subtitle ?? DEFAULT_SUBTITLE,
    [customization?.header?.subtitle],
  );

  return (
    <div className="bg-background flex h-screen w-screen items-start justify-center">
      <div className="h-full w-full max-w-full">
        <Layout subTitle={subTitle} title={title} logo={logo}>
          <Outlet />
        </Layout>
      </div>
    </div>
  );
}
