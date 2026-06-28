'use client';

import { useEffect, useRef, useState } from 'react';
import { animate, useReducedMotion } from 'framer-motion';

interface Props {
  value: number;
  /** ms */
  duration?: number;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * Counts up 0 → value on mount / when value changes (review #8).
 * Respects prefers-reduced-motion by rendering the final value instantly.
 */
export default function AnimatedNumber({ value, duration = 900, className, style }: Props) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(reduce ? value : 0);
  const prev = useRef(0);

  useEffect(() => {
    if (reduce) {
      setDisplay(value);
      return;
    }
    const controls = animate(prev.current, value, {
      duration: duration / 1000,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: v => setDisplay(Math.round(v)),
    });
    prev.current = value;
    return () => controls.stop();
  }, [value, duration, reduce]);

  return (
    <span className={className} style={{ fontVariantNumeric: 'tabular-nums', ...style }}>
      {display.toLocaleString()}
    </span>
  );
}
