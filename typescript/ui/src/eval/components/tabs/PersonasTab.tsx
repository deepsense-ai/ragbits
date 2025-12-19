import { useState, useEffect, useRef } from "react";
import { Card, CardBody, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import type { Persona, PersonasListResponse } from "../../types";

export function PersonasTab() {
  const { client } = useRagbitsContext();
  const loadedRef = useRef(false);

  const [personas, setPersonas] = useState<Persona[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);

  // Load personas from API
  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;

    async function loadPersonas() {
      try {
        setIsLoading(true);
        const response = await fetch(`${client.getBaseUrl()}/api/eval/personas`);
        if (!response.ok) {
          throw new Error(`Failed to load personas: ${response.statusText}`);
        }
        const data: PersonasListResponse = await response.json();
        setPersonas(data.personas);
        setError(null);
      } catch (err) {
        console.error("Failed to load personas:", err);
        setError(err instanceof Error ? err.message : "Failed to load personas");
      } finally {
        setIsLoading(false);
      }
    }

    loadPersonas();
  }, [client]);

  // Auto-select first persona
  useEffect(() => {
    if (!selectedName && personas.length > 0) {
      setSelectedName(personas[0].name);
    }
  }, [selectedName, personas]);

  const selectedPersona = personas.find((p) => p.name === selectedName);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <Icon
          icon="heroicons:exclamation-triangle"
          className="text-6xl text-danger mb-4"
        />
        <h2 className="text-xl font-semibold text-foreground mb-2">
          Error Loading Personas
        </h2>
        <p className="text-foreground-500 max-w-md">{error}</p>
      </div>
    );
  }

  if (personas.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <Icon
          icon="heroicons:user-group"
          className="text-6xl text-foreground-300 mb-4"
        />
        <h2 className="text-xl font-semibold text-foreground mb-2">
          No Personas Found
        </h2>
        <p className="text-foreground-500 max-w-md">
          Create a <code className="bg-content2 px-1.5 py-0.5 rounded text-sm">personas.json</code> file
          in your scenarios directory to define user personas for simulations.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left: Persona list */}
      <aside className="w-72 flex-shrink-0 border-r border-divider overflow-y-auto">
        <div className="p-4">
          <h3 className="text-sm font-semibold text-foreground-500 uppercase tracking-wide mb-3">
            Personas ({personas.length})
          </h3>
          <div className="space-y-1">
            {personas.map((persona) => (
              <Card
                key={persona.name}
                isPressable
                onPress={() => setSelectedName(persona.name)}
                className={`w-full ${
                  selectedName === persona.name ? "border-2 border-primary" : ""
                }`}
              >
                <CardBody className="p-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-secondary/20 flex items-center justify-center flex-shrink-0">
                      <Icon
                        icon="heroicons:user"
                        className="text-secondary text-sm"
                      />
                    </div>
                    <p className="font-medium truncate">{persona.name}</p>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        </div>
      </aside>

      {/* Right: Persona detail */}
      <main className="flex-1 min-h-0 overflow-auto">
        {selectedPersona ? (
          <PersonaDetail persona={selectedPersona} />
        ) : (
          <div className="flex h-full items-center justify-center text-foreground-500">
            Select a persona to view details
          </div>
        )}
      </main>
    </div>
  );
}

function PersonaDetail({ persona }: { persona: Persona }) {
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-full bg-secondary/20 flex items-center justify-center">
            <Icon icon="heroicons:user" className="text-secondary text-2xl" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold">{persona.name}</h2>
            <p className="text-foreground-500">Persona definition</p>
          </div>
        </div>
      </div>

      {/* Description */}
      <Card className="mb-4">
        <CardBody className="p-4">
          <h3 className="text-sm font-semibold text-foreground-500 uppercase tracking-wide mb-3">
            Description
          </h3>
          <p className="text-foreground-700 whitespace-pre-wrap leading-relaxed">
            {persona.description}
          </p>
        </CardBody>
      </Card>

      {/* Info */}
      <Card>
        <CardBody className="p-4">
          <div className="flex items-start gap-3">
            <Icon
              icon="heroicons:information-circle"
              className="text-foreground-400 text-xl flex-shrink-0 mt-0.5"
            />
            <div>
              <p className="text-foreground-600">
                This persona can be selected when running scenarios to define
                the simulated user's behavior and personality.
              </p>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
