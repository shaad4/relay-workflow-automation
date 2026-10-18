"use client";

import { createContext, useContext, Children } from "react";

export const InspectorReadOnly = createContext(false);

// Read-only controls remain focusable, selectable, and scrollable.
export function InspectorInput({ disabled, readOnly, ...props }) {
  const inspecting = useContext(InspectorReadOnly) || readOnly;
  return <input {...props} disabled={inspecting ? false : disabled} readOnly={inspecting} />;
}

export function InspectorTextarea({ disabled, readOnly, ...props }) {
  const inspecting = useContext(InspectorReadOnly) || readOnly;
  return <textarea {...props} disabled={inspecting ? false : disabled} readOnly={inspecting} />;
}

export function InspectorSelect({ children, disabled, readOnly, value, onChange, ...props }) {
  const inspecting = useContext(InspectorReadOnly) || readOnly;
  if (inspecting) {
    const selected = Children.toArray(children).find((child) => String(child.props?.value) === String(value));
    const label = selected?.props.children;
    return <input {...props} value={label ? Children.toArray(label).join("") : value ?? ""} readOnly />;
  }
  return <select {...props} value={value} disabled={disabled} onChange={onChange}>{children}</select>;
}

export function InspectorButton({ inspectionAction = false, disabled, ...props }) {
  const inspecting = useContext(InspectorReadOnly);
  return <button {...props} disabled={disabled || (inspecting && !inspectionAction)} />;
}

export function InspectorFieldset({ disabled, ...props }) {
  const inspecting = useContext(InspectorReadOnly);
  return <fieldset {...props} disabled={!inspecting && disabled} />;
}
