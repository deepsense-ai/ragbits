import type {CSSProperties} from "react";

export enum CategoryEnum {
  APPLICATION = "application",
  AI = "ai",
  MARKETING = "marketing",
  ECOMMERCE = "ecommerce",
  CHARTS = "charts",
}

export type Attributes = {
  /**
   * If defined, will override the default component name taken from the folder name
   */
  name?: string;
  /**
   * If defined, will override the default component image taken from storybook preview
   */
  image?: string;
  /**
   * Group name to be used when opening the component
   */
  group?: string;
  /**
   *  If defined, indicates that the component only supports a specific theme
   */
  supportedTheme?: "dark" | "light";
  /**
   * If defined, it will allow users to refresh the iframe
   */
  allowRefresh?: boolean;
  /**
   * If defined, the component will be featured in the homepage
   */
  featured?: string | boolean;
  /**
   * If defined, an alert will be shown in the component preview page
   * to encourage the user to open the component in a new tab.
   */
  openInNewTabRecommended?: boolean;
  /**
   * If defined, will sort the component in the category panel based on the priority
   */
  sortPriority?: "high" | "medium" | "low";
  /**
   * If defined, will sort the component in the components preview page from low to high
   */
  groupOrder?: number;
  /**
   * Whether the component is new or not
   * @default false
   */
  isNew?: boolean;
  /**
   * Whether the component is free to use or not
   * @default false
   */
  isFree?: boolean;
  /**
   * Props to be passed to the iframe component inside components/page
   */
  iframe?: {
    /**
     * If defined, the iframe will justify the content based on the value
     */
    justify?: "start" | "center" | "end";
    /**
     * If defined, the iframe will adjust the height based on the content when the window is resized
     */
    shouldUpdateHeightOnResize?: boolean;
    /**
     * The initial height of the iframe
     */
    initialHeight?: number;
    /**
     * The initial height of the iframe on mobile
     */
    initialMobileHeight?: number;
    /**
     * If true, the iframe will not have any padding
     */
    removePadding?: boolean;
  };
  /**
   * Props to control the image component inside CategoryPanel
   */
  screenshot?: {
    /**
     * If defined, it will override the default screenshot selector
     */
    selector?: string;
    /**
     * If defined, the screenshot will be delayed for the specified amount of time
     */
    delay?: number;
    /**
     * If defined, it will override the default viewport size
     */
    viewport?: {
      width: number;
      height: number;
    };
    /**
     * If true, the screenshot will be full width (object-fit: cover & padding:0)
     * @default false
     */
    fullWidth?: string | boolean;
    /**
     * If defined, the default object position will be overridden
     */
    objectPosition?: string;
    /**
     * Style object to be passed to the image component.
     */
    style?: CSSProperties;
  };
  /**
   * If false, the component will be rendered directly in the page instead of within an iframe
   * @default false
   */
  renderInIframe?: boolean;
};

export interface TsConfigOptions {
  baseUrl?: string;
  paths?: Record<string, string[]>; // Explicit type for paths
}

export type ComponentCodeFile = {
  fileName: string;
  code: string;
  language: string;
};

export type ComponentInfo = {
  slug: string;
  name: string;
  image: string;
  code?: ComponentCodeFile[];
  files?: {
    javascript?: Record<string, string>;
    typescript?: Record<string, string>;
  };
  attributes?: Attributes;
};

export type GroupInfo = {
  key: string;
  name?: string;
};

export type CategoryComponents = Record<CategoryEnum, ComponentInfo[]>;

export interface ComponentPreviewPageInfo {
  group?: string;
  category?: CategoryEnum;
  components?: ComponentInfo[];
}

export type DynamicComponentProps = {
  category?: CategoryEnum;
  componentSlug?: string;
  component?: ComponentInfo;
};

export interface SearchResultItem {
  slug: string;
  url: string;
  group: GroupInfo;
  content: string;
  image?: string;
  category: string;
  component: ComponentInfo;
}

export type MessagingChatMessageProps = React.HTMLAttributes<HTMLDivElement> & {
  name: string;
  message: string;
  time?: string;
  isRTL?: boolean;
  classNames?: Record<"base", string>;
};
