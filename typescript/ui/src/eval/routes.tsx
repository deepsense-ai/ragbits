import { RouteObject, Navigate } from "react-router";
import { EvalLayout } from "./components/EvalLayout";
import { RunsTab } from "./components/tabs/RunsTab/RunsTab";
import { RunDetail } from "./components/tabs/RunsTab/RunDetail";
import { NewRunTab } from "./components/tabs/NewRunTab";
import { ScenariosTab } from "./components/tabs/ScenariosTab";
import { ScenarioDetail } from "./components/ScenarioDetail/ScenarioDetail";
import { PersonasTab } from "./components/tabs/PersonasTab";
import { PlaygroundTab } from "./components/tabs/PlaygroundTab";

export const EVAL_ROUTES: RouteObject[] = [
  {
    path: "/",
    element: <EvalLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/runs" replace />,
      },
      {
        path: "runs",
        element: <RunsTab />,
      },
      {
        path: "runs/:runId",
        element: <RunDetail />,
      },
      {
        path: "new",
        element: <NewRunTab />,
      },
      {
        path: "scenarios",
        element: <ScenariosTab />,
      },
      {
        path: "scenarios/:scenarioName",
        element: <ScenarioDetail />,
      },
      {
        path: "personas",
        element: <PersonasTab />,
      },
      {
        path: "playground",
        element: <PlaygroundTab />,
      },
    ],
  },
];
