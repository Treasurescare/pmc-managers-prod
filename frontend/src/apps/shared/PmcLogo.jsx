export default function PmcLogo({ className = "", size = 40, inverse = false, src = null }) {
  // When a tenant has uploaded a custom logo, render it as an img.
  if (src) {
    return (
      <img src={src} alt="Portal logo"
           width={size} height={size}
           className={`${className} object-contain`}
           style={{ width: size, height: size }} />
    );
  }
  const bg = inverse ? "#ffffff" : "#0f1b3d";
  const fg = inverse ? "#0f1b3d" : "#ffffff";
  const accent = "#3b6fa0";
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-hidden="true">
      <rect width="64" height="64" fill={bg} />
      <text x="14" y="42" fill={fg} fontFamily="'Libre Baskerville', Georgia, serif" fontSize="34" fontWeight="700">P</text>
      <circle cx="46" cy="20" r="6" fill="none" stroke={accent} strokeWidth="2" />
      <line x1="42" y1="20" x2="50" y2="20" stroke={accent} strokeWidth="1" />
      <line x1="46" y1="16" x2="46" y2="24" stroke={accent} strokeWidth="1" />
      <rect x="42" y="46" width="4" height="8" fill={accent} />
      <rect x="48" y="42" width="4" height="12" fill={accent} />
      <rect x="54" y="38" width="4" height="16" fill={accent} />
    </svg>
  );
}
