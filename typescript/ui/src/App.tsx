import Layout from "./core/components/Layout";
import { useLayoutEffect, useMemo } from "react";
import { useConfigContext } from "./core/contexts/ConfigContext/useConfigContext";
import { DEFAULT_LOGO, DEFAULT_SUBTITLE, DEFAULT_TITLE } from "./core/config";
import { Outlet } from "react-router";
import { isURL } from "./core/utils/media";
import { usePluginActivation } from "./ragbits/PluginActivator";

const CUSTOM_FAVICON_ID = "generated-favicon";

export default function App() {
  usePluginActivation();

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

  const favicon = useMemo(
    () => customization?.meta?.favicon ?? logo,
    [customization?.meta?.favicon, logo],
  );
  const pageTitle = useMemo(
    () => customization?.meta?.page_title ?? title,
    [customization?.meta?.page_title, title],
  );

  useLayoutEffect(() => {
    document.title = pageTitle;
  }, [pageTitle]);

  const addFaviconTag = (href: string) => {
    const link = document.createElement("link");
    link.rel = "icon";
    link.href = href;
    link.id = CUSTOM_FAVICON_ID;

    document.head.appendChild(link);
  };

  useLayoutEffect(() => {
    const oldLinks = document.querySelectorAll("link[rel*='icon']");
    oldLinks.forEach((el) => el.remove());

    if (isURL(favicon)) {
      addFaviconTag(favicon);
    } else {
      const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">
        <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle"
              font-family="sans-serif" font-size="48">${favicon}</text>
      </svg>
    `;
      const utf8Bytes = new TextEncoder().encode(svg);
      const binaryString = Array.from(utf8Bytes)
        .map((byte) => String.fromCharCode(byte))
        .join("");
      const base64 = btoa(binaryString);
      const svgDataUrl = `data:image/svg+xml;base64,${base64}`;
      addFaviconTag(svgDataUrl);
    }

    // Remove existing favicons
    return () => {
      document.querySelector(`#${CUSTOM_FAVICON_ID}`)?.remove();
    };
  }, [favicon]);

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
