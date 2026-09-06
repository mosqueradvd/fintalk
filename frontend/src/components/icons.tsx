// Small inline SVGs — kept local so the bundle stays dependency-free.
// All use `currentColor` so they inherit the surrounding text color / theme.

type P = { size?: number };

export const SparkIcon = ({ size = 16 }: P) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden>
    <path
      d="M8 1.5l1.4 3.6L13 6.5 9.4 7.9 8 11.5 6.6 7.9 3 6.5l3.6-1.4L8 1.5z"
      fill="currentColor"
    />
  </svg>
);

export const CloseIcon = ({ size = 16 }: P) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden>
    <path
      d="M4 4l8 8M12 4l-8 8"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
    />
  </svg>
);

export const CopyIcon = ({ size = 14 }: P) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden>
    <rect
      x="5.75"
      y="5.75"
      width="8.5"
      height="8.5"
      rx="2"
      stroke="currentColor"
      strokeWidth="1.5"
    />
    <path
      d="M10.5 5.5V4a2 2 0 00-2-2H4a2 2 0 00-2 2v4.5a2 2 0 002 2h1.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
);

export const CheckIcon = ({ size = 14 }: P) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden>
    <path
      d="M3.5 8.5l3 3 6-7"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// A tool call — a function-call glyph: ƒ(x) styled as brackets + dot.
export const ToolIcon = ({ size = 15 }: P) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden>
    <path
      d="M6 2.5C4 2.5 4 5 4 6.5S4 10 3 10.5c1 .5 1 2 1 3.5s0 1.5 2 1.5M10 2.5c2 0 2 2.5 2 4s0 3.5 1 4c-1 .5-1 2-1 3.5s0 1.5-2 1.5"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinecap="round"
    />
    <circle cx="8" cy="8" r="1" fill="currentColor" />
  </svg>
);

export const SunIcon = ({ size = 15 }: P) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden>
    <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.5" />
    <path
      d="M8 1v1.5M8 13.5V15M15 8h-1.5M2.5 8H1M12.95 3.05l-1.06 1.06M4.11 11.89l-1.06 1.06M12.95 12.95l-1.06-1.06M4.11 4.11L3.05 3.05"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
);

export const MoonIcon = ({ size = 15 }: P) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden>
    <path
      d="M13.5 9.5A5.5 5.5 0 016.5 2.5a5.5 5.5 0 107 7z"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinejoin="round"
    />
  </svg>
);
