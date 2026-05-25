/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
    theme: {
        extend: {
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            colors: {
                // C1B brand tokens (PRD §7.2) — used directly via bg-pn-* / text-pn-*
                pn: {
                    primary: "#0F172A",
                    accent: "#6366F1",
                    "accent-soft": "#818CF8",
                    success: "#10B981",
                    warning: "#F59E0B",
                    danger: "#F43F5E",
                    surface: "#F8FAFC",
                    card: "#FFFFFF",
                    muted: "#94A3B8",
                    border: "#E2E8F0",
                    ink: "#1E293B",
                },
                // shadcn semantic mapping
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
                popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
                primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
                secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
                muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
                accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
                destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                chart: {
                    1: "hsl(var(--chart-1))",
                    2: "hsl(var(--chart-2))",
                    3: "hsl(var(--chart-3))",
                    4: "hsl(var(--chart-4))",
                    5: "hsl(var(--chart-5))",
                },
            },
            fontFamily: {
                sans: ["'Plus Jakarta Sans'", "ui-sans-serif", "system-ui", "sans-serif"],
                display: ["'Sora'", "'Plus Jakarta Sans'", "sans-serif"],
                mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
            },
            keyframes: {
                "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
                "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
                shimmer: {
                    "0%": { backgroundPosition: "-1000px 0" },
                    "100%": { backgroundPosition: "1000px 0" },
                },
                pulseRing: {
                    "0%, 100%": { boxShadow: "0 0 0 0 var(--pulse-color)" },
                    "50%": { boxShadow: "0 0 0 12px transparent" },
                },
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
                shimmer: "shimmer 1.5s linear infinite",
                "pulse-ring": "pulseRing 2s infinite",
            },
        },
    },
    plugins: [require("tailwindcss-animate")],
};
