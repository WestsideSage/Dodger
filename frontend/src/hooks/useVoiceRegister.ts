import { useCallback, useEffect, useState } from 'react';
import { commandApi } from '../api/client';

type VoiceRegister = Record<string, string>;

const registerCache = new Map<number, VoiceRegister>();

function formatTemplate(template: string, fmt?: Record<string, string | number>) {
  if (!fmt) return template;
  return template.replace(/\{(\w+)\}/g, (_match, token: string) => (
    token in fmt ? String(fmt[token]) : `{${token}}`
  ));
}

export function useVoiceRegister(tier = 1) {
  const [register, setRegister] = useState<VoiceRegister | null>(() => registerCache.get(tier) ?? null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (register) return;
    let cancelled = false;
    commandApi.voiceRegister(tier)
      .then((payload) => {
        if (cancelled) return;
        registerCache.set(tier, payload);
        setRegister(payload);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [register, tier]);

  const t = useCallback(
    (key: string, fmt?: Record<string, string | number>) => {
      const template = register?.[key];
      if (!template) return key;
      return formatTemplate(template, fmt);
    },
    [register],
  );

  return {
    error,
    ready: register !== null,
    register,
    t,
  };
}
