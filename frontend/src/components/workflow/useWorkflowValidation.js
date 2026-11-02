"use client";

import { useEffect, useState } from "react";
import {
  getWorkflowNodeTypes,
  validateWorkflowDefinition,
} from "@/services/workflows";
import { workflowSaveSnapshot } from "./workflowSaveState.js";
import { validateCanvas } from "./workflowValidation.js";

export function useWorkflowValidation(nodes, edges, sampleText, scope) {
  const [catalog, setCatalog] = useState(null);
  const [validation, setValidation] = useState(null);
  // Selection and canvas UUID replacements aren't changes to the definition.
  const snapshot = workflowSaveSnapshot(nodes, edges);
  const key = JSON.stringify([scope, snapshot, sampleText]);
  useEffect(() => {
    let current = true;
    getWorkflowNodeTypes()
      .then((result) => {
        if (current && Array.isArray(result?.nodes)) setCatalog(result);
      })
      .catch(() => {
        /* Server validation remains available without field hints. */
      });
    return () => {
      current = false;
    };
  }, [scope]);

  useEffect(() => {
    let current = true;
    const timer = window.setTimeout(async () => {
      const result = await validateCanvas({
        nodes,
        edges,
        sampleText,
        request: validateWorkflowDefinition,
        isCurrent: () => current,
      });
      if (result) setValidation({ key, result });
    }, 600);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
    // Only persisted definition changes should restart validation, not selection.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return {
    catalog,
    result: validation?.key === key ? validation.result : null,
    pending: validation?.key !== key,
  };
}
