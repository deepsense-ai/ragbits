import { RouteObject } from "react-router";
import App from "./App";
import Chat from "./core/components/Chat";

export const ROUTES: RouteObject[] = [
  {
    path: "/",
    element: <App />,
    children: [
      {
        index: true,
        element: <Chat />,
      },
      {
        path: "*",
        element: <Chat />,
      },
    ],
  },
];
